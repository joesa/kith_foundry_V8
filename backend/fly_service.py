"""
Fly.io Sandbox Service — creates and manages Fly Machines for user project previews.

Uses the Fly Machines API to create per-project apps with a Vite dev server.
Each sandbox runs in a Docker container with a bridge API for file writes and commands.
"""
import os
import time
import threading
import secrets
import shutil
import subprocess
import json
import socket
import contextlib
from pathlib import Path
import httpx  # type: ignore[import]
import requests  # type: ignore[import]
from typing import Any, Optional

load_dotenv: Any = __import__("dotenv").load_dotenv  # type: ignore[name-defined]
_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv()
load_dotenv(_BACKEND_DIR / ".env", override=False)

FLY_API_TOKEN = ""
FLY_ORG_SLUG = os.getenv("FLY_ORG_SLUG", "personal")
FLY_API_HOST = os.getenv("FLY_API_HOSTNAME", "https://api.machines.dev")
FLY_REGION = os.getenv("FLY_SANDBOX_REGION", "ord")
FLY_SANDBOX_BASE_APP = os.getenv("FLY_SANDBOX_BASE_APP", "kith-sandbox-base")
BRIDGE_SECRET = os.getenv("FLY_BRIDGE_SECRET") or secrets.token_urlsafe(32)

# Shared IPv4s are allocated per app. We resolve and use the app's actual
# shared ingress IPv4 directly to bypass local DNS propagation delays.

_workers: dict[str, "FlySandboxWorker"] = {}
_lock = threading.Lock()
_project_locks: dict[str, threading.Lock] = {}
_creating_apps: set[str] = set()
_resolved_image: Optional[str] = None


def _resolve_flyctl() -> Optional[str]:
    return shutil.which("flyctl") or shutil.which("flyctl.exe")


def _resolve_fly_api_token() -> str:
    token = os.getenv("FLY_API_TOKEN", "").strip()
    if token:
        return token

    flyctl = _resolve_flyctl()
    if not flyctl:
        return ""

    try:
        proc = subprocess.run(
            [flyctl, "auth", "token"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return ""

    if proc.returncode != 0:
        return ""

    lines = [line.strip() for line in ((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("FlyV1 ") or line.startswith("fm") or line.startswith("fo1_"):
            return line
    return ""


def _get_fly_api_token() -> str:
    global FLY_API_TOKEN
    if FLY_API_TOKEN:
        return FLY_API_TOKEN
    FLY_API_TOKEN = _resolve_fly_api_token()
    return FLY_API_TOKEN


def _get_project_lock(project_id: str) -> threading.Lock:
    with _lock:
        lock = _project_locks.get(project_id)
        if lock is None:
            lock = threading.Lock()
            _project_locks[project_id] = lock
        return lock


FLY_GRAPHQL_URL = "https://api.fly.io/graphql"


def _graphql(query: str, variables: dict | None = None) -> dict:
    """Execute a Fly.io GraphQL query/mutation using the API token."""
    token = _get_fly_api_token()
    if not token:
        raise RuntimeError("FLY_API_TOKEN is not set — cannot call Fly GraphQL API")
    resp = httpx.post(
        FLY_GRAPHQL_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"Fly GraphQL error: {data['errors']}")
    return data.get("data") or {}


def _allocate_public_ip(app_name: str) -> None:
    """Allocate a shared Anycast IPv4 so Fly Proxy can route to the app.

    Apps created via the Machines API don't automatically get public IPs.
    Without a public IP, the bridge can run inside the VM but will never be
    reachable through Fly Proxy or at *.fly.dev.

    Uses the Fly Machines REST API (POST /v1/apps/:name/ip_assignments).
    """
    token = _get_fly_api_token()
    if not token:
        raise RuntimeError("FLY_API_TOKEN is not set — cannot allocate IP")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{FLY_API_HOST}/v1/apps/{app_name}/ip_assignments"
    last_err: Optional[str] = None
    for attempt in range(20):
        try:
            resp = httpx.post(
                url,
                headers=headers,
                json={"type": "shared_v4"},
                timeout=15,
            )
            if resp.status_code == 200 or resp.status_code == 201:
                data = resp.json()
                addr = data.get("address") or data.get("ip") or ""
                if addr:
                    print(f"[fly] Allocated shared IPv4 {addr} for {app_name}")
                    return
                # Some Fly regions return 200 with the IP nested differently
                print(f"[fly] IP allocated (200) but no address in response: {data}")
                return  # IP was allocated even if address not in response body
            if resp.status_code == 409:
                # Already allocated
                print(f"[fly] Shared IPv4 already allocated for {app_name}")
                return
            body = resp.text[:300] if resp.text else "(empty)"
            last_err = f"HTTP {resp.status_code}: {body}"
            if resp.status_code == 404:
                if attempt < 19:
                    print(f"[fly] App not visible yet for IP allocation (attempt {attempt + 1}), retrying...")
                time.sleep(3)
                continue
            print(f"[fly] IP allocate error (attempt {attempt + 1}): {last_err}")
        except Exception as e:
            last_err = str(e)
            print(f"[fly] IP allocate exception (attempt {attempt + 1}): {e}")
        time.sleep(3)

    raise RuntimeError(f"Failed to allocate shared IPv4 for {app_name}: {last_err}")


def _get_public_ip(app_name: str) -> str:
    """Return the app's shared public IPv4 allocated by Fly.

    Uses the Fly Machines REST API (GET /v1/apps/:name/ip_assignments).
    """
    token = _get_fly_api_token()
    if not token:
        raise RuntimeError("FLY_API_TOKEN is not set — cannot resolve IP")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FLY_API_HOST}/v1/apps/{app_name}/ip_assignments"
    last_err: Optional[str] = None
    for attempt in range(20):
        try:
            resp = httpx.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # Response can be a bare list or wrapped in {'ips': [...]}
            entries = data if isinstance(data, list) else data.get("ips") or []
            for entry in entries:
                addr = entry.get("address") or entry.get("ip") or ""
                ip_type = (entry.get("type") or "").lower()
                is_shared = entry.get("shared", False)
                # Match by type field (v4/shared) OR by the 'shared' boolean flag
                if addr and ("v4" in ip_type or "shared" in ip_type or is_shared):
                    return addr
            last_err = f"no shared IPv4 found for {app_name} (response: {data})"
        except Exception as e:
            last_err = str(e)
        time.sleep(2)

    raise RuntimeError(f"Failed to resolve shared IPv4 for {app_name}: {last_err}")


def _resolve_sandbox_image() -> str:
    """Look up the latest deployed image from the base app's machines.

    Queries the Fly Machines API once at startup, caches the result.
    Falls back to FLY_SANDBOX_IMAGE env var if the lookup fails.
    """
    global _resolved_image
    if _resolved_image:
        return _resolved_image

    env_override = os.getenv("FLY_SANDBOX_IMAGE", "")
    if env_override:
        _resolved_image = env_override
        print(f"[fly] Using image from FLY_SANDBOX_IMAGE env: {_resolved_image}")
        return _resolved_image

    token = _get_fly_api_token()
    if not token:
        raise RuntimeError("FLY_API_TOKEN is not set — cannot resolve sandbox image")

    try:
        resp = httpx.get(
            f"{FLY_API_HOST}/v1/apps/{FLY_SANDBOX_BASE_APP}/machines",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        machines = resp.json()
        for m in machines:
            image = m.get("config", {}).get("image", "")
            if image and FLY_SANDBOX_BASE_APP in image:
                _resolved_image = image
                print(f"[fly] Auto-detected sandbox image: {_resolved_image}")
                return _resolved_image
        raise RuntimeError(f"No machines with a valid image found in {FLY_SANDBOX_BASE_APP}")
    except Exception as e:
        print(f"[fly] WARNING: Could not auto-detect sandbox image: {e}")
        raise


if not _get_fly_api_token():
    print("[fly] WARNING: FLY_API_TOKEN is not set and flyctl auth token could not be resolved — sandbox creation will fail")
else:
    print(f"[fly] Token loaded ({len(FLY_API_TOKEN)} chars), org={FLY_ORG_SLUG}, region={FLY_REGION}")
    try:
        _resolve_sandbox_image()
    except Exception as e:
        print(f"[fly] WARNING: Image auto-detect failed at startup: {e}")


class FlySandboxWorker:
    """Manages a single Fly app/machine for a project."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.app_name: Optional[str] = None
        self.machine_id: Optional[str] = None
        self.preview_url: Optional[str] = None
        self._public_ip: Optional[str] = None
        self._bridge_secret = BRIDGE_SECRET

    @property
    def sandbox_id(self) -> Optional[str]:
        return self.app_name

    @property
    def is_alive(self) -> bool:
        return bool(self.preview_url) and self.health_check() == "ok"

    @property
    def _bridge_host(self) -> str:
        return f"{self.app_name}.fly.dev"

    def _bridge_url(self, path: str) -> str:
        """Bridge endpoint using the real hostname.

        We override DNS locally so requests connect to the app's allocated shared
        IPv4 without waiting for local DNS propagation.
        """
        return f"http://{self._bridge_host}/__bridge{path}"

    @contextlib.contextmanager
    def _with_dns_override(self):
        if not self._public_ip:
            raise RuntimeError(f"sandbox app {self.app_name} has no allocated public IPv4")
        original = socket.getaddrinfo
        host = self._bridge_host
        ip = self._public_ip

        def _patched(name, port, *args, **kwargs):  # type: ignore[assignment]
            if name == host:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
            return original(name, port, *args, **kwargs)

        socket.getaddrinfo = _patched  # type: ignore[assignment]
        try:
            yield
        finally:
            socket.getaddrinfo = original

    def _bridge_headers(self, extra: dict | None = None) -> dict:
        """Standard headers for bridge calls (Host for Fly routing + auth).

        Accept-Encoding: identity disables Fly's edge compression (zstd/gzip),
        ensuring responses are returned as plain JSON that requests can parse.
        """
        h = {
            "Host": self._bridge_host,
            "X-Bridge-Secret": self._bridge_secret,
            "Accept-Encoding": "identity",
        }
        if extra:
            h.update(extra)
        return h

    def _api_request(
        self,
        method: str,
        path: str,
        json_body: Optional[dict] = None,
        timeout: float = 60.0,
    ) -> dict:
        url = f"{FLY_API_HOST}/v1{path}"
        token = _get_fly_api_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if not token:
            raise RuntimeError("FLY_API_TOKEN is not set — cannot create Fly sandbox")
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, url, headers=headers, json=json_body)
            if resp.status_code >= 400:
                body = resp.text[:500] if resp.text else "(empty)"
                print(f"[fly] API error: {method} {url} → {resp.status_code}: {body}")
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    def create(self) -> str:  # type: ignore[return]
        """Create Fly app and machine, return preview URL."""
        hex_suffix = secrets.token_hex(4)
        app_name = f"kith-sandbox-{hex_suffix}"
        self.app_name = app_name
        with _lock:
            _creating_apps.add(app_name)

        try:

            # Create app (path is /apps, base URL already has /v1)
            self._api_request(
                "POST",
                "/apps",
                json_body={
                    "app_name": self.app_name,
                    "org_slug": FLY_ORG_SLUG,
                },
            )

            # Create machine with our sandbox image (auto-detected from base app)
            config = {
                "image": _resolve_sandbox_image(),
                "env": {
                    "FLY_APP_NAME": self.app_name,
                    "BRIDGE_SECRET": self._bridge_secret,
                },
                "guest": {"cpu_kind": "shared", "cpus": 2, "memory_mb": 2048},
                "services": [
                    {
                        "protocol": "tcp",
                        "internal_port": 80,
                        "ports": [{"port": 80, "handlers": ["http"]}, {"port": 443, "handlers": ["tls", "http"]}],
                        # Keep the machine alive — Fly's default is to stop idle machines,
                        # which causes ERR_CONNECTION_CLOSED for users still looking at the preview.
                        "auto_stop_machines": "off",
                        "auto_start_machines": True,
                        "min_machines_running": 1,
                    }
                ],
                "restart": {"policy": "always"},
            }
            machine = self._api_request(
                "POST",
                f"/apps/{self.app_name}/machines",
                json_body={"config": config, "region": FLY_REGION, "lease_ttl": 120},
            )
            self.machine_id = machine.get("id")
            self.preview_url = f"https://{app_name}.fly.dev"
            _allocate_public_ip(app_name)
            self._public_ip = _get_public_ip(app_name)
            print(f"[fly] Using shared IPv4 {self._public_ip} for {app_name}")

            # Wait for machine to be started
            print(f"[fly] Waiting for machine {self.machine_id} to start...")
            for i in range(60):
                m = self._api_request("GET", f"/apps/{app_name}/machines/{self.machine_id}")
                state = m.get("state")
                if state == "started":
                    print(f"[fly] Machine started after {i * 2}s")
                    break
                if i % 5 == 4:
                    print(f"[fly] Machine state: {state} (waiting...)")
                time.sleep(2)

            # Wait for bridge to be reachable.
            # We use plain HTTP directly to Fly's anycast IP with a Host header.
            # This bypasses DNS propagation delays for new *.fly.dev apps.
            health_url = self._bridge_url("/health")
            health_headers = self._bridge_headers()
            print(f"[fly] Waiting for bridge (HTTP via {self._bridge_host} -> {self._public_ip})...")

            bridge_reachable = False
            for attempt in range(60):  # up to ~120 seconds
                try:
                    with self._with_dns_override():
                        r = requests.get(health_url, headers=health_headers, timeout=5)
                    if r.status_code == 200:
                        try:
                            data = r.json()
                        except Exception:
                            # Got HTTP 200 but non-JSON body — likely Vite HTML or Fly edge passthrough
                            if attempt % 5 == 4:
                                body_preview = r.text[:120].replace("\n", " ") if r.text else "(empty)"
                                print(f"[fly] bridge health returned 200 but non-JSON (attempt {attempt}): {body_preview!r}")
                            time.sleep(2)
                            continue
                        bridge_reachable = True
                        if data.get("vite_ready"):
                            print(f"[fly] Bridge + Vite ready after {attempt * 2}s")
                            break
                        if attempt % 5 == 4:
                            print(f"[fly] Bridge up, Vite not ready yet (attempt {attempt}): {data}")
                    elif r.status_code in (404, 502, 503):
                        if attempt % 5 == 4:
                            print(f"[fly] Fly edge reached but not routing yet (HTTP {r.status_code}, attempt {attempt})")
                except (requests.RequestException, OSError) as e:
                    if attempt % 10 == 9:
                        print(f"[fly] Bridge not reachable yet (attempt {attempt}): {e}")
                except Exception as e:
                    if attempt % 10 == 9:
                        print(f"[fly] Health check error (attempt {attempt}): {e}")
                time.sleep(2)

            if not bridge_reachable:
                raise RuntimeError(
                    f"Bridge at {self.preview_url} never became reachable after ~120s "
                    f"(container boot failure)"
                )

            # Wait for public DNS to propagate so the browser iframe can load the URL.
            # The bridge loop above uses IP-override to bypass DNS, but the user's
            # browser resolves the hostname normally and will get NXDOMAIN for a
            # brand-new *.fly.dev app until Fly's DNS propagates (~10-60s).
            dns_host = f"{app_name}.fly.dev"
            print(f"[fly] Waiting for DNS propagation of {dns_host}...")
            dns_ok = False
            for _ in range(30):  # up to ~60s
                try:
                    socket.getaddrinfo(dns_host, 443)
                    print(f"[fly] DNS propagated for {dns_host}")
                    dns_ok = True
                    break
                except socket.gaierror:
                    time.sleep(2)
            if not dns_ok:
                print(f"[fly] DNS not yet propagated for {dns_host} after 60s — browser may retry")

            preview: str = self.preview_url  # type: ignore[assignment]
            return preview
        finally:
            with _lock:
                if self.app_name:
                    _creating_apps.discard(self.app_name)  # type: ignore[arg-type]

    def _bridge_call(
        self, path: str, method: str = "POST",
        json_body: Optional[dict] = None, max_retries: int = 5,
    ) -> dict:
        """Call the bridge API via hostname with DNS overridden to the app IP."""
        url = self._bridge_url(path)
        headers = self._bridge_headers({"Content-Type": "application/json"})
        last_err = None
        for attempt in range(max_retries):
            try:
                with self._with_dns_override():
                    resp = requests.request(method, url, headers=headers, json=json_body, timeout=120)
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except (requests.RequestException, OSError) as e:
                last_err = e
                print(f"[fly] Bridge call {method} {path} failed (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(3)
            except requests.HTTPError:
                raise
        raise RuntimeError(f"Bridge call {method} {path} failed after {max_retries} retries: {last_err}")

    def write_files(self, files: list[dict]) -> None:
        self._bridge_call("/write_files", json_body={"files": files})

    def setup_vite(self) -> None:
        self._bridge_call("/setup_vite")

    def start_vite(self) -> str:
        self._bridge_call("/start_vite")
        # Ensure preview_url is always set — derive from app_name if somehow None
        if not self.preview_url and self.app_name:
            self.preview_url = f"https://{self.app_name}.fly.dev"
        if not self.preview_url:
            raise RuntimeError("start_vite: preview_url is not set and app_name is unknown")
        url: str = self.preview_url  # type: ignore[assignment]
        return url

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
        """Probe all src/*.tsx files through Vite and return any that return HTTP 500.

        wait_vite_ready only checks the root page, which returns 200 even when
        lazy-loaded route components have syntax errors.  This method eagerly
        requests every TSX file so compilation errors surface before the browser
        loads the preview.
        """
        try:
            result = self._bridge_call("/check_vite_errors", max_retries=1)
            return result.get("errors", [])
        except Exception as e:
            print(f"[fly] check_vite_errors failed (non-fatal): {e}")
            return []

    def execute(self, cmd: str, args=None, timeout: float = 120.0):
        """Dispatch a command to the sandbox."""
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

    def health_check(self) -> str:
        try:
            with self._with_dns_override():
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

    def restart_machine(self) -> bool:
        """Start a stopped Fly machine back up. Returns True if successfully started."""
        if not self.app_name or not self.machine_id:
            return False
        try:
            # Check current state first
            m = self._api_request("GET", f"/apps/{self.app_name}/machines/{self.machine_id}")
            state = m.get("state", "")
            if state == "started":
                return True
            if state in ("stopped", "suspended"):
                print(f"[fly] Restarting stopped machine {self.machine_id} (state={state})")
                self._api_request("POST", f"/apps/{self.app_name}/machines/{self.machine_id}/start", timeout=15)
                # Wait for it to come back up
                for i in range(30):
                    time.sleep(2)
                    m = self._api_request("GET", f"/apps/{self.app_name}/machines/{self.machine_id}")
                    if m.get("state") == "started":
                        print(f"[fly] Machine restarted after {i * 2}s")
                        # Wait for bridge to be reachable again (up to 30s)
                        for _ in range(15):
                            if self.health_check() == "ok":
                                return True
                            time.sleep(2)
                        return False
                print(f"[fly] Machine did not reach 'started' state after restart")
                return False
            print(f"[fly] Cannot restart machine in state: {state}")
            return False
        except Exception as e:
            print(f"[fly] restart_machine failed: {e}")
            return False

    def destroy(self) -> None:
        if self.app_name:
            try:
                self._api_request("DELETE", f"/apps/{self.app_name}?force=true", timeout=30)
            except Exception as e:
                print(f"[fly] Warning: could not delete app {self.app_name}: {e}")
            self.app_name = None
            self.machine_id = None
            self.preview_url = None

    # ── Redis serialization ───────────────────────────────────────────────

    def to_metadata(self) -> dict:
        """Serialise to a Redis-safe dict for cross-worker sharing."""
        return {
            "project_id": self.project_id,
            "app_name": self.app_name,
            "machine_id": self.machine_id,
            "preview_url": self.preview_url,
            "public_ip": self._public_ip,
        }

    @classmethod
    def from_metadata(cls, meta: dict) -> "FlySandboxWorker":
        """Reconstruct a worker shell from Redis metadata (no VM creation)."""
        w = cls(meta["project_id"])
        w.app_name = meta.get("app_name")
        w.machine_id = meta.get("machine_id")
        w.preview_url = meta.get("preview_url")
        w._public_ip = meta.get("public_ip")
        return w


def get_or_create_worker(project_id: str, max_retries: int = 2) -> FlySandboxWorker:
    """Get existing Fly sandbox worker or create new one.

    Lookup order:
      1. In-process ``_workers`` dict (fastest — same gunicorn worker).
      2. Redis metadata (cross-worker — another gunicorn worker created it).
      3. Create a new sandbox and persist metadata to Redis.
    """
    from redis_state import get_sandbox_meta_sync, set_sandbox_meta_sync, delete_sandbox_meta_sync

    project_lock = _get_project_lock(project_id)
    with project_lock:
        # ── Step 1: check local in-process cache ───────────────────────────
        with _lock:
            existing = _workers.get(project_id)
            if existing and existing.preview_url:
                try:
                    if existing.health_check() == "ok":
                        return existing
                except Exception:
                    pass
                # Try to restart a stopped machine before destroying
                if existing.restart_machine():
                    print(f"[fly] In-process sandbox {existing.app_name} restarted successfully")
                    return existing
                existing.destroy()
                _workers.pop(project_id, None)

        # ── Step 2: check Redis for metadata created by another worker ─────
        try:
            meta = get_sandbox_meta_sync(project_id)
            if meta:
                worker = FlySandboxWorker.from_metadata(meta)
                try:
                    if worker.health_check() == "ok":
                        print(f"[fly] Reusing cross-worker sandbox {worker.app_name} for {project_id[:8]}")
                        with _lock:
                            _workers[project_id] = worker
                        return worker
                    else:
                        print(f"[fly] Cross-worker sandbox {worker.app_name} unhealthy — attempting restart")
                        if worker.restart_machine():
                            print(f"[fly] Cross-worker sandbox {worker.app_name} restarted successfully")
                            with _lock:
                                _workers[project_id] = worker
                            return worker
                        print(f"[fly] Cross-worker sandbox {worker.app_name} restart failed, recreating")
                        worker.destroy()
                        delete_sandbox_meta_sync(project_id)
                except Exception as e:
                    print(f"[fly] Cross-worker sandbox health check failed ({e}), recreating")
                    worker.destroy()
                    delete_sandbox_meta_sync(project_id)
        except Exception as redis_err:
            print(f"[fly] Redis lookup failed (continuing without cache): {redis_err}")

        # ── Step 3a: lease from pre-warm pool ─────────────────────────────
        try:
            from sandbox_pool import lease_machine
            pool_meta = lease_machine()
            if pool_meta:
                worker = FlySandboxWorker.from_metadata(pool_meta)
                worker.project_id = project_id  # reassign to this project
                try:
                    if worker.health_check() == "ok":
                        with _lock:
                            _workers[project_id] = worker
                        set_sandbox_meta_sync(project_id, worker.to_metadata())
                        print(f"[fly] Leased warm sandbox {worker.app_name} from pool for {project_id[:8]}")
                        return worker
                    else:
                        print(f"[fly] Pool sandbox {worker.app_name} unhealthy, destroying and continuing")
                        worker.destroy()
                except Exception as e:
                    print(f"[fly] Pool sandbox health check failed ({e}), destroying")
                    try:
                        worker.destroy()
                    except Exception:
                        pass
        except Exception as pool_err:
            print(f"[fly] Pool lease failed (non-fatal): {pool_err}")

        # ── Step 3b: create a new sandbox ─────────────────────────────────
        for attempt in range(max_retries):
            worker = FlySandboxWorker(project_id)
            try:
                worker.create()
                with _lock:
                    _workers[project_id] = worker
                # Persist metadata to Redis for cross-worker discovery
                try:
                    set_sandbox_meta_sync(project_id, worker.to_metadata())
                except Exception as redis_err:
                    print(f"[fly] Redis metadata save failed (non-fatal): {redis_err}")
                print(f"[fly] Sandbox created for {project_id}: {worker.preview_url}")
                return worker
            except Exception as e:
                import traceback
                print(f"[fly] Sandbox creation failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"[fly] Traceback:\n{traceback.format_exc()}")
                worker.destroy()
                if attempt < max_retries - 1:
                    time.sleep(3)
        raise RuntimeError(f"Failed to create Fly sandbox for {project_id}")


def release_worker(project_id: str) -> None:
    """Destroy and remove the Fly sandbox for a project."""
    from redis_state import delete_sandbox_meta_sync
    with _lock:
        worker = _workers.pop(project_id, None)
    if worker:
        worker.destroy()
        print(f"[fly] Sandbox released for {project_id}")
    # Always remove Redis metadata so other workers stop trying to reuse it
    try:
        delete_sandbox_meta_sync(project_id)
    except Exception as redis_err:
        print(f"[fly] Redis metadata delete failed (non-fatal): {redis_err}")


def cleanup_stale_sandboxes() -> int:
    """Delete sandbox apps not tracked by this process (leaked from crashes)."""
    token = _get_fly_api_token()
    if not token:
        return 0
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = httpx.get(
            f"{FLY_API_HOST}/v1/apps?org_slug={FLY_ORG_SLUG}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        apps = data if isinstance(data, list) else data.get("apps", [])

        tracked = {w.app_name for w in _workers.values()}
        tracked.update(_creating_apps)
        # Also include sandbox app names stored in Redis (created on other workers)
        try:
            from redis_state import list_sandbox_app_names_sync
            tracked.update(list_sandbox_app_names_sync())
        except Exception:
            pass
        stale = []
        for app in apps:
            name = app.get("name", "") if isinstance(app, dict) else str(app)
            if (
                name.startswith("kith-sandbox-")
                and name != FLY_SANDBOX_BASE_APP
                and name not in tracked
            ):
                stale.append(name)

        if not stale:
            print("[fly] No stale sandboxes to clean up")
            return 0

        # Cross-reference stale candidates against the database.
        # A sandbox is still needed if any project has fly_sandbox_id pointing to it
        # AND that project was active within the last 7 days.
        # Projects inactive for longer get their sandbox released here — it will
        # be lazily recreated the next time that user opens the project.
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
                db_tracked = set(row[0] for row in active_rows if row[0])

                # For inactive projects whose sandbox is in the stale list, clear
                # fly_sandbox_id so the next connect creates a fresh sandbox.
                inactive_rows = (
                    db.query(_Project.id, _Project.fly_sandbox_id)
                    .filter(
                        _Project.fly_sandbox_id.in_(stale),
                        _Project.updated_at < cutoff,
                    )
                    .all()
                )
                if inactive_rows:
                    inactive_names = [row[1] for row in inactive_rows]
                    print(f"[fly] Releasing {len(inactive_rows)} sandbox(es) from inactive projects (>{_SANDBOX_TTL_DAYS}d): {inactive_names}")
                    db.query(_Project).filter(
                        _Project.fly_sandbox_id.in_(inactive_names)
                    ).update({_Project.fly_sandbox_id: None, _Project.preview_url: None}, synchronize_session=False)
                    db.commit()
            finally:
                db.close()
            if db_tracked:
                print(f"[fly] Keeping {len(db_tracked)} sandbox(es) for recently active projects: {db_tracked}")
            stale = [n for n in stale if n not in db_tracked]
        except Exception as db_err:
            print(f"[fly] DB cross-reference failed ({db_err}) — skipping cleanup to be safe")
            return 0

        print(f"[fly] Cleaning up {len(stale)} stale sandbox(es): {stale}")
        deleted: int = 0
        for name in stale:
            try:
                httpx.delete(
                    f"{FLY_API_HOST}/v1/apps/{name}",
                    headers=headers,
                    timeout=30,
                )
                print(f"[fly] Deleted stale sandbox: {name}")
                deleted += 1  # type: ignore[operator]
            except Exception as e:
                print(f"[fly] Warning: failed to delete {name}: {e}")
        return deleted
    except Exception as e:
        print(f"[fly] WARNING: Stale sandbox cleanup failed: {e}")
        return 0


# ── Deferred startup cleanup (runs after module fully loads) ──
def _deferred_startup_cleanup():
    """Clean up stale sandboxes in a background thread so import isn't blocked."""
    try:
        deleted = cleanup_stale_sandboxes()
        if deleted:
            print(f"[fly] Startup cleanup: removed {deleted} stale sandbox(es)")
    except Exception as e:
        print(f"[fly] Startup cleanup error: {e}")


if FLY_API_TOKEN:
    threading.Thread(target=_deferred_startup_cleanup, daemon=True).start()
