"""
Northflank Sandbox Service — creates and manages NF deployment services for user project previews.

Replaces fly_service.py.  Uses the Northflank REST API to spin up per-project
deployment services.  Each service runs the same Docker image (bridge + Nginx +
Vite) that was previously deployed on Fly.io.

Architecture
────────────
• One Northflank *project* (NF_PROJECT_ID, default "kith") hosts all sandboxes.
• Each user project gets its own NF *deployment service* named "sb-{8hex}".
• Nginx listens on port 80; Northflank exposes that port publicly and assigns
  a stable DNS: p01--{service-id}--{namespace}.code.run
• The bridge HTTP API is reached via the /__bridge/ path prefix:
    GET/POST https://{dns}/__bridge/health
    POST     https://{dns}/__bridge/write_files
    POST     https://{dns}/__bridge/start_vite
    …
• No IP allocation, no DNS-override trick — NF DNS propagates immediately.

Required environment variables
───────────────────────────────
NF_API_TOKEN       Northflank API token  (falls back to ~/.northflank/config.json)
NF_PROJECT_ID      Northflank project ID (default: kith)
NF_SANDBOX_IMAGE   Docker image for the sandbox (must be accessible by NF)
                   e.g. "docker.io/youruser/kith-sandbox:latest"
NF_SANDBOX_PLAN    Billing plan (default: nf-compute-100-1)
NF_SANDBOX_REGION  Region slug (default: us-east1)
NF_BRIDGE_SECRET   Shared secret forwarded as X-Bridge-Secret header

Public symbols (same interface as fly_service.py)
──────────────────────────────────────────────────
NfSandboxWorker           ← replaces FlySandboxWorker
get_or_create_worker()
release_worker()
cleanup_stale_sandboxes()
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Optional

import requests  # type: ignore[import]

# ── env bootstrap ─────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv  # type: ignore[import]
    _BACKEND_DIR = Path(__file__).resolve().parent
    load_dotenv()
    load_dotenv(_BACKEND_DIR / ".env", override=False)
except Exception:
    pass

NF_API_BASE = "https://api.northflank.com/v1"
NF_PROJECT_ID = os.getenv("NF_PROJECT_ID", "kith")
NF_SANDBOX_PLAN = os.getenv("NF_SANDBOX_PLAN", "nf-compute-100-1")
NF_SANDBOX_REGION = os.getenv("NF_SANDBOX_REGION", "us-east1")
NF_SANDBOX_IMAGE = os.getenv("NF_SANDBOX_IMAGE", "")
NF_BRIDGE_SECRET = os.getenv("NF_BRIDGE_SECRET") or os.getenv("FLY_BRIDGE_SECRET") or secrets.token_urlsafe(32)
SANDBOX_CONTROL_PLANE_URL = os.getenv("SANDBOX_CONTROL_PLANE_URL", "https://api.forgeoperator.com")

# service prefix must match cleanup filter
_SB_PREFIX = "sb-"

# in-process worker cache
_workers: dict[str, "NfSandboxWorker"] = {}
_lock = threading.Lock()
_project_locks: dict[str, threading.Lock] = {}


# ── API token resolution ───────────────────────────────────────────────────────

def _resolve_nf_token() -> str:
    """Read NF_API_TOKEN from env, then fall back to ~/.northflank/config.json."""
    token = os.getenv("NF_API_TOKEN", "").strip()
    if token:
        return token
    try:
        cfg_path = Path.home() / ".northflank" / "config.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text())
            contexts = data.get("contexts", [])
            current = data.get("current", "")
            for ctx in contexts:
                if ctx.get("name") == current or not current:
                    t = ctx.get("token", "").strip()
                    if t:
                        return t
    except Exception:
        pass
    return ""


_NF_TOKEN: str = ""


def _get_nf_token() -> str:
    global _NF_TOKEN
    if _NF_TOKEN:
        return _NF_TOKEN
    _NF_TOKEN = _resolve_nf_token()
    return _NF_TOKEN


def _get_project_lock(project_id: str) -> threading.Lock:
    with _lock:
        lk = _project_locks.get(project_id)
        if lk is None:
            lk = threading.Lock()
            _project_locks[project_id] = lk
        return lk


# ── Northflank REST helpers ────────────────────────────────────────────────────

def _nf_request(
    method: str,
    path: str,
    json_body: Optional[dict] = None,
    timeout: float = 30.0,
) -> dict:
    token = _get_nf_token()
    if not token:
        raise RuntimeError("NF_API_TOKEN is not set and ~/.northflank/config.json has no token")
    url = f"{NF_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = requests.request(method, url, headers=headers, json=json_body, timeout=timeout)
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        return {}
    if not resp.ok:
        msg = data.get("error", {}).get("message", resp.text[:300])
        raise RuntimeError(f"NF API {method} {path} → {resp.status_code}: {msg}")
    return data.get("data", data)


# ── NfSandboxWorker ────────────────────────────────────────────────────────────

class NfSandboxWorker:
    """Manages a single Northflank deployment service for a project."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.service_id: Optional[str] = None      # NF service id, e.g. "sb-abc12345"
        self.preview_url: Optional[str] = None     # https://p01--sb-xxx--ns.code.run
        self._dns: Optional[str] = None            # raw DNS from NF ports response

    # ── identity / state ──────────────────────────────────────────────────────

    @property
    def sandbox_id(self) -> Optional[str]:
        return self.service_id

    @property
    def app_name(self) -> Optional[str]:
        """Alias for service_id for compat with code that reads worker.app_name."""
        return self.service_id

    @property
    def is_alive(self) -> bool:
        return bool(self.preview_url) and self.health_check() == "ok"

    # ── URL helpers ───────────────────────────────────────────────────────────

    def _bridge_url(self, path: str) -> str:
        """Return the public URL for a bridge endpoint via the /__bridge/ prefix."""
        if not self._dns:
            raise RuntimeError(f"sandbox {self.service_id} has no DNS assigned yet")
        return f"https://{self._dns}/__bridge{path}"

    def _bridge_headers(self) -> dict:
        return {
            "X-Bridge-Secret": NF_BRIDGE_SECRET,
            "Accept-Encoding": "identity",
        }

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def create(self) -> str:
        """Create a new NF deployment service and wait until it is healthy.

        Returns the preview URL.
        """
        if not NF_SANDBOX_IMAGE:
            raise RuntimeError(
                "NF_SANDBOX_IMAGE is not set. "
                "Build and push backend/Dockerfile.sandbox to a registry then set this env var."
            )

        hex_suffix = secrets.token_hex(4)
        service_id = f"{_SB_PREFIX}{hex_suffix}"
        self.service_id = service_id

        payload: dict[str, Any] = {
            "name": service_id,
            "billing": {"deploymentPlan": NF_SANDBOX_PLAN},
            "deployment": {
                "instances": 1,
                "external": {
                    "imagePath": NF_SANDBOX_IMAGE,
                    "credentials": "fly-registry",
                },
            },
            "ports": [
                {
                    "name": "p01",
                    "internalPort": 80,
                    "public": True,
                    "protocol": "HTTP",
                }
            ],
            "runtimeEnvironment": {
                "BRIDGE_SECRET": NF_BRIDGE_SECRET,
                "CONTROL_PLANE_URL": SANDBOX_CONTROL_PLANE_URL,
            },
        }

        print(f"[nf] Creating sandbox service {service_id} in project {NF_PROJECT_ID}…")
        result = _nf_request(
            "POST",
            f"/projects/{NF_PROJECT_ID}/services/deployment",
            json_body=payload,
            timeout=30.0,
        )

        # Extract DNS from the ports array
        dns = self._extract_dns(result)
        self._dns = dns
        self.preview_url = f"https://{dns}"
        print(f"[nf] Service {service_id} created → {self.preview_url}")

        # Wait for the NF deployment to reach RUNNING/COMPLETED
        self._wait_for_running(timeout=180.0)

        # Wait for the bridge inside the container to be reachable
        self._wait_for_bridge(timeout=120.0)

        return self.preview_url

    def _extract_dns(self, service_data: dict) -> str:
        ports = service_data.get("ports", [])
        for port in ports:
            if port.get("name") == "p01" and port.get("dns"):
                return port["dns"]
        raise RuntimeError(f"Could not find 'p01' port DNS in service response: {service_data}")

    def _wait_for_running(self, timeout: float = 180.0) -> None:
        """Wait until the NF deployment status is COMPLETED (containers running)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data = _nf_request("GET", f"/projects/{NF_PROJECT_ID}/services/{self.service_id}")
                status = (
                    data.get("status", {})
                    .get("deployment", {})
                    .get("status", "unknown")
                )
                if status == "COMPLETED":
                    print(f"[nf] Service {self.service_id} is running")
                    return
                if status == "FAILED":
                    raise RuntimeError(f"NF service {self.service_id} failed to start: {data}")
                print(f"[nf] Service {self.service_id} status: {status} (waiting…)")
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[nf] Status check error ({e}), retrying…")
            time.sleep(5)
        raise RuntimeError(f"NF service {self.service_id} did not reach COMPLETED within {timeout:.0f}s")

    def _wait_for_bridge(self, timeout: float = 120.0) -> None:
        """Wait until the bridge API inside the sandbox container is reachable."""
        deadline = time.time() + timeout
        attempt = 0
        while time.time() < deadline:
            try:
                r = requests.get(
                    self._bridge_url("/health"),
                    headers=self._bridge_headers(),
                    timeout=8,
                )
                if r.status_code == 200:
                    print(f"[nf] Bridge reachable for {self.service_id}")
                    return
            except Exception:
                pass
            attempt += 1
            if attempt % 5 == 0:
                print(f"[nf] Waiting for bridge to come up (attempt {attempt})…")
            time.sleep(4)
        raise RuntimeError(
            f"Bridge at {self._bridge_url('/health')} never became reachable after {timeout:.0f}s"
        )

    def destroy(self) -> None:
        """Delete the NF deployment service."""
        if not self.service_id:
            return
        try:
            _nf_request("DELETE", f"/projects/{NF_PROJECT_ID}/services/{self.service_id}", timeout=30.0)
            print(f"[nf] Deleted service {self.service_id}")
        except Exception as e:
            print(f"[nf] Warning: failed to delete service {self.service_id}: {e}")
        self.service_id = None
        self.preview_url = None
        self._dns = None

    def restart_machine(self) -> bool:
        """Restart the NF service (pause → resume).

        Returns True if the service is back up and healthy.
        """
        if not self.service_id:
            return False
        try:
            _nf_request("POST", f"/projects/{NF_PROJECT_ID}/services/{self.service_id}/resume")
            print(f"[nf] Resumed service {self.service_id}")
            # Wait for it to come back
            self._wait_for_running(timeout=90.0)
            self._wait_for_bridge(timeout=60.0)
            return True
        except Exception as e:
            print(f"[nf] Restart failed for {self.service_id}: {e}")
            return False

    # ── bridge operations ─────────────────────────────────────────────────────

    def _bridge_call(self, path: str, json_body: Optional[dict] = None, timeout: float = 60.0) -> Any:
        r = requests.post(
            self._bridge_url(path),
            json=json_body or {},
            headers=self._bridge_headers(),
            timeout=timeout,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Bridge {path} → HTTP {r.status_code}: {r.text[:300]}")
        try:
            return r.json()
        except Exception:
            return r.text

    def write_files(self, files: list[dict]) -> None:
        self._bridge_call("/write_files", {"files": files}, timeout=120.0)

    def setup_vite(self) -> None:
        self._bridge_call("/setup_vite")

    def start_vite(self) -> str:
        self._bridge_call("/start_vite")
        if not self.preview_url and self.service_id:
            self.preview_url = f"https://p01--{self.service_id}--{self._dns_namespace()}.code.run"
        if not self.preview_url:
            raise RuntimeError("start_vite: preview_url is not set and service_id is unknown")
        return self.preview_url

    def _dns_namespace(self) -> str:
        """Extract the namespace slug from the stored DNS string."""
        if self._dns:
            # Format: p01--sb-xxxxxxxx--{namespace}.code.run
            stripped = self._dns.removesuffix(".code.run")
            parts = stripped.split("--")
            if len(parts) >= 3:
                return parts[-1]
        return "unknown"

    def wait_vite_ready(self, timeout: float = 45.0) -> str:
        deadline = time.time() + timeout
        last = "bridge unreachable"
        while time.time() < deadline:
            last = self.health_check()
            if last == "ok":
                return "ok"
            time.sleep(2)
        raise RuntimeError(f"Vite not ready after {timeout:.0f}s: {last}")

    def check_vite_errors(self) -> list:
        try:
            result = self._bridge_call("/check_vite_errors", timeout=30.0)
            if isinstance(result, dict):
                errors = result.get("errors", [])
                return errors if isinstance(errors, list) else []
            if isinstance(result, list):
                # Backward compatibility if bridge returns a raw list.
                return result
        except Exception as e:
            print(f"[nf] check_vite_errors failed (non-fatal): {e}")
        return []

    def health_check(self) -> str:
        try:
            r = requests.get(
                self._bridge_url("/health"),
                headers=self._bridge_headers(),
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("vite_ready"):
                    return "ok"
                return f"vite not ready: {data}"
            return f"HTTP {r.status_code}"
        except Exception as e:
            return str(e)

    def execute(self, cmd: str, args: Any = None, timeout: float = 120.0) -> Any:
        """Dispatch a named command to the sandbox bridge."""
        if cmd == "health_check":
            return self.health_check()
        if cmd == "setup_vite":
            self.setup_vite()
            return "ok"
        if cmd == "write_files":
            self.write_files(args or [])
            return "ok"
        if cmd == "start_vite":
            return self.start_vite()
        if cmd == "wait_vite_ready":
            return self.wait_vite_ready(timeout)
        if cmd == "check_vite_errors":
            return self.check_vite_errors()
        raise RuntimeError(f"unknown command: {cmd}")

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_metadata(self) -> dict:
        return {
            "project_id": self.project_id,
            "service_id": self.service_id,
            "preview_url": self.preview_url,
            "dns": self._dns,
        }

    @classmethod
    def from_metadata(cls, meta: dict) -> "NfSandboxWorker":
        w = cls(meta.get("project_id", ""))
        w.service_id = meta.get("service_id")
        w.preview_url = meta.get("preview_url")
        w._dns = meta.get("dns")
        return w

    # ── compat aliases ────────────────────────────────────────────────────────

    @property
    def fly_sandbox_id(self) -> Optional[str]:
        """Compat alias used in main.py (project.fly_sandbox_id = worker.sandbox_id)."""
        return self.service_id


# ── module-level worker cache (same shape as fly_service.py) ──────────────────

def get_or_create_worker(project_id: str, max_retries: int = 3) -> NfSandboxWorker:
    """Return existing NF sandbox worker or create a new one.

    Lookup order:
      1. In-process _workers dict (same gunicorn worker).
      2. Redis metadata (cross-worker — another gunicorn worker created it).
      3. Create a new NF deployment service.
    """
    from redis_state import get_sandbox_meta_sync, set_sandbox_meta_sync, delete_sandbox_meta_sync

    project_lock = _get_project_lock(project_id)
    with project_lock:
        # ── Step 1: check local in-process cache ─────────────────────────────
        with _lock:
            existing = _workers.get(project_id)
            if existing and existing.preview_url:
                try:
                    if existing.health_check() == "ok":
                        return existing
                except Exception:
                    pass
                # Unhealthy — try restart before discarding
                if existing.restart_machine():
                    print(f"[nf] In-process sandbox {existing.service_id} restarted successfully")
                    return existing
                existing.destroy()
                _workers.pop(project_id, None)

        # ── Step 2: check Redis for metadata from another worker ──────────────
        try:
            meta = get_sandbox_meta_sync(project_id)
            if meta:
                # redis_state was written by fly_service previously — keys differ.
                # Try both "service_id" (new) and "app_name" (old Fly compat).
                service_id = meta.get("service_id") or meta.get("app_name")
                if service_id and service_id.startswith(_SB_PREFIX):
                    worker = NfSandboxWorker.from_metadata(meta)
                    try:
                        if worker.health_check() == "ok":
                            print(f"[nf] Reusing cross-worker sandbox {worker.service_id}")
                            with _lock:
                                _workers[project_id] = worker
                            return worker
                    except Exception as e:
                        print(f"[nf] Cross-worker sandbox unhealthy ({e}), recreating")
                    try:
                        worker.destroy()
                    except Exception:
                        pass
                    delete_sandbox_meta_sync(project_id)
        except Exception as redis_err:
            print(f"[nf] Redis lookup failed (continuing without cache): {redis_err}")

        # ── Step 3: lease from pre-warm pool ──────────────────────────────────
        try:
            from sandbox_pool import lease_machine
            pool_meta = lease_machine()
            if pool_meta and pool_meta.get("service_id", "").startswith(_SB_PREFIX):
                worker = NfSandboxWorker.from_metadata(pool_meta)
                worker.project_id = project_id
                try:
                    if worker.health_check() == "ok":
                        with _lock:
                            _workers[project_id] = worker
                        set_sandbox_meta_sync(project_id, worker.to_metadata())
                        print(f"[nf] Leased warm sandbox {worker.service_id} from pool for {project_id[:8]}")
                        return worker
                    else:
                        print(f"[nf] Pool sandbox {worker.service_id} unhealthy, destroying")
                        worker.destroy()
                except Exception as e:
                    print(f"[nf] Pool sandbox error ({e}), destroying")
                    try:
                        worker.destroy()
                    except Exception:
                        pass
        except Exception as pool_err:
            print(f"[nf] Pool lease failed (non-fatal): {pool_err}")

        # ── Step 4: create a new sandbox ─────────────────────────────────────
        for attempt in range(max_retries):
            worker = NfSandboxWorker(project_id)
            try:
                worker.create()
                with _lock:
                    _workers[project_id] = worker
                try:
                    set_sandbox_meta_sync(project_id, worker.to_metadata())
                except Exception as redis_err:
                    print(f"[nf] Redis metadata save failed (non-fatal): {redis_err}")
                print(f"[nf] Sandbox created for {project_id[:8]}: {worker.preview_url}")
                return worker
            except Exception as e:
                print(f"[nf] Create attempt {attempt + 1}/{max_retries} failed: {e}")
                try:
                    worker.destroy()
                except Exception:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(5)

        raise RuntimeError(f"Failed to create NF sandbox for {project_id} after {max_retries} attempts")


def release_worker(project_id: str) -> None:
    """Destroy and remove the NF sandbox for a project."""
    from redis_state import delete_sandbox_meta_sync
    with _lock:
        worker = _workers.pop(project_id, None)
    if worker:
        worker.destroy()
        print(f"[nf] Sandbox released for {project_id[:8]}")
    try:
        delete_sandbox_meta_sync(project_id)
    except Exception as redis_err:
        print(f"[nf] Redis metadata delete failed (non-fatal): {redis_err}")


def cleanup_stale_sandboxes() -> int:
    """Delete NF sandbox services not tracked by any active project."""
    try:
        # List all services in the NF project
        data = _nf_request("GET", f"/projects/{NF_PROJECT_ID}/services", timeout=30.0)
        services = data.get("services", [])
    except Exception as e:
        print(f"[nf] WARNING: Could not list services for cleanup: {e}")
        return 0

    # Collect service IDs that look like sandboxes (sb- prefix)
    all_sandbox_ids = [
        s.get("id", "") for s in services
        if isinstance(s, dict) and s.get("id", "").startswith(_SB_PREFIX)
    ]
    if not all_sandbox_ids:
        print("[nf] No stale sandboxes found")
        return 0

    # Build set of tracked IDs
    tracked: set[str] = set()
    with _lock:
        tracked.update(w.service_id for w in _workers.values() if w.service_id)
    try:
        from redis_state import list_sandbox_app_names_sync
        tracked.update(list_sandbox_app_names_sync())
    except Exception:
        pass

    stale = [sid for sid in all_sandbox_ids if sid not in tracked]
    if not stale:
        print(f"[nf] All {len(all_sandbox_ids)} sandbox(es) are active")
        return 0

    # Cross-reference with DB to avoid deleting recently active projects
    _SANDBOX_TTL_DAYS = 7
    try:
        from datetime import datetime, timedelta
        from models import SessionLocal, Project as _Project
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=_SANDBOX_TTL_DAYS)
            active_rows = (
                db.query(_Project.fly_sandbox_id)
                .filter(
                    _Project.fly_sandbox_id.in_(stale),
                    _Project.updated_at >= cutoff,
                )
                .all()
            )
            db_tracked = {row[0] for row in active_rows if row[0]}

            inactive_rows = (
                db.query(_Project.id, _Project.fly_sandbox_id)
                .filter(
                    _Project.fly_sandbox_id.in_(stale),
                    _Project.updated_at < cutoff,
                )
                .all()
            )
            if inactive_rows:
                inactive_ids = [row[1] for row in inactive_rows]
                print(f"[nf] Clearing {len(inactive_rows)} inactive project sandbox refs: {inactive_ids}")
                db.query(_Project).filter(
                    _Project.fly_sandbox_id.in_(inactive_ids)
                ).update({_Project.fly_sandbox_id: None, _Project.preview_url: None}, synchronize_session=False)
                db.commit()
        finally:
            db.close()
        if db_tracked:
            print(f"[nf] Keeping {len(db_tracked)} sandbox(es) for recently active projects")
        stale = [sid for sid in stale if sid not in db_tracked]
    except Exception as db_err:
        print(f"[nf] DB cross-reference failed ({db_err}) — skipping cleanup to be safe")
        return 0

    print(f"[nf] Cleaning up {len(stale)} stale sandbox(es): {stale}")
    deleted = 0
    for sid in stale:
        try:
            _nf_request("DELETE", f"/projects/{NF_PROJECT_ID}/services/{sid}", timeout=30.0)
            print(f"[nf] Deleted stale sandbox: {sid}")
            deleted += 1
        except Exception as e:
            print(f"[nf] Warning: failed to delete {sid}: {e}")
    return deleted


# ── startup ────────────────────────────────────────────────────────────────────

def _startup() -> None:
    token = _get_nf_token()
    if not token:
        print("[nf] WARNING: NF_API_TOKEN not set and ~/.northflank/config.json has no token — sandbox creation will fail")
        return
    if not NF_SANDBOX_IMAGE:
        print("[nf] WARNING: NF_SANDBOX_IMAGE not set — sandbox creation will fail until this is configured")
    else:
        print(f"[nf] Token loaded, project={NF_PROJECT_ID}, plan={NF_SANDBOX_PLAN}, image={NF_SANDBOX_IMAGE}")
    threading.Thread(target=_deferred_startup_cleanup, daemon=True).start()


def _deferred_startup_cleanup() -> None:
    try:
        deleted = cleanup_stale_sandboxes()
        if deleted:
            print(f"[nf] Startup cleanup: removed {deleted} stale sandbox(es)")
    except Exception as e:
        print(f"[nf] Startup cleanup error (non-fatal): {e}")


# Aliases so that code importing FlySandboxWorker still works during transition
FlySandboxWorker = NfSandboxWorker

_startup()
