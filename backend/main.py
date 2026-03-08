import os
import sys

# Fix Anaconda SSL_CERT_FILE pointing to a non-existent path.
# Conda activation scripts set this env var, but the cert file may not exist
# in the venv or the path may be stale — causing FileNotFoundError in ssl.py.
for _ssl_var in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
    _val = os.environ.get(_ssl_var, "")
    if _val and not os.path.exists(_val):
        del os.environ[_ssl_var]

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()
import uuid
import signal
import atexit
import socket
import subprocess
from datetime import datetime
from agent import process_user_request
from error_resolver import attempt_fix, reset_fix_cycle

from fly_service import get_or_create_worker, release_worker
from models import Base, engine, SessionLocal, Project, File, Message, get_db
from auth import get_current_user_ws, get_current_user
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
Base.metadata.create_all(bind=engine)
storage_service.ensure_bucket_exists()

app = FastAPI()

# Allow all origins in development — restricts to explicit list in production.
# Covers localhost, WSL IPs (172.x.x.x / 192.168.x.x) and any other dev hostname.
_PROD_ORIGINS = [
    "https://kith-foundry.fly.dev",  # update with your prod domain
]
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
import routing_api
app.include_router(routing_api.router)

# ── Inngest — durable background jobs ────────────────────────────────────────
from inngest.fast_api import serve as _inngest_serve
import inngest_functions as _inngest_fns
import inngest_client as _inngest_client
_inngest_serve(app, _inngest_client.client, _inngest_fns.all_functions)


@app.on_event("startup")
async def _inngest_dev_sync():
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
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            # Check Dev Server is up
            ping = await client.get(dev_server, timeout=2)
            if ping.status_code >= 400:
                raise RuntimeError(f"Dev Server returned {ping.status_code}")
            print(f"✅ Inngest Dev Server reachable at {dev_server}")
            # Trigger SDK sync: Dev Server polls our /api/inngest automatically
            # when started with -u flag. No action needed here.
            print(f"📡 Inngest functions registered at {app_url}")
    except Exception as e:
        print(f"⚠️  Inngest Dev Server not reachable ({e})")
        print(f"   Start it with: npx inngest-cli@latest dev -u {app_url}")


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
    stored_files = db.query(File).filter(File.project_id == project_id).order_by(File.file_path.asc()).all()
    if stored_files:
        # Build fallback map for legacy rows that still have content in DB
        db_fallback = {f.file_path: f.content for f in stored_files if f.content}
        file_paths = [f.file_path for f in stored_files]
        # Download content from Supabase Storage (falls back to DB content for legacy rows)
        contents = await storage_service.download_project_files(
            project_id, file_paths, db_fallback=db_fallback
        )
        for file_row in stored_files:
            await _send_json(websocket, {
                "type": "file_written",
                "file": file_row.file_path,
                "content": contents.get(file_row.file_path, ""),
            })

    # Purge stale transient messages
    all_messages = db.query(Message).filter(Message.project_id == project_id).order_by(Message.created_at.asc()).all()
    clean_history = []
    for m in all_messages:
        if m.role == "system" and _is_transient(m.content or ""):
            db.delete(m)
        else:
            clean_history.append({"role": m.role, "content": m.content})
    db.commit()

    await _send_json(websocket, {
        "type": "message_history",
        "messages": clean_history,
    })


async def _ensure_sandbox_ready(websocket, db, project, project_id: str) -> tuple:
    """Boot or reuse a sandbox worker, restore files, start Vite, return (worker, preview_url)."""
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Booting secure sandbox..."
    })

    # Get or create sandbox worker (runs on dedicated thread)
    worker = await asyncio.to_thread(get_or_create_worker, project_id)

    # Store sandbox_id on project
    sandbox_id = worker.sandbox_id
    if sandbox_id and project.fly_sandbox_id != sandbox_id:
        project.fly_sandbox_id = sandbox_id
        project.updated_at = datetime.utcnow()
        db.commit()

    # If this worker already has Vite running, verify it's still alive before reusing
    if worker.preview_url:
        try:
            health = await asyncio.to_thread(worker.execute, "health_check", None, 10.0)
            if health == "ok":
                # Reusing worker — but we must restore files so the preview shows current
                # state (not scaffold) after refresh/re-login. Fly machines can be recycled.
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
                        await _send_json(websocket, {
                            "type": "status", "status": "booting_sandbox",
                            "message": "Syncing project files..."
                        })
                        try:
                            await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
                        except Exception as e:
                            print(f"[sandbox] wait_vite_ready after reuse restore timed out: {e}")
                print(f"[sandbox] Reusing existing sandbox {worker.sandbox_id}, Vite healthy at {worker.preview_url}")
                return worker, worker.preview_url
            else:
                print(f"[sandbox] Sandbox {worker.sandbox_id} unhealthy ({health}), recreating...")
        except Exception as e:
            print(f"[sandbox] Sandbox {worker.sandbox_id} health check failed ({e}), recreating...")

        # Sandbox is dead — release and create a fresh one
        release_worker(project_id)
        worker = await asyncio.to_thread(get_or_create_worker, project_id)
        sandbox_id = worker.sandbox_id
        if sandbox_id and project.fly_sandbox_id != sandbox_id:
            project.fly_sandbox_id = sandbox_id
            project.updated_at = datetime.utcnow()
            db.commit()

    # Setup Vite project (npm install etc.)
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Setting up project environment..."
    })
    await asyncio.to_thread(worker.execute, "setup_vite")

    # Replay persisted files into sandbox (content from Supabase Storage)
    stored_files = _load_project_files(db, project_id)
    if stored_files:
        db_fallback = {f.file_path: f.content for f in stored_files if f.content}
        file_paths = [f.file_path for f in stored_files]
        contents = await storage_service.download_project_files(
            project_id, file_paths, db_fallback=db_fallback
        )
        # Only write files with non-empty content — an empty file written to the sandbox
        # causes Vite to return 500 when it tries to compile it (e.g. empty App.tsx).
        # The placeholder files written by setup_vite() serve as safe fallbacks.
        batch = [
            {"file_path": fp, "content": contents.get(fp, "")}
            for fp in file_paths
            if contents.get(fp, "").strip()
        ]
        skipped = [fp for fp in file_paths if not contents.get(fp, "").strip()]
        if skipped:
            print(f"[sandbox] Skipping {len(skipped)} empty/missing file(s) from Storage restore: {skipped[:5]}")
        if batch:
            await asyncio.to_thread(worker.execute, "write_files", batch)

    # Start Vite dev server and get preview URL
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Starting preview server..."
    })
    preview_url = await asyncio.to_thread(worker.execute, "start_vite")

    # Wait for Vite to finish initial compilation (especially when user files
    # were restored — Vite needs to compile them before the iframe can show them)
    await _send_json(websocket, {
        "type": "status", "status": "booting_sandbox",
        "message": "Compiling preview..."
    })
    try:
        await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 45.0)
    except Exception as e:
        print(f"[sandbox] wait_vite_ready timed out (non-fatal): {e}")

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
            batch = [{"file_path": e["file_path"], "content": e.get("content", "")} for e in edits if (e.get("content") or "").strip()]
            if batch and worker.is_alive:
                await asyncio.to_thread(worker.execute, "write_files", batch)
                # Wait for Vite to rebuild so frontend reload shows updated UI
                try:
                    await asyncio.to_thread(worker.execute, "wait_vite_ready", None, 30.0)
                except Exception as ve:
                    print(f"[save] wait_vite_ready (non-fatal): {ve}")
        except Exception as e:
            print(f"[save] Sandbox write error (non-fatal): {e}")

    return {"saved": len(edits)}


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

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        await _send_json(websocket, {"type": "error", "message": "Project not found"})
        await websocket.close(code=4404)
        db.close()
        return

    try:
        # Count existing files
        file_count = db.query(File).filter(File.project_id == project_id).count()

        # Boot sandbox worker, restore files, start Vite
        worker, preview_url = await _ensure_sandbox_ready(websocket, db, project, project_id)

        # Send sandbox_ready with preview URL
        await _send_json(websocket, {
            "type": "sandbox_ready",
            "previewUrl": preview_url,
            "fileCount": file_count,
        })

        # Build file tree from DB and send
        db_tree = _build_file_tree_from_db(db, project_id)
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
            await _send_json(websocket, {
                "type": "reload_preview",
                "url": preview_url,
            })

        await _send_json(websocket, {"type": "status", "status": "idle"})

    except Exception as init_err:
        print(f"[init] Error (non-fatal): {init_err}")
        await _send_json(websocket, {
            "type": "status", "status": "idle",
            "message": f"Init issue: {str(init_err)}. You can still use the editor."
        })

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
            model_id = payload.get("model", "claude-3-5-sonnet-latest")
            images = payload.get("images", [])

            if not user_prompt and not images:
                continue

            # Reset auto-fix cycle on user-initiated edits
            reset_fix_cycle(project_id)

            try:
                _persist_message(db, project_id, "user", user_prompt or f"[{len(images)} image(s)]")

                # Refresh project
                project = db.query(Project).filter(Project.id == project_id).first()

                preview_url = project.preview_url if project else ""
                await _send_json(websocket, {
                    "type": "sandbox_ready",
                    "previewUrl": preview_url
                })

                # Send file tree from DB
                db_tree = _build_file_tree_from_db(db, project_id)
                if db_tree:
                    await _send_json(websocket, {"type": "file_tree", "tree": db_tree})

                # Process user request — reads files from DB
                async for step in process_user_request(user_prompt, project_id, model_id, db=db, images=images, user_id=user.id):
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
                    elif step["status"] == "execution_complete":
                        edits = step.get("edits", [])
                        write_edits = [e for e in edits if e.get("action") == "write"]

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
                            db_tree = _build_file_tree_from_db(db, project_id)
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
                    else:
                        await _send_json(websocket, {
                            "type": "agent_status", "data": step
                        })
                        _TRANSIENT = {"analyzing", "reading", "generating"}
                        if step.get("message") and step.get("status") not in _TRANSIENT:
                            _persist_message(db, project_id, "system", step["message"])

                await _send_json(websocket, {"type": "status", "status": "idle"})

            except Exception as loop_err:
                print(f"[ws] Request error: {loop_err}")
                await _send_json(websocket, {
                    "type": "error",
                    "message": _user_visible_error_message(loop_err)
                })
                _persist_message(db, project_id, "system", f"Error: {str(loop_err)}")
                await _send_json(websocket, {
                    "type": "status", "status": "idle",
                    "message": "Waiting for input..."
                })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        # Keep sandbox alive across reconnects — only release on explicit project deletion
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=_PORT, reload=True)
