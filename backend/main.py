import os
import sys

# Fix Anaconda SSL_CERT_FILE pointing to a non-existent path.
# Conda activation scripts set this env var, but the cert file may not exist
# in the venv or the path may be stale — causing FileNotFoundError in ssl.py.
for _ssl_var in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
    _val = os.environ.get(_ssl_var, "")
    if _val and not os.path.exists(_val):
        del os.environ[_ssl_var]

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from rate_limiter import limiter
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
import uuid
import signal
import atexit
import socket
import subprocess
from datetime import datetime
from agent import classify_intent, _resolve_llm_credentials, process_conversation
from error_resolver import attempt_fix, reset_fix_cycle

from nf_service import get_or_create_worker, release_worker
from models import Base, engine, SessionLocal, Project, File, Message, get_db
import sqlalchemy as sa
from auth import get_current_user_ws, get_current_user, resolve_user_from_token
import storage_service
import models_api
import provider_api
import projects_api
import ideation_api
import csuite_api
import artifacts_api
import design_api


# ── Port Guard ───────────────────────────────────────────────────────────────
# Ensure only ONE server instance runs. Refuse to start if port is in use or
# another instance holds the PID lock. Never kill other processes.

_PORT = int(os.environ.get("PORT", 8000))
_PID_DIR = os.environ.get("KITH_PID_DIR", os.path.expanduser("~/.kith-foundry"))
_PID_FILE = os.path.join(_PID_DIR, f"server-{_PORT}.pid")


def _port_in_use(port: int) -> bool:
    """Return True if any process (other than us) is listening on port."""
    my_pid = os.getpid()
    my_ppid = os.getppid()
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, creationflags=0x08000000,
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = int(parts[-1])
                    if pid in (0, my_pid, my_ppid):
                        continue
                    return True
        except Exception:
            pass
        return False
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        for pid_str in out.splitlines():
            pid = int(pid_str)
            if pid in (my_pid, my_ppid):
                continue
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return False


def _pid_listening_on_port(pid: int, port: int) -> bool:
    """Return True if the given PID is listening on the given port."""
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, creationflags=0x08000000,
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 1 and parts[-1] == str(pid):
                        return True
        except Exception:
            pass
        return False
    try:
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        return str(pid) in out.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _pid_lock_held() -> tuple[bool, str]:
    """Return (held, message). held=True if another instance holds the lock."""
    try:
        os.makedirs(_PID_DIR, exist_ok=True)
    except OSError:
        pass
    # Escape hatch: force-clear stale lock (e.g. after crash when PID file wasn't removed)
    if os.getenv("KITH_FORCE_CLEAR_LOCK", "").lower() in ("1", "true", "yes"):
        try:
            if os.path.exists(_PID_FILE):
                os.remove(_PID_FILE)
                print("[port-guard] Cleared stale lock (KITH_FORCE_CLEAR_LOCK=1)")
        except OSError:
            pass
        return False, ""
    if not os.path.exists(_PID_FILE):
        return False, ""
    # If port is free, any lock is stale — safe to remove and proceed
    if not _port_in_use(_PORT):
        try:
            os.remove(_PID_FILE)
        except OSError:
            pass
        return False, ""
    try:
        with open(_PID_FILE, "r") as f:
            pid_str = f.read().strip()
        pid = int(pid_str)
        if pid == os.getpid():
            return False, ""
        if pid == os.getppid():
            # Lock held by our parent (uvicorn reloader) — we're the worker, same instance
            return False, ""
        try:
            os.kill(pid, 0)
        except OSError:
            # Process is dead — stale lock
            os.remove(_PID_FILE)
            return False, ""
        # Process exists; only treat as held if it's actually listening on our port
        if not _pid_listening_on_port(pid, _PORT):
            # PID exists but not using our port — stale lock (crashed without cleanup)
            os.remove(_PID_FILE)
            return False, ""
        # Extra safety: if port isn't in use at all, lock is stale (e.g. Windows os.kill quirk)
        if not _port_in_use(_PORT):
            os.remove(_PID_FILE)
            return False, ""
        return True, f"Another server (PID {pid}) holds the lock. Stop it first."
    except (ValueError, OSError):
        try:
            os.remove(_PID_FILE)
        except OSError:
            pass
        return False, ""


def _acquire_pid_lock() -> None:
    """Write our PID to the lock file."""
    try:
        os.makedirs(_PID_DIR, exist_ok=True)
        with open(_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError as e:
        print(f"[port-guard] Warning: could not write PID file: {e}")


def _release_pid_lock() -> None:
    """Remove PID file if it contains our PID."""
    try:
        if os.path.exists(_PID_FILE):
            with open(_PID_FILE, "r") as f:
                if f.read().strip() == str(os.getpid()):
                    os.remove(_PID_FILE)
    except OSError:
        pass


def _enforce_single_instance() -> None:
    """Refuse to start if port in use or another instance holds the lock."""
    held, msg = _pid_lock_held()
    if held:
        print(f"[port-guard] FATAL: {msg}")
        sys.exit(1)
    if _port_in_use(_PORT):
        print(f"[port-guard] FATAL: Port {_PORT} is already in use. Stop the other server first.")
        sys.exit(1)
    _acquire_pid_lock()


# Always enforce single instance (block duplicate servers from second terminal)
_enforce_single_instance()
atexit.register(_release_pid_lock)


# Create tables and ensure Storage bucket exists
# Use a daemon thread with join timeout to prevent DB hangs from blocking worker startup.
import threading as _threading

def _try_create_all() -> None:
    Base.metadata.create_all(bind=engine)

def _try_enum_migration() -> None:
    with engine.connect() as conn:
        for val in ("db_plan", "auth_plan", "implementation_phases"):
            conn.execute(
                sa.text(
                    "DO $$ BEGIN "
                    f"ALTER TYPE artifacttype ADD VALUE IF NOT EXISTS '{val}'; "
                    "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
                )
            )
        conn.commit()

for _fn, _label in ((_try_create_all, "create_all"), (_try_enum_migration, "enum migration")):
    _t = _threading.Thread(target=_fn, daemon=True, name=f"startup-{_label}")
    _t.start()
    _t.join(timeout=12)  # 12s max — daemon thread stays if DB hangs, but we continue
    if _t.is_alive():
        print(f"[startup] Warning: {_label} timed out (DB busy) — will retry 20s after app startup")

storage_service.ensure_bucket_exists()

# ── Startup recovery: reset orphaned CSuite 'running' rows ───────────────────
def _reset_orphaned_csuite() -> None:
    from models import CSuiteAnalysis, AgentStatus
    _startup_db = SessionLocal()
    try:
        _stuck = _startup_db.query(CSuiteAnalysis).filter(
            CSuiteAnalysis.status == AgentStatus.running
        ).all()
        if _stuck:
            print(f"[startup] Resetting {len(_stuck)} orphaned CSuite 'running' row(s) to 'pending'")
            for _row in _stuck:
                _row.status = AgentStatus.pending
            _startup_db.commit()
    finally:
        _startup_db.close()

try:
    _ct = _threading.Thread(target=_reset_orphaned_csuite, daemon=True, name="startup-csuite-reset")
    _ct.start()
    _ct.join(timeout=10)
    if _ct.is_alive():
        print("[startup] Warning: orphaned CSuite row reset timed out (non-fatal)")
except Exception as _e:
    print(f"[startup] Warning: could not reset orphaned CSuite rows: {_e}")

app = FastAPI()

# ── Rate limiting ────────────────────────────────────────────────────────────
# limiter is defined in rate_limiter.py (shared with API routers to avoid
# circular imports).  LLM-triggering endpoints use @limiter.limit("30/minute").
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Allow all origins in development — restricts to explicit list in production.
# Covers localhost, WSL IPs (172.x.x.x / 192.168.x.x) and any other dev hostname.
_CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "")
_PROD_ORIGINS = (
    [o.strip() for o in _CORS_ORIGINS_ENV.split(",") if o.strip()]
    if _CORS_ORIGINS_ENV
    else [
        "https://forgeoperator.com",
        "https://www.forgeoperator.com",
        "https://forge-operator.pages.dev",
        "https://kith-foundry.fly.dev",
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ENVIRONMENT", "development") != "production" else _PROD_ORIGINS,
    allow_credentials=False,  # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing routers
app.include_router(models_api.router)
app.include_router(provider_api.router)

# New API routers — design first (more specific /design/* paths) so they match before /{project_id}
app.include_router(design_api.router)
app.include_router(projects_api.router)
app.include_router(ideation_api.router)
app.include_router(csuite_api.router)
app.include_router(artifacts_api.router)
import export_api
app.include_router(export_api.router)
import routing_api
app.include_router(routing_api.router)
import billing_api
app.include_router(billing_api.router)
import capabilities_api
app.include_router(capabilities_api.router)
import secrets_api
app.include_router(secrets_api.router)
import deploy_api
app.include_router(deploy_api.router)
import sandbox_api
app.include_router(sandbox_api.router)

# ── Inngest — durable background jobs ────────────────────────────────────────
from inngest.fast_api import serve as _inngest_serve
import inngest_functions as _inngest_fns
import inngest_client as _inngest_client
from inngest_client import use_inngest
_inngest_serve(app, _inngest_client.client, _inngest_fns.all_functions)


@app.on_event("startup")
async def _startup_db_deferred() -> None:
    """Retry DB init in the background 20 s after startup.

    At cold boot PgBouncer often has no free backend slots, so create_all()
    and the enum migration time out in the module-level daemon threads.
    By the time 20 s have passed the workers are up and the pool has warmed,
    so the retry almost always succeeds.  Both operations are idempotent.
    """
    async def _run() -> None:
        await asyncio.sleep(20)
        for _fn, _label in ((_try_create_all, "create_all"), (_try_enum_migration, "enum migration")):
            _rt = _threading.Thread(target=_fn, daemon=True, name=f"retry-{_label}")
            _rt.start()
            _rt.join(timeout=30)
            if _rt.is_alive():
                print(f"[startup] {_label} retry still timed out — DB may be unavailable")
            else:
                print(f"[startup] {_label} completed on deferred retry")

    asyncio.create_task(_run())


@app.get("/api/health")
async def health_check():
    """Quick liveness + Redis connectivity check. Safe to call unauthenticated."""
    import time
    from redis_client import get_async_redis, REDIS_URL
    from circuit_breaker import llm_breaker
    status = {"ok": True, "redis": False, "redis_url_prefix": REDIS_URL[:20] + "..."}
    try:
        r = get_async_redis()
        probe_key = f"kith:health:{int(time.time())}"
        await r.set(probe_key, "1", ex=5)
        val = await r.get(probe_key)
        await r.delete(probe_key)
        status["redis"] = val == "1"
    except Exception as e:
        status["redis_error"] = str(e)
    status["llm_circuits"] = llm_breaker.status()
    return status


@app.get("/api/v1/projects/{project_id}/events")
async def project_events_sse(
    project_id: str,
    request: Request,
    token: str | None = None,
    db=Depends(get_db),
):
    """
    Server-Sent Events stream for a project.  Clients subscribe once and receive
    real-time updates instead of polling.  The stream relays any Redis pub/sub
    message published to kith:project:{project_id}:updates.

    Auth: send the JWT as ?token=... query param (EventSource can't set headers).
    """
    from sse_starlette.sse import EventSourceResponse
    from redis_state import project_channel, get_async_redis

    # Authenticate via query-param token (mirrors WebSocket auth)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    try:
        user = await resolve_user_from_token(token, db)
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    # Verify the user owns the project
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        return JSONResponse(status_code=404, content={"detail": "Project not found"})

    async def _event_generator():
        r = get_async_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(project_channel(project_id))
        try:
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message.get("type") == "message":
                    raw = message["data"]
                    yield {"data": raw.decode() if isinstance(raw, bytes) else raw}
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(project_channel(project_id))
            await pubsub.aclose()

    return EventSourceResponse(_event_generator())





    """Verify Inngest Dev Server can reach this app on startup."""
    import os, httpx
    if os.getenv("USE_INNGEST", "0").strip() != "1":
        return  # Inngest disabled
    is_prod = os.getenv("INNGEST_PRODUCTION", "0").strip() == "1"
    if is_prod:
        print("📡 Inngest: production mode — sync handled by Inngest Cloud")
        return
    # In dev mode: ping the Dev Server to confirm it's reachable,
    # then trigger a sync by calling our own /api/inngest (PUT = SDK sync endpoint).
    dev_server = os.getenv("INNGEST_DEV_SERVER_URL", "http://localhost:8288")
    app_url = "http://localhost:8000/api/inngest"
    async def _wait_for_inngest_dev_server() -> None:
        last_error = ""
        async with httpx.AsyncClient(timeout=3) as client:
            for attempt in range(1, 11):
                try:
                    ping = await client.get(dev_server, timeout=2)
                    if ping.status_code >= 400:
                        raise RuntimeError(f"Dev Server returned {ping.status_code}")
                    print(f"✅ Inngest Dev Server reachable at {dev_server}")
                    print(f"📡 Inngest functions registered at {app_url}")
                    return
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                    if attempt < 10:
                        await asyncio.sleep(2)

        print(f"⚠️  Inngest Dev Server not reachable at {dev_server} ({last_error})")
        print(f"   Start it with: npx inngest-cli@latest dev -u {app_url}")
        print("   If you started Inngest after the backend, this warning is harmless; jobs will work once the dev server is up.")

    asyncio.create_task(_wait_for_inngest_dev_server())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _persist_message(db, project_id: str, role: str, content: str):
    if not content:
        return
    db.add(Message(
        id=str(uuid.uuid4()),
        project_id=project_id,
        role=role,
        content=content,
        created_at=datetime.utcnow(),
    ))
    db.commit()


async def _persist_files(db, project_id: str, write_edits: list[dict]):
    """Upload file contents to Supabase Storage and update DB metadata (no content in DB)."""
    # 1. Upload content to Supabase Storage (may partially fail)
    storage_error = None
    try:
        await storage_service.upload_files(project_id, write_edits)
    except Exception as e:
        storage_error = e
        import traceback
        print(f"[persist] Storage upload error (saving DB metadata anyway): {e}")
        print(f"[persist] FULL TRACEBACK:\n{traceback.format_exc()}")

    # 2. Keep DB metadata (file_path + timestamp only) — content stays in Storage
    for edit in write_edits:
        file_path = edit.get("file_path")
        if not file_path:
            continue

        existing = db.query(File).filter(
            File.project_id == project_id,
            File.file_path == file_path,
        ).first()

        if existing:
            existing.content = None  # clear legacy DB content
            existing.updated_at = datetime.utcnow()
        else:
            db.add(File(
                id=str(uuid.uuid4()),
                project_id=project_id,
                file_path=file_path,
                content=None,  # content lives in Storage
                updated_at=datetime.utcnow(),
            ))
    db.commit()

    if storage_error:
        raise storage_error


# ── Lucide-react icon sanitizer constants ─────────────────────────────────────
# Maps hallucinated / incorrectly-cased lucide-react icon names to real exports.
_LUCIDE_ICON_RENAMES: dict[str, str] = {
    "GitDiff": "GitCompare",
    "Close": "X",
    "Checkmark": "Check",
    "Cancel": "X",
    "Gear": "Settings",
    "Config": "Settings",
    "GitHub": "Github",
    "GitLab": "Gitlab",
    "Warning": "AlertTriangle",
    "Danger": "AlertCircle",
    "InfoCircle": "Info",
    "QuestionCircle": "HelpCircle",
    "ErrorCircle": "XCircle",
    "SuccessCircle": "CheckCircle",
    "Money": "DollarSign",
    "Dollar": "DollarSign",
    "Delete": "Trash2",
    "People": "Users",
    "ExternalLinkAlt": "ExternalLink",
    "Spinner": "LoaderCircle",
    "Loading": "LoaderCircle",
}

_LUCIDE_KNOWN_ICONS: frozenset = frozenset({
    "AArrowDown", "AArrowUp", "ALargeSmall", "Accessibility", "Activity", "ActivitySquare", "AirVent", "Airplay",
    "AlarmCheck", "AlarmClock", "AlarmClockCheck", "AlarmClockMinus", "AlarmClockOff", "AlarmClockPlus", "AlarmMinus", "AlarmPlus",
    "AlarmSmoke", "Album", "AlertCircle", "AlertOctagon", "AlertTriangle", "AlignCenter", "AlignCenterHorizontal", "AlignCenterVertical",
    "AlignEndHorizontal", "AlignEndVertical", "AlignHorizontalDistributeCenter", "AlignHorizontalDistributeEnd", "AlignHorizontalDistributeStart", "AlignHorizontalJustifyCenter", "AlignHorizontalJustifyEnd", "AlignHorizontalJustifyStart",
    "AlignHorizontalSpaceAround", "AlignHorizontalSpaceBetween", "AlignJustify", "AlignLeft", "AlignRight", "AlignStartHorizontal", "AlignStartVertical", "AlignVerticalDistributeCenter",
    "AlignVerticalDistributeEnd", "AlignVerticalDistributeStart", "AlignVerticalJustifyCenter", "AlignVerticalJustifyEnd", "AlignVerticalJustifyStart", "AlignVerticalSpaceAround", "AlignVerticalSpaceBetween", "Ambulance",
    "Ampersand", "Ampersands", "Amphora", "Anchor", "Angry", "Annoyed", "Antenna", "Anvil",
    "Aperture", "AppWindow", "AppWindowMac", "Apple", "Archive", "ArchiveRestore", "ArchiveX", "AreaChart",
    "Armchair", "ArrowBigDown", "ArrowBigDownDash", "ArrowBigLeft", "ArrowBigLeftDash", "ArrowBigRight", "ArrowBigRightDash", "ArrowBigUp",
    "ArrowBigUpDash", "ArrowDown", "ArrowDown01", "ArrowDown10", "ArrowDownAZ", "ArrowDownAz", "ArrowDownCircle", "ArrowDownFromLine",
    "ArrowDownLeft", "ArrowDownLeftFromCircle", "ArrowDownLeftFromSquare", "ArrowDownLeftSquare", "ArrowDownNarrowWide", "ArrowDownRight", "ArrowDownRightFromCircle", "ArrowDownRightFromSquare",
    "ArrowDownRightSquare", "ArrowDownSquare", "ArrowDownToDot", "ArrowDownToLine", "ArrowDownUp", "ArrowDownWideNarrow", "ArrowDownZA", "ArrowDownZa",
    "ArrowLeft", "ArrowLeftCircle", "ArrowLeftFromLine", "ArrowLeftRight", "ArrowLeftSquare", "ArrowLeftToLine", "ArrowRight", "ArrowRightCircle",
    "ArrowRightFromLine", "ArrowRightLeft", "ArrowRightSquare", "ArrowRightToLine", "ArrowUp", "ArrowUp01", "ArrowUp10", "ArrowUpAZ",
    "ArrowUpAz", "ArrowUpCircle", "ArrowUpDown", "ArrowUpFromDot", "ArrowUpFromLine", "ArrowUpLeft", "ArrowUpLeftFromCircle", "ArrowUpLeftFromSquare",
    "ArrowUpLeftSquare", "ArrowUpNarrowWide", "ArrowUpRight", "ArrowUpRightFromCircle", "ArrowUpRightFromSquare", "ArrowUpRightSquare", "ArrowUpSquare", "ArrowUpToLine",
    "ArrowUpWideNarrow", "ArrowUpZA", "ArrowUpZa", "ArrowsUpFromLine", "Asterisk", "AsteriskSquare", "AtSign", "Atom",
    "AudioLines", "AudioWaveform", "Award", "Axe", "Axis3D", "Axis3d", "Baby", "Backpack",
    "Badge", "BadgeAlert", "BadgeCent", "BadgeCheck", "BadgeDollarSign", "BadgeEuro", "BadgeHelp", "BadgeIndianRupee",
    "BadgeInfo", "BadgeJapaneseYen", "BadgeMinus", "BadgePercent", "BadgePlus", "BadgePoundSterling", "BadgeQuestionMark", "BadgeRussianRuble",
    "BadgeSwissFranc", "BadgeTurkishLira", "BadgeX", "BaggageClaim", "Balloon", "Ban", "Banana", "Bandage",
    "Banknote", "BanknoteArrowDown", "BanknoteArrowUp", "BanknoteX", "BarChart", "BarChart2", "BarChart3", "BarChart4",
    "BarChartBig", "BarChartHorizontal", "BarChartHorizontalBig", "Barcode", "Barrel", "Baseline", "Bath", "Battery",
    "BatteryCharging", "BatteryFull", "BatteryLow", "BatteryMedium", "BatteryPlus", "BatteryWarning", "Beaker", "Bean",
    "BeanOff", "Bed", "BedDouble", "BedSingle", "Beef", "Beer", "BeerOff", "Bell",
    "BellDot", "BellElectric", "BellMinus", "BellOff", "BellPlus", "BellRing", "BetweenHorizonalEnd", "BetweenHorizonalStart",
    "BetweenHorizontalEnd", "BetweenHorizontalStart", "BetweenVerticalEnd", "BetweenVerticalStart", "BicepsFlexed", "Bike", "Binary", "Binoculars",
    "Biohazard", "Bird", "Birdhouse", "Bitcoin", "Blend", "Blinds", "Blocks", "Bluetooth",
    "BluetoothConnected", "BluetoothOff", "BluetoothSearching", "Bold", "Bolt", "Bomb", "Bone", "Book",
    "BookA", "BookAlert", "BookAudio", "BookCheck", "BookCopy", "BookDashed", "BookDown", "BookHeadphones",
    "BookHeart", "BookImage", "BookKey", "BookLock", "BookMarked", "BookMinus", "BookOpen", "BookOpenCheck",
    "BookOpenText", "BookPlus", "BookSearch", "BookTemplate", "BookText", "BookType", "BookUp", "BookUp2",
    "BookUser", "BookX", "Bookmark", "BookmarkCheck", "BookmarkMinus", "BookmarkPlus", "BookmarkX", "BoomBox",
    "Bot", "BotMessageSquare", "BotOff", "BottleWine", "BowArrow", "Box", "BoxSelect", "Boxes",
    "Braces", "Brackets", "Brain", "BrainCircuit", "BrainCog", "BrickWall", "BrickWallFire", "BrickWallShield",
    "Briefcase", "BriefcaseBusiness", "BriefcaseConveyorBelt", "BriefcaseMedical", "BringToFront", "Brush", "BrushCleaning", "Bubbles",
    "Bug", "BugOff", "BugPlay", "Building", "Building2", "Bus", "BusFront", "Cable",
    "CableCar", "Cake", "CakeSlice", "Calculator", "Calendar", "Calendar1", "CalendarArrowDown", "CalendarArrowUp",
    "CalendarCheck", "CalendarCheck2", "CalendarClock", "CalendarCog", "CalendarDays", "CalendarFold", "CalendarHeart", "CalendarMinus",
    "CalendarMinus2", "CalendarOff", "CalendarPlus", "CalendarPlus2", "CalendarRange", "CalendarSearch", "CalendarSync", "CalendarX",
    "CalendarX2", "Calendars", "Camera", "CameraOff", "CandlestickChart", "Candy", "CandyCane", "CandyOff",
    "Cannabis", "CannabisOff", "Captions", "CaptionsOff", "Car", "CarFront", "CarTaxiFront", "Caravan",
    "CardSim", "Carrot", "CaseLower", "CaseSensitive", "CaseUpper", "CassetteTape", "Cast", "Castle",
    "Cat", "Cctv", "ChartArea", "ChartBar", "ChartBarBig", "ChartBarDecreasing", "ChartBarIncreasing", "ChartBarStacked",
    "ChartCandlestick", "ChartColumn", "ChartColumnBig", "ChartColumnDecreasing", "ChartColumnIncreasing", "ChartColumnStacked", "ChartGantt", "ChartLine",
    "ChartNetwork", "ChartNoAxesColumn", "ChartNoAxesColumnDecreasing", "ChartNoAxesColumnIncreasing", "ChartNoAxesCombined", "ChartNoAxesGantt", "ChartPie", "ChartScatter",
    "ChartSpline", "Check", "CheckCheck", "CheckCircle", "CheckCircle2", "CheckLine", "CheckSquare", "CheckSquare2",
    "ChefHat", "Cherry", "ChessBishop", "ChessKing", "ChessKnight", "ChessPawn", "ChessQueen", "ChessRook",
    "ChevronDown", "ChevronDownCircle", "ChevronDownSquare", "ChevronFirst", "ChevronLast", "ChevronLeft", "ChevronLeftCircle", "ChevronLeftSquare",
    "ChevronRight", "ChevronRightCircle", "ChevronRightSquare", "ChevronUp", "ChevronUpCircle", "ChevronUpSquare", "ChevronsDown", "ChevronsDownUp",
    "ChevronsLeft", "ChevronsLeftRight", "ChevronsLeftRightEllipsis", "ChevronsRight", "ChevronsRightLeft", "ChevronsUp", "ChevronsUpDown", "Chrome",
    "Chromium", "Church", "Cigarette", "CigaretteOff", "Circle", "CircleAlert", "CircleArrowDown", "CircleArrowLeft",
    "CircleArrowOutDownLeft", "CircleArrowOutDownRight", "CircleArrowOutUpLeft", "CircleArrowOutUpRight", "CircleArrowRight", "CircleArrowUp", "CircleCheck", "CircleCheckBig",
    "CircleChevronDown", "CircleChevronLeft", "CircleChevronRight", "CircleChevronUp", "CircleDashed", "CircleDivide", "CircleDollarSign", "CircleDot",
    "CircleDotDashed", "CircleEllipsis", "CircleEqual", "CircleFadingArrowUp", "CircleFadingPlus", "CircleGauge", "CircleHelp", "CircleMinus",
    "CircleOff", "CircleParking", "CircleParkingOff", "CirclePause", "CirclePercent", "CirclePile", "CirclePlay", "CirclePlus",
    "CirclePoundSterling", "CirclePower", "CircleQuestionMark", "CircleSlash", "CircleSlash2", "CircleSlashed", "CircleSmall", "CircleStar",
    "CircleStop", "CircleUser", "CircleUserRound", "CircleX", "CircuitBoard", "Citrus", "Clapperboard", "Clipboard",
    "ClipboardCheck", "ClipboardClock", "ClipboardCopy", "ClipboardEdit", "ClipboardList", "ClipboardMinus", "ClipboardPaste", "ClipboardPen",
    "ClipboardPenLine", "ClipboardPlus", "ClipboardSignature", "ClipboardType", "ClipboardX", "Clock", "Clock1", "Clock10",
    "Clock11", "Clock12", "Clock2", "Clock3", "Clock4", "Clock5", "Clock6", "Clock7",
    "Clock8", "Clock9", "ClockAlert", "ClockArrowDown", "ClockArrowUp", "ClockCheck", "ClockFading", "ClockPlus",
    "ClosedCaption", "Cloud", "CloudAlert", "CloudBackup", "CloudCheck", "CloudCog", "CloudDownload", "CloudDrizzle",
    "CloudFog", "CloudHail", "CloudLightning", "CloudMoon", "CloudMoonRain", "CloudOff", "CloudRain", "CloudRainWind",
    "CloudSnow", "CloudSun", "CloudSunRain", "CloudSync", "CloudUpload", "Cloudy", "Clover", "Club",
    "Code", "Code2", "CodeSquare", "CodeXml", "Codepen", "Codesandbox", "Coffee", "Cog",
    "Coins", "Columns", "Columns2", "Columns3", "Columns3Cog", "Columns4", "ColumnsSettings", "Combine",
    "Command", "Compass", "Component", "Computer", "ConciergeBell", "Cone", "Construction", "Contact",
    "Contact2", "ContactRound", "Container", "Contrast", "Cookie", "CookingPot", "Copy", "CopyCheck",
    "CopyMinus", "CopyPlus", "CopySlash", "CopyX", "Copyleft", "Copyright", "CornerDownLeft", "CornerDownRight",
    "CornerLeftDown", "CornerLeftUp", "CornerRightDown", "CornerRightUp", "CornerUpLeft", "CornerUpRight", "Cpu", "CreativeCommons",
    "CreditCard", "Croissant", "Crop", "Cross", "Crosshair", "Crown", "Cuboid", "CupSoda",
    "CurlyBraces", "Currency", "Cylinder", "Dam", "Database", "DatabaseBackup", "DatabaseSearch", "DatabaseZap",
    "DecimalsArrowLeft", "DecimalsArrowRight", "Delete", "Dessert", "Diameter", "Diamond", "DiamondMinus", "DiamondPercent",
    "DiamondPlus", "Dice1", "Dice2", "Dice3", "Dice4", "Dice5", "Dice6", "Dices",
    "Diff", "Disc", "Disc2", "Disc3", "DiscAlbum", "Divide", "DivideCircle", "DivideSquare",
    "Dna", "DnaOff", "Dock", "Dog", "DollarSign", "Donut", "DoorClosed", "DoorClosedLocked",
    "DoorOpen", "Dot", "DotSquare", "Download", "DownloadCloud", "DraftingCompass", "Drama", "Dribbble",
    "Drill", "Drone", "Droplet", "DropletOff", "Droplets", "Drum", "Drumstick", "Dumbbell",
    "Ear", "EarOff", "Earth", "EarthLock", "Eclipse", "Edit", "Edit2", "Edit3",
    "Egg", "EggFried", "EggOff", "Ellipsis", "EllipsisVertical", "Equal", "EqualApproximately", "EqualNot",
    "EqualSquare", "Eraser", "EthernetPort", "Euro", "EvCharger", "Expand", "ExternalLink", "Eye",
    "EyeClosed", "EyeOff", "Facebook", "Factory", "Fan", "FastForward", "Feather", "Fence",
    "FerrisWheel", "Figma", "File", "FileArchive", "FileAudio", "FileAudio2", "FileAxis3D", "FileAxis3d",
    "FileBadge", "FileBadge2", "FileBarChart", "FileBarChart2", "FileBox", "FileBraces", "FileBracesCorner", "FileChartColumn",
    "FileChartColumnIncreasing", "FileChartLine", "FileChartPie", "FileCheck", "FileCheck2", "FileCheckCorner", "FileClock", "FileCode",
    "FileCode2", "FileCodeCorner", "FileCog", "FileCog2", "FileDiff", "FileDigit", "FileDown", "FileEdit",
    "FileExclamationPoint", "FileHeadphone", "FileHeart", "FileImage", "FileInput", "FileJson", "FileJson2", "FileKey",
    "FileKey2", "FileLineChart", "FileLock", "FileLock2", "FileMinus", "FileMinus2", "FileMinusCorner", "FileMusic",
    "FileOutput", "FilePen", "FilePenLine", "FilePieChart", "FilePlay", "FilePlus", "FilePlus2", "FilePlusCorner",
    "FileQuestion", "FileQuestionMark", "FileScan", "FileSearch", "FileSearch2", "FileSearchCorner", "FileSignal", "FileSignature",
    "FileSliders", "FileSpreadsheet", "FileStack", "FileSymlink", "FileTerminal", "FileText", "FileType", "FileType2",
    "FileTypeCorner", "FileUp", "FileUser", "FileVideo", "FileVideo2", "FileVideoCamera", "FileVolume", "FileVolume2",
    "FileWarning", "FileX", "FileX2", "FileXCorner", "Files", "Film", "Filter", "FilterX",
    "Fingerprint", "FingerprintPattern", "FireExtinguisher", "Fish", "FishOff", "FishSymbol", "FishingHook", "Flag",
    "FlagOff", "FlagTriangleLeft", "FlagTriangleRight", "Flame", "FlameKindling", "Flashlight", "FlashlightOff", "FlaskConical",
    "FlaskConicalOff", "FlaskRound", "FlipHorizontal", "FlipHorizontal2", "FlipVertical", "FlipVertical2", "Flower", "Flower2",
    "Focus", "FoldHorizontal", "FoldVertical", "Folder", "FolderArchive", "FolderCheck", "FolderClock", "FolderClosed",
    "FolderCode", "FolderCog", "FolderCog2", "FolderDot", "FolderDown", "FolderEdit", "FolderGit", "FolderGit2",
    "FolderHeart", "FolderInput", "FolderKanban", "FolderKey", "FolderLock", "FolderMinus", "FolderOpen", "FolderOpenDot",
    "FolderOutput", "FolderPen", "FolderPlus", "FolderRoot", "FolderSearch", "FolderSearch2", "FolderSymlink", "FolderSync",
    "FolderTree", "FolderUp", "FolderX", "Folders", "Footprints", "ForkKnife", "ForkKnifeCrossed", "Forklift",
    "Form", "FormInput", "Forward", "Frame", "Framer", "Frown", "Fuel", "Fullscreen",
    "FunctionSquare", "Funnel", "FunnelPlus", "FunnelX", "GalleryHorizontal", "GalleryHorizontalEnd", "GalleryThumbnails", "GalleryVertical",
    "GalleryVerticalEnd", "Gamepad", "Gamepad2", "GamepadDirectional", "GanttChart", "GanttChartSquare", "Gauge", "GaugeCircle",
    "Gavel", "Gem", "GeorgianLari", "Ghost", "Gift", "GitBranch", "GitBranchMinus", "GitBranchPlus",
    "GitCommit", "GitCommitHorizontal", "GitCommitVertical", "GitCompare", "GitCompareArrows", "GitFork", "GitGraph", "GitMerge",
    "GitMergeConflict", "GitPullRequest", "GitPullRequestArrow", "GitPullRequestClosed", "GitPullRequestCreate", "GitPullRequestCreateArrow", "GitPullRequestDraft", "Github",
    "Gitlab", "GlassWater", "Glasses", "Globe", "Globe2", "GlobeLock", "GlobeOff", "GlobeX",
    "Goal", "Gpu", "Grab", "GraduationCap", "Grape", "Grid", "Grid2X2", "Grid2X2Check",
    "Grid2X2Plus", "Grid2X2X", "Grid2x2", "Grid2x2Check", "Grid2x2Plus", "Grid2x2X", "Grid3X3", "Grid3x2",
    "Grid3x3", "Grip", "GripHorizontal", "GripVertical", "Group", "Guitar", "Ham", "Hamburger",
    "Hammer", "Hand", "HandCoins", "HandFist", "HandGrab", "HandHeart", "HandHelping", "HandMetal",
    "HandPlatter", "Handbag", "Handshake", "HardDrive", "HardDriveDownload", "HardDriveUpload", "HardHat", "Hash",
    "HatGlasses", "Haze", "Hd", "HdmiPort", "Heading", "Heading1", "Heading2", "Heading3",
    "Heading4", "Heading5", "Heading6", "HeadphoneOff", "Headphones", "Headset", "Heart", "HeartCrack",
    "HeartHandshake", "HeartMinus", "HeartOff", "HeartPlus", "HeartPulse", "Heater", "Helicopter", "HelpCircle",
    "HelpingHand", "Hexagon", "Highlighter", "History", "Home", "Hop", "HopOff", "Hospital",
    "Hotel", "Hourglass", "House", "HouseHeart", "HousePlug", "HousePlus", "HouseWifi", "IceCream",
    "IceCream2", "IceCreamBowl", "IceCreamCone", "IdCard", "IdCardLanyard", "Image", "ImageDown", "ImageMinus",
    "ImageOff", "ImagePlay", "ImagePlus", "ImageUp", "ImageUpscale", "Images", "Import", "Inbox",
    "Indent", "IndentDecrease", "IndentIncrease", "IndianRupee", "Infinity", "Info", "Inspect", "InspectionPanel",
    "Instagram", "Italic", "IterationCcw", "IterationCw", "JapaneseYen", "Joystick", "Kanban", "KanbanSquare",
    "KanbanSquareDashed", "Kayak", "Key", "KeyRound", "KeySquare", "Keyboard", "KeyboardMusic", "KeyboardOff",
    "Lamp", "LampCeiling", "LampDesk", "LampFloor", "LampWallDown", "LampWallUp", "LandPlot", "Landmark",
    "Languages", "Laptop", "Laptop2", "LaptopMinimal", "LaptopMinimalCheck", "Lasso", "LassoSelect", "Laugh",
    "Layers", "Layers2", "Layers3", "LayersPlus", "Layout", "LayoutDashboard", "LayoutGrid", "LayoutList",
    "LayoutPanelLeft", "LayoutPanelTop", "LayoutTemplate", "Leaf", "LeafyGreen", "Lectern", "LensConcave", "LensConvex",
    "LetterText", "Library", "LibraryBig", "LibrarySquare", "LifeBuoy", "Ligature", "Lightbulb", "LightbulbOff",
    "LineChart", "LineDotRightHorizontal", "LineSquiggle", "Link", "Link2", "Link2Off", "Linkedin", "List",
    "ListCheck", "ListChecks", "ListChevronsDownUp", "ListChevronsUpDown", "ListCollapse", "ListEnd", "ListFilter", "ListFilterPlus",
    "ListIndentDecrease", "ListIndentIncrease", "ListMinus", "ListMusic", "ListOrdered", "ListPlus", "ListRestart", "ListStart",
    "ListTodo", "ListTree", "ListVideo", "ListX", "Loader", "Loader2", "LoaderCircle", "LoaderPinwheel",
    "Locate", "LocateFixed", "LocateOff", "LocationEdit", "Lock", "LockKeyhole", "LockKeyholeOpen", "LockOpen",
    "LogIn", "LogOut", "Logs", "Lollipop", "Luggage", "MSquare", "Magnet", "Mail",
    "MailCheck", "MailMinus", "MailOpen", "MailPlus", "MailQuestion", "MailQuestionMark", "MailSearch", "MailWarning",
    "MailX", "Mailbox", "Mails", "Map", "MapMinus", "MapPin", "MapPinCheck", "MapPinCheckInside",
    "MapPinHouse", "MapPinMinus", "MapPinMinusInside", "MapPinOff", "MapPinPen", "MapPinPlus", "MapPinPlusInside", "MapPinX",
    "MapPinXInside", "MapPinned", "MapPlus", "Mars", "MarsStroke", "Martini", "Maximize", "Maximize2",
    "Medal", "Megaphone", "MegaphoneOff", "Meh", "MemoryStick", "Menu", "MenuSquare", "Merge",
    "MessageCircle", "MessageCircleCheck", "MessageCircleCode", "MessageCircleDashed", "MessageCircleHeart", "MessageCircleMore", "MessageCircleOff", "MessageCirclePlus",
    "MessageCircleQuestion", "MessageCircleQuestionMark", "MessageCircleReply", "MessageCircleWarning", "MessageCircleX", "MessageSquare", "MessageSquareCheck", "MessageSquareCode",
    "MessageSquareDashed", "MessageSquareDiff", "MessageSquareDot", "MessageSquareHeart", "MessageSquareLock", "MessageSquareMore", "MessageSquareOff", "MessageSquarePlus",
    "MessageSquareQuote", "MessageSquareReply", "MessageSquareShare", "MessageSquareText", "MessageSquareWarning", "MessageSquareX", "MessagesSquare", "Metronome",
    "Mic", "Mic2", "MicOff", "MicVocal", "Microchip", "Microscope", "Microwave", "Milestone",
    "Milk", "MilkOff", "Minimize", "Minimize2", "Minus", "MinusCircle", "MinusSquare", "MirrorRectangular",
    "MirrorRound", "Monitor", "MonitorCheck", "MonitorCloud", "MonitorCog", "MonitorDot", "MonitorDown", "MonitorOff",
    "MonitorPause", "MonitorPlay", "MonitorSmartphone", "MonitorSpeaker", "MonitorStop", "MonitorUp", "MonitorX", "Moon",
    "MoonStar", "MoreHorizontal", "MoreVertical", "Motorbike", "Mountain", "MountainSnow", "Mouse", "MouseLeft",
    "MouseOff", "MousePointer", "MousePointer2", "MousePointer2Off", "MousePointerBan", "MousePointerClick", "MousePointerSquareDashed", "MouseRight",
    "Move", "Move3D", "Move3d", "MoveDiagonal", "MoveDiagonal2", "MoveDown", "MoveDownLeft", "MoveDownRight",
    "MoveHorizontal", "MoveLeft", "MoveRight", "MoveUp", "MoveUpLeft", "MoveUpRight", "MoveVertical", "Music",
    "Music2", "Music3", "Music4", "Navigation", "Navigation2", "Navigation2Off", "NavigationOff", "Network",
    "Newspaper", "Nfc", "NonBinary", "Notebook", "NotebookPen", "NotebookTabs", "NotebookText", "NotepadText",
    "NotepadTextDashed", "Nut", "NutOff", "Octagon", "OctagonAlert", "OctagonMinus", "OctagonPause", "OctagonX",
    "Omega", "Option", "Orbit", "Origami", "Outdent", "Package", "Package2", "PackageCheck",
    "PackageMinus", "PackageOpen", "PackagePlus", "PackageSearch", "PackageX", "PaintBucket", "PaintRoller", "Paintbrush",
    "Paintbrush2", "PaintbrushVertical", "Palette", "Palmtree", "Panda", "PanelBottom", "PanelBottomClose", "PanelBottomDashed",
    "PanelBottomInactive", "PanelBottomOpen", "PanelLeft", "PanelLeftClose", "PanelLeftDashed", "PanelLeftInactive", "PanelLeftOpen", "PanelLeftRightDashed",
    "PanelRight", "PanelRightClose", "PanelRightDashed", "PanelRightInactive", "PanelRightOpen", "PanelTop", "PanelTopBottomDashed", "PanelTopClose",
    "PanelTopDashed", "PanelTopInactive", "PanelTopOpen", "PanelsLeftBottom", "PanelsLeftRight", "PanelsRightBottom", "PanelsTopBottom", "PanelsTopLeft",
    "Paperclip", "Parentheses", "ParkingCircle", "ParkingCircleOff", "ParkingMeter", "ParkingSquare", "ParkingSquareOff", "PartyPopper",
    "Pause", "PauseCircle", "PauseOctagon", "PawPrint", "PcCase", "Pen", "PenBox", "PenLine",
    "PenOff", "PenSquare", "PenTool", "Pencil", "PencilLine", "PencilOff", "PencilRuler", "Pentagon",
    "Percent", "PercentCircle", "PercentDiamond", "PercentSquare", "PersonStanding", "PhilippinePeso", "Phone", "PhoneCall",
    "PhoneForwarded", "PhoneIncoming", "PhoneMissed", "PhoneOff", "PhoneOutgoing", "Pi", "PiSquare", "Piano",
    "Pickaxe", "PictureInPicture", "PictureInPicture2", "PieChart", "PiggyBank", "Pilcrow", "PilcrowLeft", "PilcrowRight",
    "PilcrowSquare", "Pill", "PillBottle", "Pin", "PinOff", "Pipette", "Pizza", "Plane",
    "PlaneLanding", "PlaneTakeoff", "Play", "PlayCircle", "PlaySquare", "Plug", "Plug2", "PlugZap",
    "PlugZap2", "Plus", "PlusCircle", "PlusSquare", "Pocket", "PocketKnife", "Podcast", "Pointer",
    "PointerOff", "Popcorn", "Popsicle", "PoundSterling", "Power", "PowerCircle", "PowerOff", "PowerSquare",
    "Presentation", "Printer", "PrinterCheck", "PrinterX", "Projector", "Proportions", "Puzzle", "Pyramid",
    "QrCode", "Quote", "Rabbit", "Radar", "Radiation", "Radical", "Radio", "RadioReceiver",
    "RadioTower", "Radius", "RailSymbol", "Rainbow", "Rat", "Ratio", "Receipt", "ReceiptCent",
    "ReceiptEuro", "ReceiptIndianRupee", "ReceiptJapaneseYen", "ReceiptPoundSterling", "ReceiptRussianRuble", "ReceiptSwissFranc", "ReceiptText", "ReceiptTurkishLira",
    "RectangleCircle", "RectangleEllipsis", "RectangleGoggles", "RectangleHorizontal", "RectangleVertical", "Recycle", "Redo", "Redo2",
    "RedoDot", "RefreshCcw", "RefreshCcwDot", "RefreshCw", "RefreshCwOff", "Refrigerator", "Regex", "RemoveFormatting",
    "Repeat", "Repeat1", "Repeat2", "Replace", "ReplaceAll", "Reply", "ReplyAll", "Rewind",
    "Ribbon", "Rocket", "RockingChair", "RollerCoaster", "Rose", "Rotate3D", "Rotate3d", "RotateCcw",
    "RotateCcwKey", "RotateCcwSquare", "RotateCw", "RotateCwSquare", "Route", "RouteOff", "Router", "Rows",
    "Rows2", "Rows3", "Rows4", "Rss", "Ruler", "RulerDimensionLine", "RussianRuble", "Sailboat",
    "Salad", "Sandwich", "Satellite", "SatelliteDish", "SaudiRiyal", "Save", "SaveAll", "SaveOff",
    "Scale", "Scale3D", "Scale3d", "Scaling", "Scan", "ScanBarcode", "ScanEye", "ScanFace",
    "ScanHeart", "ScanLine", "ScanQrCode", "ScanSearch", "ScanText", "ScatterChart", "School", "School2",
    "Scissors", "ScissorsLineDashed", "ScissorsSquare", "ScissorsSquareDashedBottom", "Scooter", "ScreenShare", "ScreenShareOff", "Scroll",
    "ScrollText", "Search", "SearchAlert", "SearchCheck", "SearchCode", "SearchSlash", "SearchX", "Section",
    "Send", "SendHorizonal", "SendHorizontal", "SendToBack", "SeparatorHorizontal", "SeparatorVertical", "Server", "ServerCog",
    "ServerCrash", "ServerOff", "Settings", "Settings2", "Shapes", "Share", "Share2", "Sheet",
    "Shell", "ShelvingUnit", "Shield", "ShieldAlert", "ShieldBan", "ShieldCheck", "ShieldClose", "ShieldEllipsis",
    "ShieldHalf", "ShieldMinus", "ShieldOff", "ShieldPlus", "ShieldQuestion", "ShieldQuestionMark", "ShieldUser", "ShieldX",
    "Ship", "ShipWheel", "Shirt", "ShoppingBag", "ShoppingBasket", "ShoppingCart", "Shovel", "ShowerHead",
    "Shredder", "Shrimp", "Shrink", "Shrub", "Shuffle", "Sidebar", "SidebarClose", "SidebarOpen",
    "Sigma", "SigmaSquare", "Signal", "SignalHigh", "SignalLow", "SignalMedium", "SignalZero", "Signature",
    "Signpost", "SignpostBig", "Siren", "SkipBack", "SkipForward", "Skull", "Slack", "Slash",
    "SlashSquare", "Slice", "Sliders", "SlidersHorizontal", "SlidersVertical", "Smartphone", "SmartphoneCharging", "SmartphoneNfc",
    "Smile", "SmilePlus", "Snail", "Snowflake", "SoapDispenserDroplet", "Sofa", "SolarPanel", "SortAsc",
    "SortDesc", "Soup", "Space", "Spade", "Sparkle", "Sparkles", "Speaker", "Speech",
    "SpellCheck", "SpellCheck2", "Spline", "SplinePointer", "Split", "SplitSquareHorizontal", "SplitSquareVertical", "Spool",
    "Spotlight", "SprayCan", "Sprout", "Square", "SquareActivity", "SquareArrowDown", "SquareArrowDownLeft", "SquareArrowDownRight",
    "SquareArrowLeft", "SquareArrowOutDownLeft", "SquareArrowOutDownRight", "SquareArrowOutUpLeft", "SquareArrowOutUpRight", "SquareArrowRight", "SquareArrowRightEnter", "SquareArrowRightExit",
    "SquareArrowUp", "SquareArrowUpLeft", "SquareArrowUpRight", "SquareAsterisk", "SquareBottomDashedScissors", "SquareCenterlineDashedHorizontal", "SquareCenterlineDashedVertical", "SquareChartGantt",
    "SquareCheck", "SquareCheckBig", "SquareChevronDown", "SquareChevronLeft", "SquareChevronRight", "SquareChevronUp", "SquareCode", "SquareDashed",
    "SquareDashedBottom", "SquareDashedBottomCode", "SquareDashedKanban", "SquareDashedMousePointer", "SquareDashedTopSolid", "SquareDivide", "SquareDot", "SquareEqual",
    "SquareFunction", "SquareGanttChart", "SquareKanban", "SquareLibrary", "SquareM", "SquareMenu", "SquareMinus", "SquareMousePointer",
    "SquareParking", "SquareParkingOff", "SquarePause", "SquarePen", "SquarePercent", "SquarePi", "SquarePilcrow", "SquarePlay",
    "SquarePlus", "SquarePower", "SquareRadical", "SquareRoundCorner", "SquareScissors", "SquareSigma", "SquareSlash", "SquareSplitHorizontal",
    "SquareSplitVertical", "SquareSquare", "SquareStack", "SquareStar", "SquareStop", "SquareTerminal", "SquareUser", "SquareUserRound",
    "SquareX", "SquaresExclude", "SquaresIntersect", "SquaresSubtract", "SquaresUnite", "Squircle", "SquircleDashed", "Squirrel",
    "Stamp", "Star", "StarHalf", "StarOff", "Stars", "StepBack", "StepForward", "Stethoscope",
    "Sticker", "StickyNote", "Stone", "StopCircle", "Store", "StretchHorizontal", "StretchVertical", "Strikethrough",
    "Subscript", "Subtitles", "Sun", "SunDim", "SunMedium", "SunMoon", "SunSnow", "Sunrise",
    "Sunset", "Superscript", "SwatchBook", "SwissFranc", "SwitchCamera", "Sword", "Swords", "Syringe",
    "Table", "Table2", "TableCellsMerge", "TableCellsSplit", "TableColumnsSplit", "TableConfig", "TableOfContents", "TableProperties",
    "TableRowsSplit", "Tablet", "TabletSmartphone", "Tablets", "Tag", "Tags", "Tally1", "Tally2",
    "Tally3", "Tally4", "Tally5", "Tangent", "Target", "Telescope", "Tent", "TentTree",
    "Terminal", "TerminalSquare", "TestTube", "TestTube2", "TestTubeDiagonal", "TestTubes", "Text", "TextAlignCenter",
    "TextAlignEnd", "TextAlignJustify", "TextAlignStart", "TextCursor", "TextCursorInput", "TextInitial", "TextQuote", "TextSearch",
    "TextSelect", "TextSelection", "TextWrap", "Theater", "Thermometer", "ThermometerSnowflake", "ThermometerSun", "ThumbsDown",
    "ThumbsUp", "Ticket", "TicketCheck", "TicketMinus", "TicketPercent", "TicketPlus", "TicketSlash", "TicketX",
    "Tickets", "TicketsPlane", "Timer", "TimerOff", "TimerReset", "ToggleLeft", "ToggleRight", "Toilet",
    "ToolCase", "Toolbox", "Tornado", "Torus", "Touchpad", "TouchpadOff", "TowelRack", "TowerControl",
    "ToyBrick", "Tractor", "TrafficCone", "Train", "TrainFront", "TrainFrontTunnel", "TrainTrack", "TramFront",
    "Transgender", "Trash", "Trash2", "TreeDeciduous", "TreePalm", "TreePine", "Trees", "Trello",
    "TrendingDown", "TrendingUp", "TrendingUpDown", "Triangle", "TriangleAlert", "TriangleDashed", "TriangleRight", "Trophy",
    "Truck", "TruckElectric", "TurkishLira", "Turntable", "Turtle", "Tv", "Tv2", "TvMinimal",
    "TvMinimalPlay", "Twitch", "Twitter", "Type", "TypeOutline", "Umbrella", "UmbrellaOff", "Underline",
    "Undo", "Undo2", "UndoDot", "UnfoldHorizontal", "UnfoldVertical", "Ungroup", "University", "Unlink",
    "Unlink2", "Unlock", "UnlockKeyhole", "Unplug", "Upload", "UploadCloud", "Usb", "User",
    "User2", "UserCheck", "UserCheck2", "UserCircle", "UserCircle2", "UserCog", "UserCog2", "UserKey",
    "UserLock", "UserMinus", "UserMinus2", "UserPen", "UserPlus", "UserPlus2", "UserRound", "UserRoundCheck",
    "UserRoundCog", "UserRoundKey", "UserRoundMinus", "UserRoundPen", "UserRoundPlus", "UserRoundSearch", "UserRoundX", "UserSearch",
    "UserSquare", "UserSquare2", "UserStar", "UserX", "UserX2", "Users", "Users2", "UsersRound",
    "Utensils", "UtensilsCrossed", "UtilityPole", "Van", "Variable", "Vault", "VectorSquare", "Vegan",
    "VenetianMask", "Venus", "VenusAndMars", "Verified", "Vibrate", "VibrateOff", "Video", "VideoOff",
    "Videotape", "View", "Voicemail", "Volleyball", "Volume", "Volume1", "Volume2", "VolumeOff",
    "VolumeX", "Vote", "Wallet", "Wallet2", "WalletCards", "WalletMinimal", "Wallpaper", "Wand",
    "Wand2", "WandSparkles", "Warehouse", "WashingMachine", "Watch", "Waves", "WavesArrowDown", "WavesArrowUp",
    "WavesLadder", "Waypoints", "Webcam", "Webhook", "WebhookOff", "Weight", "WeightTilde", "Wheat",
    "WheatOff", "WholeWord", "Wifi", "WifiCog", "WifiHigh", "WifiLow", "WifiOff", "WifiPen",
    "WifiSync", "WifiZero", "Wind", "WindArrowDown", "Wine", "WineOff", "Workflow", "Worm",
    "WrapText", "Wrench", "X", "XCircle", "XLineTop", "XOctagon", "XSquare", "Youtube",
    "Zap", "ZapOff", "ZoomIn", "ZoomOut",
})

def _sanitize_tsx_write_edits(write_edits: list[dict]) -> list[dict]:
    """Fix hallucinated lucide-react icon names in AI-generated TSX/JSX files.

    LLMs occasionally invent icon names (e.g. 'GitDiff') that do not exist in
    the installed lucide-react package, crashing the Vite sandbox at import time.
    This function rewrites `import { ... } from 'lucide-react'` statements so:
    - Known-wrong names are replaced via _LUCIDE_ICON_RENAMES
    - Completely unknown names fall back to 'Circle' (always safe)
    - Duplicate imports after remapping are deduplicated
    """
    import re as _re

    _IMPORT_RE = _re.compile(
        r"""^([ \t]*)import\s*\{([^}]+)\}\s*from\s+['"]lucide-react['"]""",
        _re.MULTILINE,
    )

    def _fix_import_line(match: _re.Match) -> str:
        indent = match.group(1)
        raw_names = match.group(2)
        fixed: list[str] = []
        seen: set[str] = set()
        for raw in _re.split(r",\s*", raw_names):
            name = raw.strip()
            if not name:
                continue
            as_match = _re.match(r"^(\w+)\s+as\s+(\w+)$", name)
            if as_match:
                icon_name, alias = as_match.group(1), as_match.group(2)
                canonical = _LUCIDE_ICON_RENAMES.get(icon_name, icon_name)
                if canonical not in _LUCIDE_KNOWN_ICONS:
                    print(f"[tsx-sanitize] Unknown lucide icon '{icon_name}' → Circle")
                    canonical = "Circle"
                resolved = f"{canonical} as {alias}" if canonical != icon_name else name
            else:
                icon_name = name
                canonical = _LUCIDE_ICON_RENAMES.get(icon_name, icon_name)
                if canonical not in _LUCIDE_KNOWN_ICONS:
                    print(f"[tsx-sanitize] Unknown lucide icon '{icon_name}' → Circle")
                    canonical = "Circle"
                if canonical != icon_name:
                    # Track identifier rewrites so JSX usage (e.g. <GitDiff />)
                    # is kept in sync with sanitized imports.
                    import_rewrites[icon_name] = canonical
                resolved = canonical
            if resolved not in seen:
                seen.add(resolved)
                fixed.append(resolved)
        return f"{indent}import {{ {', '.join(fixed)} }} from 'lucide-react'"

    patched: list[dict] = []
    for edit in write_edits:
        file_path = str(edit.get("file_path", ""))
        content = edit.get("content")
        if not isinstance(content, str) or not file_path.endswith((".tsx", ".ts", ".jsx", ".js")):
            patched.append(edit)
            continue
        if "lucide-react" not in content:
            patched.append(edit)
            continue
        import_rewrites: dict[str, str] = {}
        new_content = _IMPORT_RE.sub(_fix_import_line, content)
        if import_rewrites:
            for old_name, new_name in import_rewrites.items():
                new_content = _re.sub(rf"\b{_re.escape(old_name)}\b", new_name, new_content)
        if new_content != content:
            print(f"[tsx-sanitize] Patched lucide-react imports in {file_path}")
            next_edit = dict(edit)
            next_edit["content"] = new_content
            patched.append(next_edit)
        else:
            patched.append(edit)
    return patched

def _sanitize_css_write_edits(write_edits: list[dict]) -> list[dict]:
    """Patch known generated CSS pitfalls that crash Vite/PostCSS.

    Some model outputs use `@apply font-body` / `@apply font-heading` in App.css
    without defining those utilities. Tailwind then throws a 500 on /src/App.css.
    We append utility definitions once so preview compilation remains stable.
    """
    import re

    def _rewrite_apply_arbitrary_value_classes(css: str) -> str:
        """Rewrite unsupported @apply arbitrary-value classes to plain CSS.

        Tailwind's @apply does not support classes like bg-[var(--surface)]/80,
        text-[var(--text-primary)], border-[var(--border)], etc.
        Convert those tokens into direct declarations so CSS compiles.
        """
        apply_re = re.compile(r"^(?P<indent>\s*)@apply\s+(?P<body>[^;]+);\s*$")

        out_lines: list[str] = []
        for line in css.splitlines():
            m = apply_re.match(line)
            if not m:
                out_lines.append(line)
                continue

            indent = m.group("indent")
            tokens = m.group("body").split()
            remaining: list[str] = []
            declarations: list[str] = []

            for token in tokens:
                bg = re.match(r"^bg-\[var\(--(?P<name>[^)]+)\)\](?:/(?P<alpha>\d{1,3}))?$", token)
                if bg:
                    name = bg.group("name")
                    alpha = bg.group("alpha")
                    if alpha is not None:
                        declarations.append(
                            f"{indent}background-color: color-mix(in srgb, var(--{name}) {alpha}%, transparent);"
                        )
                    else:
                        declarations.append(f"{indent}background-color: var(--{name});")
                    continue

                text = re.match(r"^text-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if text:
                    declarations.append(f"{indent}color: var(--{text.group('name')});")
                    continue

                border = re.match(r"^border-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if border:
                    declarations.append(f"{indent}border-color: var(--{border.group('name')});")
                    continue

                rounded = re.match(r"^rounded-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if rounded:
                    declarations.append(f"{indent}border-radius: var(--{rounded.group('name')});")
                    continue

                shadow = re.match(r"^shadow-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if shadow:
                    declarations.append(f"{indent}box-shadow: var(--{shadow.group('name')});")
                    continue

                font = re.match(r"^font-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if font:
                    declarations.append(f"{indent}font-family: var(--{font.group('name')});")
                    continue

                w = re.match(r"^w-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if w:
                    declarations.append(f"{indent}width: var(--{w.group('name')});")
                    continue

                h = re.match(r"^h-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if h:
                    declarations.append(f"{indent}height: var(--{h.group('name')});")
                    continue

                p = re.match(r"^p-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if p:
                    declarations.append(f"{indent}padding: var(--{p.group('name')});")
                    continue

                px = re.match(r"^px-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if px:
                    name = px.group("name")
                    declarations.append(f"{indent}padding-left: var(--{name});")
                    declarations.append(f"{indent}padding-right: var(--{name});")
                    continue

                py = re.match(r"^py-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if py:
                    name = py.group("name")
                    declarations.append(f"{indent}padding-top: var(--{name});")
                    declarations.append(f"{indent}padding-bottom: var(--{name});")
                    continue

                mrg = re.match(r"^m-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if mrg:
                    declarations.append(f"{indent}margin: var(--{mrg.group('name')});")
                    continue

                mx = re.match(r"^mx-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if mx:
                    name = mx.group("name")
                    declarations.append(f"{indent}margin-left: var(--{name});")
                    declarations.append(f"{indent}margin-right: var(--{name});")
                    continue

                my = re.match(r"^my-\[var\(--(?P<name>[^)]+)\)\]$", token)
                if my:
                    name = my.group("name")
                    declarations.append(f"{indent}margin-top: var(--{name});")
                    declarations.append(f"{indent}margin-bottom: var(--{name});")
                    continue

                remaining.append(token)

            out_lines.extend(declarations)
            if remaining:
                out_lines.append(f"{indent}@apply {' '.join(remaining)};")

        return "\n".join(out_lines)

    patched: list[dict] = []
    utility_block = (
        "\n@layer utilities {\n"
        "  .font-body { font-family: var(--font-body); }\n"
        "  .font-heading { font-family: var(--font-heading); }\n"
        "}\n"
    )

    for edit in write_edits:
        file_path = str(edit.get("file_path", ""))
        content = edit.get("content")
        if not isinstance(content, str):
            patched.append(edit)
            continue

        if file_path.endswith(".css") and "@apply" in content:
            normalized = _rewrite_apply_arbitrary_value_classes(content)
            next_edit = dict(edit)
            next_edit["content"] = normalized

            content = normalized
            edit = next_edit

        if file_path.endswith(".css") and ("@apply" in content) and ("font-body" in content or "font-heading" in content):
            has_font_body_def = ".font-body" in content
            has_font_heading_def = ".font-heading" in content
            if not (has_font_body_def and has_font_heading_def):
                next_edit = dict(edit)
                next_edit["content"] = content.rstrip() + utility_block
                patched.append(next_edit)
                continue

        patched.append(edit)

    return patched


# ── Golden fallback — always-working React stub ───────────────────────────
# Written to the sandbox when code-gen produces files that fail Vite compilation
# AND the auto-fix loop also fails.  Guarantees the user always sees a working
# (if minimal) preview rather than a blank or erroring iframe.
_GOLDEN_FALLBACK_EDITS: list[dict] = [
    {
        "file_path": "src/main.tsx",
        "action": "write",
        "content": (
            "import React from 'react'\n"
            "import ReactDOM from 'react-dom/client'\n"
            "import App from './App'\n"
            "import './App.css'\n\n"
            "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
            "  <React.StrictMode>\n"
            "    <App />\n"
            "  </React.StrictMode>,\n"
            ")\n"
        ),
    },
    {
        "file_path": "src/App.tsx",
        "action": "write",
        "content": (
            "import './App.css'\n\n"
            "export default function App() {\n"
            "  return (\n"
            "    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: 600, margin: '0 auto' }}>\n"
            "      <h1 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Build error — safe placeholder</h1>\n"
            "      <p style={{ color: '#555' }}>\n"
            "        The generated code had a compilation error that could not be auto-repaired.\n"
            "        Describe what you want in the chat and I'll regenerate it cleanly.\n"
            "      </p>\n"
            "    </div>\n"
            "  )\n"
            "}\n"
        ),
    },
    {
        "file_path": "src/App.css",
        "action": "write",
        "content": "body { margin: 0; background: #fff; }\n",
    },
]


async def _send_json(websocket: WebSocket, payload: dict):
    try:
        await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        return
    except Exception as e:
        lowered = str(e).lower()
        if "disconnect" in lowered or "closed" in lowered or "close message" in lowered or "accept" in lowered:
            return
        raise


_TRANSIENT_MESSAGES = {
    "Analyzing request",
    "Reading current project files",
    "Generating code",
    "Waiting for input",
    "Writing ",
    "Agent is working",
}

# Error patterns that should NOT be persisted/replayed across sessions.
# These are transient infrastructure errors, not meaningful user context.
_TRANSIENT_ERROR_PATTERNS = {
    "storage upload failed",
    "connectionterminated",
    "error_code:9",
    "cloud save hit a temporary",
}

def _is_transient(content: str) -> bool:
    if any(content.startswith(t) for t in _TRANSIENT_MESSAGES):
        return True
    # Treat storage/connection errors as transient regardless of prefix
    lower = content.lower()
    if any(p in lower for p in _TRANSIENT_ERROR_PATTERNS):
        return True
    return False


def _user_visible_error_message(err: Exception) -> str:
    raw = str(err)
    lower = raw.lower()
    if (
        "storage upload failed" in lower
        or "connectionterminated" in lower
        or "error_code:9" in lower
    ):
        return "Files were generated, but cloud save hit a temporary network issue. Please retry."
    return f"Request processing failed: {raw}"


def _load_project_files(db, project_id: str):
    return db.query(File).filter(File.project_id == project_id).order_by(File.file_path.asc()).all()


def _build_file_tree_from_db(db, project_id: str) -> list:
    """Build a file tree structure from stored DB files."""
    stored_files = _load_project_files(db, project_id)
    root: list = []

    for f in stored_files:
        parts = f.file_path.split("/")
        current_level = root
        path_so_far = ""

        for i, part in enumerate(parts):
            path_so_far = f"{path_so_far}/{part}" if path_so_far else part
            is_file = (i == len(parts) - 1)

            existing = next((n for n in current_level if n["name"] == part), None)
            if existing:
                if not is_file:
                    current_level = existing.setdefault("children", [])
            else:
                node = {"name": part, "path": path_so_far, "type": "file" if is_file else "dir"}
                if not is_file:
                    node["children"] = []
                current_level.append(node)
                if not is_file:
                    current_level = node["children"]

    return root


async def _restore_project_state(websocket: WebSocket, db, project_id: str):
    """Send stored files and chat history to the frontend on reconnect."""

    def _fetch_state(db, project_id):
        sf = db.query(File).filter(
            File.project_id == project_id
        ).order_by(File.file_path.asc()).all()
        all_msgs = db.query(Message).filter(
            Message.project_id == project_id
        ).order_by(Message.created_at.asc()).all()
        history = []
        for m in all_msgs:
            if m.role == "system" and _is_transient(m.content or ""):
                db.delete(m)
            else:
                history.append({"role": m.role, "content": m.content})
        db.commit()
        # Snapshot to plain tuples — avoids expired-ORM-state errors after async boundary
        file_meta = [(f.file_path, f.content) for f in sf]
        return file_meta, history

    file_meta, clean_history = await asyncio.to_thread(_fetch_state, db, project_id)

    if file_meta:
        file_paths = [fp for fp, _ in file_meta]
        db_fallback = {fp: c for fp, c in file_meta if c}
        contents = await storage_service.download_project_files(
            project_id, file_paths, db_fallback=db_fallback
        )
        for fp, _ in file_meta:
            await _send_json(websocket, {
                "type": "file_written",
                "file": fp,
                "content": contents.get(fp, ""),
            })

    await _send_json(websocket, {
        "type": "message_history",
        "messages": clean_history,
    })


async def _ensure_sandbox_ready(websocket, db, project, project_id: str) -> tuple:
    """Boot or reuse a sandbox worker, restore files, start Vite, return (worker, preview_url).

    Sends sandbox_ready as early as possible (once the scaffold Vite page is confirmed
    serving) so the iframe appears immediately rather than waiting for full file restore.
    """
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Booting secure sandbox..."
    })

    # Get or create sandbox worker (runs on dedicated thread)
    worker = await asyncio.to_thread(get_or_create_worker, project_id)

    # Persist sandbox_id on the project row
    sandbox_id = worker.sandbox_id
    if sandbox_id and project.fly_sandbox_id != sandbox_id:
        project.fly_sandbox_id = sandbox_id
        project.updated_at = datetime.utcnow()
        db.commit()

    # ── Reuse path: warm worker with Vite already running ────────────────────
    if worker.preview_url:
        try:
            health = await asyncio.to_thread(worker.execute, "health_check", None, 10.0)
            if health == "ok":
                # Sync any DB-stored files that may differ from the live sandbox state
                # (e.g. after a server restart that recycled in-memory file writes).
                stored_files = _load_project_files(db, project_id)
                if stored_files:
                    db_fallback = {f.file_path: f.content for f in stored_files if f.content}
                    file_paths = [f.file_path for f in stored_files]
                    contents = await storage_service.download_project_files(
                        project_id, file_paths, db_fallback=db_fallback
                    )
                    batch = [
                        {"file_path": fp, "content": contents.get(fp, "")}
                        for fp in file_paths
                        if contents.get(fp, "").strip()
                    ]
                    if batch:
                        await asyncio.to_thread(worker.execute, "write_files", batch)
                        try:
                            await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
                        except Exception as e:
                            print(f"[sandbox] wait_vite_ready after reuse restore timed out: {e}")

                # Fail closed on reuse restore: if persisted files compile with errors,
                # replace with safe fallback before continuing.
                _reuse_errors = []
                try:
                    _reuse_errors = await asyncio.to_thread(worker.execute, "check_vite_errors") or []
                except Exception as _reuse_check_err:
                    print(f"[sandbox] Reuse check_vite_errors failed; applying fallback: {_reuse_check_err}")
                    _reuse_errors = [{"file": "unknown", "error": f"vite_check_failed: {_reuse_check_err}"}]

                if _reuse_errors:
                    print(f"[sandbox] Reuse path has {len(_reuse_errors)} Vite error(s); applying fallback")
                    await _persist_files(db, project_id, _GOLDEN_FALLBACK_EDITS)
                    await asyncio.to_thread(worker.execute, "write_files", _GOLDEN_FALLBACK_EDITS)
                    try:
                        await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
                    except Exception as _rwe:
                        print(f"[sandbox] Reuse fallback wait_vite_ready timeout: {_rwe}")
                    await _send_json(websocket, {
                        "type": "status", "status": "warning",
                        "message": "⚠️ Existing files had build errors. Showing a safe placeholder.",
                    })

                # Promote preview only after restore + compile checks are complete.
                await _send_json(websocket, {
                    "type": "sandbox_ready",
                    "previewUrl": worker.preview_url,
                })

                print(f"[sandbox] Reusing sandbox {worker.sandbox_id}, Vite healthy at {worker.preview_url}")
                return worker, worker.preview_url
            else:
                print(f"[sandbox] Sandbox {worker.sandbox_id} unhealthy ({health}), recreating...")
        except Exception as e:
            print(f"[sandbox] Sandbox {worker.sandbox_id} health check failed ({e}), recreating...")

        # Sandbox is dead — release and boot a fresh one
        release_worker(project_id)
        worker = await asyncio.to_thread(get_or_create_worker, project_id)
        sandbox_id = worker.sandbox_id
        if sandbox_id and project.fly_sandbox_id != sandbox_id:
            project.fly_sandbox_id = sandbox_id
            project.updated_at = datetime.utcnow()
            db.commit()

    # ── Fresh path: new/recycled sandbox ─────────────────────────────────────
    # setup_vite and start_vite are both no-ops for NF/Fly containers (Vite starts
    # via start.sh on boot). start_vite just returns the public preview URL.
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Setting up project environment..."
    })
    await asyncio.to_thread(worker.execute, "setup_vite")

    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Starting preview server..."
    })
    preview_url = await asyncio.to_thread(worker.execute, "start_vite")

    # If this project already has persisted files, avoid early preview promotion
    # until restore and compile checks complete, to prevent transient Vite overlays.
    _stored_file_count = await asyncio.to_thread(
        lambda: db.query(File).filter(File.project_id == project_id).count()
    )
    _allow_early_scaffold = _stored_file_count == 0

    # Show the scaffold iframe immediately once Vite confirms it is serving.
    # The scaffold "🚀 Preview Ready" page is pre-compiled at image build time, so
    # this wait_vite_ready should resolve in seconds. For returning users the scaffold
    # showing briefly (before their files load via HMR) is better than a blank panel.
    if _allow_early_scaffold:
        try:
            await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
            await _send_json(websocket, {
                "type": "sandbox_ready",
                "previewUrl": preview_url,
            })
        except Exception as _early_e:
            print(f"[sandbox] Scaffold not ready in 20s (continuing to user-file restore): {_early_e}")
    else:
        await _send_json(websocket, {
            "type": "status", "status": "booting_sandbox",
            "message": "Restoring project files before preview..."
        })

    # Replay persisted files into sandbox. Done AFTER the early sandbox_ready so the
    # user gets visual feedback immediately. Vite HMR recompiles them in the background.
    stored_files = _load_project_files(db, project_id)
    if stored_files:
        db_fallback = {f.file_path: f.content for f in stored_files if f.content}
        file_paths = [f.file_path for f in stored_files]
        contents = await storage_service.download_project_files(
            project_id, file_paths, db_fallback=db_fallback
        )
        # Only write files with non-empty content — an empty file written to the sandbox
        # causes Vite to return 500 when it tries to compile it (e.g. empty App.tsx).
        batch = [
            {"file_path": fp, "content": contents.get(fp, "")}
            for fp in file_paths
            if contents.get(fp, "").strip()
        ]
        skipped = [fp for fp in file_paths if not contents.get(fp, "").strip()]
        if skipped:
            print(f"[sandbox] Skipping {len(skipped)} empty/missing file(s): {skipped[:5]}")
        if batch:
            await asyncio.to_thread(worker.execute, "write_files", batch)

    # Wait for Vite to finish compiling with user files.
    # For new projects (no user files) this returns immediately.
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Compiling preview..."
    })
    try:
        await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
    except Exception as e:
        print(f"[sandbox] wait_vite_ready timed out (non-fatal): {e}")

    # Fail closed after restore on fresh path as well.
    _fresh_errors = []
    try:
        _fresh_errors = await asyncio.to_thread(worker.execute, "check_vite_errors") or []
    except Exception as _fresh_check_err:
        print(f"[sandbox] Fresh check_vite_errors failed; applying fallback: {_fresh_check_err}")
        _fresh_errors = [{"file": "unknown", "error": f"vite_check_failed: {_fresh_check_err}"}]

    if _fresh_errors:
        print(f"[sandbox] Fresh path has {len(_fresh_errors)} Vite error(s); applying fallback")
        await _persist_files(db, project_id, _GOLDEN_FALLBACK_EDITS)
        await asyncio.to_thread(worker.execute, "write_files", _GOLDEN_FALLBACK_EDITS)
        try:
            await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
        except Exception as _fwe:
            print(f"[sandbox] Fresh fallback wait_vite_ready timeout: {_fwe}")
        await _send_json(websocket, {
            "type": "status", "status": "warning",
            "message": "⚠️ Generated files had build errors. Showing a safe placeholder.",
        })

    # Persist preview URL
    project.preview_url = preview_url
    project.updated_at = datetime.utcnow()
    db.commit()

    return worker, preview_url


# ── REST: Auto-save endpoint ────────────────────────────────────────────────
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import User

class FileSavePayload(BaseModel):
    files: dict[str, str]  # {file_path: content}

@app.post("/api/v1/projects/{project_id}/save")
async def save_project_files(
    project_id: str,
    body: FileSavePayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    edits = [{"file_path": fp, "content": c} for fp, c in body.files.items()]
    edits = _sanitize_tsx_write_edits(_sanitize_css_write_edits(edits))
    try:
        await _persist_files(db, project_id, edits)
    except Exception as e:
        print(f"[save] Storage upload error (non-fatal, DB metadata saved): {e}")
    project.updated_at = datetime.utcnow()
    db.commit()

    # Write saved files to sandbox so preview reflects changes immediately
    if edits:
        try:
            worker = await asyncio.to_thread(get_or_create_worker, project_id)
            batch = [{"file_path": e["file_path"], "content": e.get("content", "")} for e in edits]
            if batch:
                if not worker.is_alive:
                    try:
                        await asyncio.to_thread(worker.execute, "start_vite")
                    except Exception as ve:
                        print(f"[save] start_vite before write (non-fatal): {ve}")

                try:
                    await asyncio.to_thread(worker.execute, "write_files", batch)
                except Exception as sb_err:
                    err_str = str(sb_err).lower()
                    if "3006" in err_str or "timed out" in err_str or "not alive" in err_str:
                        print(f"[save] Sandbox write failed ({err_str}), attempting sandbox recovery...")
                        release_worker(project_id)
                        worker = await asyncio.to_thread(get_or_create_worker, project_id)
                        await asyncio.to_thread(worker.execute, "start_vite")
                        await asyncio.to_thread(worker.execute, "write_files", batch)
                    else:
                        raise sb_err

                # Wait for Vite to rebuild so frontend reload shows updated UI
                try:
                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 30.0)
                except Exception as ve:
                    print(f"[save] wait_vite_ready (non-fatal): {ve}")

                # Notify active editor sessions to force-reload preview after save.
                try:
                    from redis_state import publish_project_update

                    reload_payload = {"type": "reload_preview"}
                    if worker.preview_url:
                        reload_payload["url"] = worker.preview_url
                    await publish_project_update(project_id, reload_payload)
                except Exception as pe:
                    print(f"[save] publish reload_preview failed (non-fatal): {pe}")
        except Exception as e:
            print(f"[save] Sandbox write error (non-fatal): {e}")

    return {"saved": len(edits)}


# ── Sandbox warm-up endpoint ─────────────────────────────────────────────────

@app.post("/api/v1/projects/{project_id}/sandbox/warm")
async def warm_sandbox(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fire-and-forget: pre-provision a Fly sandbox via Inngest background job.

    The client can subscribe to the WebSocket (or poll) for sandbox/ready events
    on the Redis pub/sub channel kith:sandbox:{project_id}:events.
    """
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    if use_inngest():
        import inngest
        await _inngest_client.client.send(
            inngest.Event(
                name="sandbox/provision.requested",
                data={"project_id": project_id},
            )
        )
        return {"status": "provisioning"}

    # Inngest disabled — provision synchronously in background thread (dev only)
    async def _provision():
        from nf_service import get_or_create_worker
        try:
            await asyncio.to_thread(get_or_create_worker, project_id)
        except Exception as e:
            print(f"[warm_sandbox] Background provision failed: {e}")

    asyncio.create_task(_provision())
    return {"status": "provisioning"}


# ── WebSocket: fire-and-forget step source ────────────────────────────────────
# In production (Inngest enabled) the LLM pipeline runs in an Inngest worker;
# the WS handler subscribes to per-job Redis pub/sub and only proxies messages,
# freeing the uvicorn worker for new connections.
# In dev mode the pipeline runs inline as before.

async def _step_stream(
    user_prompt: str,
    project_id: str,
    model_id: str,
    db,
    images: list,
    user_id: str | None,
):
    # Chat/code generation always runs inline — Inngest is only used for
    # long-running background jobs (C-Suite, Design, Artifacts), not for
    # real-time WebSocket streaming (no handler exists for chat/message.requested).
    #
    # Phase 2: Route code generation through the multi-agent pipeline
    # (Intent → Layout → Component → Code), while conversation stays
    # on the fast path.

    # 1. Resolve credentials + classify intent
    effective_model, llm_kwargs = await _resolve_llm_credentials(model_id, user_id)

    intent_class = await classify_intent(user_prompt, effective_model, llm_kwargs)

    if intent_class == "conversation":
        # Conversation mode — fast path (no pipeline needed)
        async for step in process_conversation(
            user_prompt, project_id, effective_model, llm_kwargs, db=db, images=images
        ):
            yield step
        return

    # 2. Code generation — run multi-agent pipeline
    from agent_pipeline import run_multi_agent_pipeline
    async for step in run_multi_agent_pipeline(
        user_prompt, project_id, effective_model, llm_kwargs, db,
        images=images, user_id=user_id,
    ):
        yield step


# ── WebSocket: Chat + Code Gen ──────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    db = SessionLocal()
    project_id = websocket.query_params.get("project_id")
    worker = None

    if not project_id:
        await _send_json(websocket, {"type": "error", "message": "Missing project_id in WebSocket query"})
        await websocket.close(code=4400)
        db.close()
        return

    user = await get_current_user_ws(websocket, db)
    if not user:
        await _send_json(websocket, {"type": "error", "message": "Authentication failed"})
        await websocket.close(code=4401)
        db.close()
        return

    # ── Connection rate limiting: max 10 concurrent WS sessions per user ──────
    from redis_client import get_async_redis as _gar
    _rl = _gar()
    _conn_key = f"kith:ws:conn:{user.id}"
    _MAX_WS_CONNS = 10
    try:
        _conn_n = await _rl.incr(_conn_key)
        await _rl.expire(_conn_key, 3600)
        # Safety cap: stale counts from crashed workers can accumulate; clamp to max.
        if _conn_n > _MAX_WS_CONNS:
            await _rl.set(_conn_key, _MAX_WS_CONNS, ex=3600)
            _conn_n = _MAX_WS_CONNS
    except Exception:
        _conn_n = 1  # Redis unavailable — allow through, skip rate-limiting
    if _conn_n > _MAX_WS_CONNS:
        try:
            await _rl.decr(_conn_key)
        except Exception:
            pass
        await _send_json(websocket, {
            "type": "error",
            "message": f"Too many concurrent connections (max {_MAX_WS_CONNS}). Close another tab first."
        })
        await websocket.close(code=4429)
        db.close()
        return

    project = await asyncio.to_thread(
        lambda: db.query(Project).filter(
            Project.id == project_id, Project.user_id == user.id
        ).first()
    )
    if not project:
        try:
            await _rl.decr(_conn_key)
        except Exception:
            pass
        await _send_json(websocket, {"type": "error", "message": "Project not found"})
        await websocket.close(code=4404)
        db.close()
        return

    try:
        # Count existing files
        file_count = await asyncio.to_thread(
            lambda: db.query(File).filter(File.project_id == project_id).count()
        )

        # Boot sandbox worker, restore files, start Vite
        worker, preview_url = await _ensure_sandbox_ready(websocket, db, project, project_id)

        # Send sandbox_ready with preview URL
        await _send_json(websocket, {
            "type": "sandbox_ready",
            "previewUrl": preview_url,
            "fileCount": file_count,
        })

        # Build file tree from DB and send
        db_tree = await asyncio.to_thread(_build_file_tree_from_db, db, project_id)
        if db_tree:
            await _send_json(websocket, {
                "type": "file_tree",
                "tree": db_tree
            })

        # Restore files + chat history to frontend
        await _restore_project_state(websocket, db, project_id)

        # If the project already has files, wait for Vite to finish compiling
        # then reload the preview so the user sees their app — not the placeholder.
        if file_count > 0 and worker and preview_url:
            try:
                await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
            except Exception:
                pass  # non-fatal — preview may still load

            # Promotion gate on reconnect: never surface a broken overlay page.
            _reconnect_errors = []
            try:
                _reconnect_errors = await asyncio.to_thread(worker.execute, "check_vite_errors") or []
            except Exception as _rce:
                print(f"[ws] Reconnect Vite check failed; forcing fallback: {_rce}")
                _reconnect_errors = [{"file": "unknown", "error": f"vite_check_failed: {_rce}"}]

            if _reconnect_errors:
                print(f"[ws] Reconnect found Vite errors in {len(_reconnect_errors)} file(s); applying golden fallback")
                _fallback = _GOLDEN_FALLBACK_EDITS
                await _persist_files(db, project_id, _fallback)
                await asyncio.to_thread(worker.execute, "write_files", _fallback)
                try:
                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
                except Exception as _rwe:
                    print(f"[ws] Reconnect fallback wait_vite_ready timeout: {_rwe}")
                await _send_json(websocket, {
                    "type": "status", "status": "warning",
                    "message": "⚠️ Existing project files had a build error. Showing a safe placeholder while you regenerate.",
                })

            await _send_json(websocket, {
                "type": "reload_preview",
                "url": preview_url,
            })

        await _send_json(websocket, {"type": "status", "status": "idle"})

    except Exception as init_err:
        print(f"[init] Error (non-fatal): {init_err}")
        # Ensure hasExistingFiles is set so the UI doesn't wait forever on sandbox_ready
        await _send_json(websocket, {
            "type": "sandbox_failed",
            "message": "Sandbox couldn't start. You can still use the editor, or retry below.",
        })
        await _send_json(websocket, {"type": "status", "status": "idle"})

    # ── Redis pub/sub relay: forward cross-worker events to this WS client ──
    async def _redis_relay():
        from redis_state import project_channel, get_async_redis
        r = get_async_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(project_channel(project_id))
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    try:
                        payload = json.loads(message["data"])
                        await _send_json(websocket, payload)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(project_channel(project_id))
            await pubsub.aclose()

    redis_relay_task = asyncio.create_task(_redis_relay())

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            # ── Auto-fix: handle preview errors ──────────────────────────
            if payload.get("type") == "preview_error":
                errors = payload.get("errors", [])
                if errors and worker and worker.is_alive:
                    await _send_json(websocket, {
                        "type": "auto_fix_status", "status": "fixing",
                        "message": "🔧 Auto-fixing..."
                    })
                    try:
                        fix_result = await attempt_fix(project_id, errors, user_id=user.id)
                        if fix_result and fix_result.get("files"):
                            fix_edits = [
                                {"file_path": f["file_path"], "content": f["content"], "action": "write"}
                                for f in fix_result["files"]
                            ]
                            fix_edits = _sanitize_tsx_write_edits(_sanitize_css_write_edits(fix_edits))
                            await _persist_files(db, project_id, fix_edits)
                            for edit in fix_edits:
                                await _send_json(websocket, {
                                    "type": "file_written",
                                    "file": edit["file_path"],
                                    "content": edit["content"]
                                })
                            try:
                                await asyncio.to_thread(worker.execute, "write_files", fix_edits)
                            except Exception as sb_err:
                                err_str = str(sb_err).lower()
                                if "3006" in err_str or "timed out" in err_str or "not alive" in err_str:
                                    print(f"[sandbox] Auto-fix write failed ({err_str}), attempting sandbox recovery...")
                                    release_worker(project_id)
                                    worker, preview_url = await _ensure_sandbox_ready(websocket, db, project, project_id)
                                    await asyncio.to_thread(worker.execute, "write_files", fix_edits)
                                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
                                    await _send_json(websocket, {
                                        "type": "sandbox_ready",
                                        "previewUrl": preview_url,
                                        "fileCount": len(fix_edits),
                                    })
                                else:
                                    raise sb_err
                            db_tree = _build_file_tree_from_db(db, project_id)
                            if db_tree:
                                await _send_json(websocket, {"type": "file_tree", "tree": db_tree})
                            # Wait for Vite to be fully ready before reloading
                            try:
                                await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
                            except Exception:
                                pass

                            # Do not promote a preview that still has compile errors.
                            _post_fix_errors = []
                            try:
                                _post_fix_errors = await asyncio.to_thread(worker.execute, "check_vite_errors") or []
                            except Exception as _pfe:
                                print(f"[ws] Post-fix Vite check failed; forcing fallback: {_pfe}")
                                _post_fix_errors = [{"file": "unknown", "error": f"vite_check_failed: {_pfe}"}]
                            if _post_fix_errors:
                                print(f"[ws] Auto-fix path still has {len(_post_fix_errors)} Vite error(s); applying fallback")
                                _fallback = _GOLDEN_FALLBACK_EDITS
                                await _persist_files(db, project_id, _fallback)
                                await asyncio.to_thread(worker.execute, "write_files", _fallback)
                                try:
                                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
                                except Exception as _pfwe:
                                    print(f"[ws] Post-fix fallback wait_vite_ready timeout: {_pfwe}")

                            await _send_json(websocket, {"type": "reload_preview"})
                            await _send_json(websocket, {
                                "type": "auto_fix_status", "status": "fixed",
                                "message": f"🔧 Auto-fixed {len(fix_edits)} file(s)"
                            })
                            _persist_message(db, project_id, "system",
                                f"[auto-fix] Fixed {len(fix_edits)} file(s): {', '.join(e['file_path'] for e in fix_edits)}")
                        else:
                            await _send_json(websocket, {
                                "type": "auto_fix_status", "status": "skipped"
                            })
                    except Exception as fix_err:
                        print(f"[auto-fix] Failed: {fix_err}")
                        await _send_json(websocket, {
                            "type": "auto_fix_status", "status": "failed"
                        })
                continue

            # ── Normal user prompt ───────────────────────────────────────
            user_prompt = payload.get("prompt")
            model_id = payload.get("model", "default")
            images = payload.get("images", [])

            if not user_prompt and not images:
                continue

            # Reset auto-fix cycle on user-initiated edits
            reset_fix_cycle(project_id)

            # ── Message rate limiting: max 30 messages/minute per user ─────────
            _msg_key = f"kith:ws:msgs:{user.id}"
            try:
                _msg_n = await _rl.incr(_msg_key)
                if _msg_n == 1:
                    await _rl.expire(_msg_key, 60)
            except Exception:
                _msg_n = 1  # Redis unavailable — allow through
            if _msg_n > 30:
                await _send_json(websocket, {
                    "type": "error",
                    "message": "Rate limit exceeded (30 messages/min). Please wait."
                })
                await _send_json(websocket, {"type": "status", "status": "idle"})
                continue

            try:
                await asyncio.to_thread(_persist_message, db, project_id, "user", user_prompt or f"[{len(images)} image(s)]")

                # Refresh project
                project = await asyncio.to_thread(
                    lambda: db.query(Project).filter(Project.id == project_id).first()
                )

                preview_url = worker.preview_url if worker and worker.preview_url else (project.preview_url if project else "")
                _cur_file_count = await asyncio.to_thread(
                    lambda: db.query(File).filter(File.project_id == project_id).count()
                )
                await _send_json(websocket, {
                    "type": "sandbox_ready",
                    "previewUrl": preview_url,
                    "fileCount": _cur_file_count,
                })

                # Send file tree from DB
                db_tree = await asyncio.to_thread(_build_file_tree_from_db, db, project_id)
                if db_tree:
                    await _send_json(websocket, {"type": "file_tree", "tree": db_tree})

                # Process user request — reads files from DB
                async for step in _step_stream(user_prompt, project_id, model_id, db=db, images=images, user_id=user.id):
                    if step["status"] == "file_stream_start":
                        await _send_json(websocket, {
                            "type": "file_stream_start", "file": step["file"]
                        })
                    elif step["status"] == "code_token":
                        await _send_json(websocket, {
                            "type": "code_token", "file": step["file"], "token": step["token"]
                        })
                    elif step["status"] == "file_stream_end":
                        await _send_json(websocket, {
                            "type": "file_stream_end", "file": step["file"], "content": step["content"]
                        })
                    elif step["status"] == "stream_end":
                        await _send_json(websocket, {"type": "stream_end"})
                    elif step["status"] == "validation_warning":
                        # AST Patch Safety results (Phase 5)
                        await _send_json(websocket, {
                            "type": "validation_warning",
                            "message": step.get("message", ""),
                            "errors": step.get("errors", []),
                        })
                    elif step["status"] == "chat_token":
                        await _send_json(websocket, {
                            "type": "chat_token", "token": step["token"]
                        })
                    elif step["status"] == "chat_complete":
                        await _send_json(websocket, {
                            "type": "chat_complete", "message": step["message"]
                        })
                        await asyncio.to_thread(_persist_message, db, project_id, "assistant", step["message"])
                    elif step["status"] == "execution_complete":
                        edits = step.get("edits", [])
                        write_edits = [e for e in edits if e.get("action") == "write"]
                        write_edits = _sanitize_tsx_write_edits(_sanitize_css_write_edits(write_edits))

                        if write_edits:
                            await _send_json(websocket, {
                                "type": "status", "status": "applying_edits",
                                "message": f"Saving {len(write_edits)} files..."
                            })

                            # 1. Persist to Storage (best-effort — NEVER blocks sandbox write)
                            storage_save_error = None
                            try:
                                await _persist_files(db, project_id, write_edits)
                            except Exception as _se:
                                storage_save_error = _se
                                print(f"[ws] Storage save failed (sandbox write will still proceed): {_se}")

                            # 2. Notify frontend
                            for edit in write_edits:
                                await _send_json(websocket, {
                                    "type": "file_written",
                                    "file": edit["file_path"],
                                    "content": edit["content"]
                                })

                            # 3. Update file tree
                            db_tree = await asyncio.to_thread(_build_file_tree_from_db, db, project_id)
                            if db_tree:
                                await _send_json(websocket, {"type": "file_tree", "tree": db_tree})

                            # 4. Write to sandbox (Vite HMR auto-reloads)
                            if worker and worker.is_alive:
                                reset_fix_cycle(project_id)
                                try:
                                    try:
                                        await asyncio.to_thread(worker.execute, "write_files", write_edits)
                                        # Poll until @vite/client and @react-refresh both return 200
                                        await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)

                                        _purl = worker.preview_url if worker.preview_url else (project.preview_url or "")

                                        # Promotion gate: check compilation BEFORE showing the preview.
                                        # sandbox_ready / reload_preview are sent only after the build
                                        # is confirmed clean (or replaced with a safe fallback).
                                        _build_clean = True
                                        try:
                                            vite_errors = await asyncio.to_thread(worker.execute, "check_vite_errors") or []
                                            if vite_errors and isinstance(vite_errors, list):
                                                _build_clean = False
                                                print(f"[ws] Vite compilation errors in {len(vite_errors)} file(s): {[e.get('file', 'unknown') for e in vite_errors]}")
                                                await _send_json(websocket, {
                                                    "type": "status", "status": "warning",
                                                    "message": f"⚠️ Fixing compilation error(s) in {len(vite_errors)} file(s)..."
                                                })
                                                error_events = [
                                                    {
                                                        "source": "vite",
                                                        "message": f"Compilation error in {e['file']}: {e['error'][:400]}",
                                                    }
                                                    for e in vite_errors
                                                ]
                                                fix_result = await attempt_fix(project_id, error_events, user_id=user.id)
                                                if fix_result and fix_result.get("files"):
                                                    fix_edits = [
                                                        {"file_path": f["file_path"], "content": f["content"], "action": "write"}
                                                        for f in fix_result["files"]
                                                    ]
                                                    fix_edits = _sanitize_tsx_write_edits(_sanitize_css_write_edits(fix_edits))
                                                    await _persist_files(db, project_id, fix_edits)
                                                    for edit in fix_edits:
                                                        await _send_json(websocket, {
                                                            "type": "file_written",
                                                            "file": edit["file_path"],
                                                            "content": edit["content"],
                                                        })
                                                    await asyncio.to_thread(worker.execute, "write_files", fix_edits)
                                                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 30.0)
                                                    # Verify again after attempted fix.
                                                    _post_fix_errors = []
                                                    try:
                                                        _post_fix_errors = await asyncio.to_thread(worker.execute, "check_vite_errors") or []
                                                    except Exception as _pf_check_err:
                                                        print(f"[ws] Post-fix Vite check failed; forcing fallback: {_pf_check_err}")
                                                        _post_fix_errors = [{"file": "unknown", "error": f"vite_check_failed: {_pf_check_err}"}]
                                                    if _post_fix_errors:
                                                        _build_clean = False
                                                    else:
                                                        _build_clean = True
                                                    await _send_json(websocket, {
                                                        "type": "auto_fix_status", "status": "fixed",
                                                        "message": f"🔧 Auto-fixed {len(fix_edits)} file(s)"
                                                    })

                                                if not _build_clean:
                                                    # Auto-fix produced nothing — guarantee a working preview
                                                    # by writing the golden fallback so the user never sees
                                                    # a blank or erroring iframe.
                                                    print("[ws] Auto-fix failed or unresolved; applying golden fallback")
                                                    _fallback = _GOLDEN_FALLBACK_EDITS
                                                    await _persist_files(db, project_id, _fallback)
                                                    for edit in _fallback:
                                                        await _send_json(websocket, {
                                                            "type": "file_written",
                                                            "file": edit["file_path"],
                                                            "content": edit["content"],
                                                        })
                                                    await asyncio.to_thread(worker.execute, "write_files", _fallback)
                                                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
                                                    _build_clean = True
                                                    await _send_json(websocket, {
                                                        "type": "status", "status": "warning",
                                                        "message": "⚠️ Build error couldn't be auto-repaired. Showing a safe placeholder — describe what you want and I'll regenerate.",
                                                    })
                                        except Exception as _ce:
                                            # If we can't verify the build, fail closed to safe fallback.
                                            print(f"[ws] Vite error check failed; applying fallback: {_ce}")
                                            _fallback = _GOLDEN_FALLBACK_EDITS
                                            await _persist_files(db, project_id, _fallback)
                                            for edit in _fallback:
                                                await _send_json(websocket, {
                                                    "type": "file_written",
                                                    "file": edit["file_path"],
                                                    "content": edit["content"],
                                                })
                                            await asyncio.to_thread(worker.execute, "write_files", _fallback)
                                            try:
                                                await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 20.0)
                                            except Exception as _ce_wait:
                                                print(f"[ws] Fallback wait_vite_ready timeout: {_ce_wait}")
                                            _build_clean = True
                                            await _send_json(websocket, {
                                                "type": "status", "status": "warning",
                                                "message": "⚠️ Build verification failed. Showing a safe placeholder preview.",
                                            })

                                        # Only now is the preview safe to show.
                                        if _purl:
                                            await _send_json(websocket, {
                                                "type": "sandbox_ready",
                                                "previewUrl": _purl,
                                            })
                                        await _send_json(websocket, {"type": "reload_preview"})

                                    except Exception as sb_err:
                                        err_str = str(sb_err).lower()
                                        if "3006" in err_str or "timed out" in err_str or "thread crashed" in err_str:
                                            print(f"[sandbox] Write error ({err_str}), attempting sandbox recovery...")
                                            # Force release the dead worker before recovery
                                            release_worker(project_id)
                                            worker, preview_url = await _ensure_sandbox_ready(websocket, db, project, project_id)
                                            await asyncio.to_thread(worker.execute, "write_files", write_edits)
                                            await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
                                            # Send updated preview URL to frontend
                                            await _send_json(websocket, {
                                                "type": "sandbox_ready",
                                                "previewUrl": preview_url,
                                                "fileCount": len(write_edits),
                                            })
                                            await _send_json(websocket, {"type": "reload_preview"})
                                        else:
                                            raise sb_err
                                except Exception as sb_err:
                                    import traceback
                                    with open("debug_sb_err.txt", "w") as f:
                                        f.write(traceback.format_exc())
                                    print(f"[sandbox] Write error (files saved to DB): {sb_err}")
                                    await _send_json(websocket, {
                                        "type": "status", "status": "warning",
                                        "message": "Files saved, but sandbox write failed. Preview may not update."
                                    })

                            # 5. Surface storage warning last (after sandbox is already updated)
                            if storage_save_error:
                                await _send_json(websocket, {
                                    "type": "status", "status": "warning",
                                    "message": "⚠️ Files loaded in preview, but cloud save hit a network issue. Your work is in the editor — try saving again shortly."
                                })

                            # 6. Populate Project Brain (non-blocking, non-fatal)
                            try:
                                from agent_pipeline import populate_brain_from_edits
                                await asyncio.to_thread(
                                    populate_brain_from_edits,
                                    db, project_id, write_edits,
                                )
                            except Exception as _be:
                                print(f"[brain] Post-gen population skipped: {_be}")
                    else:
                        await _send_json(websocket, {
                            "type": "agent_status", "data": step
                        })
                        _TRANSIENT = {"analyzing", "reading", "generating"}
                        if step.get("message") and step.get("status") not in _TRANSIENT:
                            await asyncio.to_thread(_persist_message, db, project_id, "system", step["message"])

                await _send_json(websocket, {"type": "status", "status": "idle"})

            except Exception as loop_err:
                print(f"[ws] Request error: {loop_err}")
                await _send_json(websocket, {
                    "type": "error",
                    "message": _user_visible_error_message(loop_err)
                })
                await asyncio.to_thread(_persist_message, db, project_id, "system", f"Error: {str(loop_err)}")
                await _send_json(websocket, {
                    "type": "status", "status": "idle",
                    "message": "Waiting for input..."
                })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        redis_relay_task.cancel()
        try:
            await redis_relay_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await _rl.decr(_conn_key)
        except Exception:
            pass
        # Keep sandbox alive across reconnects — only release on explicit project deletion
        db.close()


# ── Cloudflare: Turnstile CAPTCHA verification ────────────────────────────────

@app.post("/api/turnstile/verify")
async def turnstile_verify(request: Request):
    """Verify a Cloudflare Turnstile CAPTCHA token server-side.

    Body: {"token": "<turnstile_response_token>"}
    Returns 200 {"ok": true} on success or 403 on failure.
    Empty/missing site key → always returns ok (safe dev fallback).
    """
    body = await request.json()
    token = (body.get("token") or "").strip()
    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Missing turnstile token")

    remote_ip = request.client.host if request.client else None
    from cloudflare import verify_turnstile
    ok = await verify_turnstile(token, remote_ip)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Turnstile verification failed")
    return {"ok": True}


# ── Cloudflare: Security setup + analytics ────────────────────────────────────

@app.post("/api/cloudflare/setup-security")
async def cloudflare_setup_security(request: Request):
    """Configure rate-limit + WAF rules on the Cloudflare zone.

    Protected: requires the X-Admin-Key header matching FLY_BRIDGE_SECRET
    (or any secret you choose; this is an admin-only endpoint).
    """
    expected = os.getenv("FLY_BRIDGE_SECRET", "")
    if expected:
        key = request.headers.get("X-Admin-Key", "")
        if key != expected:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Forbidden")

    from cloudflare import setup_rate_limit_rules, setup_waf_rules
    rl_results = await setup_rate_limit_rules()
    waf_results = await setup_waf_rules()

    needs_permissions = any(isinstance(r, dict) and "error" in r for r in rl_results + waf_results)
    return {
        "ok": True,
        "rate_limit_rules": rl_results,
        "waf_rules": waf_results,
        "permission_note": (
            "Update your Cloudflare API token to include 'Zone Rulesets Edit' permission"
            if needs_permissions else None
        ),
    }


@app.get("/api/cloudflare/zone-info")
async def cloudflare_zone_info(request: Request):
    """Fetch zone info + analytics from Cloudflare. Admin only."""
    expected = os.getenv("FLY_BRIDGE_SECRET", "")
    if expected:
        key = request.headers.get("X-Admin-Key", "")
        if key != expected:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Forbidden")

    from cloudflare import get_zone_info, get_zone_analytics
    zone = await get_zone_info()
    analytics = await get_zone_analytics(since_minutes=1440)
    return {"zone": zone, "analytics": analytics}


if __name__ == "__main__":
    import uvicorn
    # Single-worker dev mode. For production use Gunicorn:
    #   cd backend && gunicorn main:app -c gunicorn_config.py
    uvicorn.run("main:app", host="0.0.0.0", port=_PORT, reload=True)
