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
import httpx
import requests
from typing import Optional

load_dotenv = __import__("dotenv").load_dotenv
load_dotenv()

FLY_API_TOKEN = os.getenv("FLY_API_TOKEN", "")
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


def _get_project_lock(project_id: str) -> threading.Lock:
    with _lock:
        lock = _project_locks.get(project_id)
        if lock is None:
            lock = threading.Lock()
            _project_locks[project_id] = lock
        return lock


def _allocate_public_ip(app_name: str) -> None:
    """Allocate a shared Anycast IPv4 so Fly Proxy can route to the app.

    Apps created via the Machines API don't automatically get public IPs.
    Without a public IP, the bridge can run inside the VM but will never be
    reachable through Fly Proxy or at *.fly.dev.
    """
    flyctl = shutil.which("flyctl") or shutil.which("flyctl.exe")
    if not flyctl:
        raise RuntimeError("flyctl not found; cannot allocate public IP for sandbox app")

    last_err: Optional[str] = None
    for attempt in range(20):
        proc = subprocess.run(
            [flyctl, "ips", "allocate-v4", "--shared", "-a", app_name],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        lowered = output.lower()
        if proc.returncode == 0:
            print(f"[fly] Allocated shared IPv4 for {app_name}")
            return
        if "already has" in lowered or "shared ipv4 address" in lowered:
            print(f"[fly] Shared IPv4 already allocated for {app_name}")
            return
        last_err = output.strip() or f"exit code {proc.returncode}"
        if "could not find app" in lowered or "not found" in lowered:
            time.sleep(3)
            continue
        break

    raise RuntimeError(f"Failed to allocate shared IPv4 for {app_name}: {last_err}")


def _get_public_ip(app_name: str) -> str:
    """Return the app's shared public IPv4 allocated by Fly."""
    flyctl = shutil.which("flyctl") or shutil.which("flyctl.exe")
    if not flyctl:
        raise RuntimeError("flyctl not found; cannot inspect public IP for sandbox app")

    last_err: Optional[str] = None
    for _ in range(20):
        proc = subprocess.run(
            [flyctl, "ips", "list", "-a", app_name, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            last_err = output.strip() or f"exit code {proc.returncode}"
            time.sleep(2)
            continue
        try:
            rows = json.loads(proc.stdout or "[]")
        except Exception:
            last_err = output.strip() or "invalid JSON from flyctl ips list"
            time.sleep(2)
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            address = row.get("address") or row.get("Address")
            ip_type = str(row.get("type") or row.get("Type") or "").lower()
            version = str(row.get("version") or row.get("Version") or "")
            if address and ((version == "v4") or ("v4" in ip_type)) and ("public ingress" in ip_type or "shared_v4" in ip_type):
                return address
        last_err = f"no shared IPv4 found for {app_name}"
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

    if not FLY_API_TOKEN:
        raise RuntimeError("FLY_API_TOKEN is not set — cannot resolve sandbox image")

    try:
        resp = httpx.get(
            f"{FLY_API_HOST}/v1/apps/{FLY_SANDBOX_BASE_APP}/machines",
            headers={"Authorization": f"Bearer {FLY_API_TOKEN}"},
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


if not FLY_API_TOKEN:
    print("[fly] WARNING: FLY_API_TOKEN is not set — sandbox creation will fail")
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

        def _patched(name, port, *args, **kwargs):
            if name == host:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
            return original(name, port, *args, **kwargs)

        socket.getaddrinfo = _patched
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
        headers = {
            "Authorization": f"Bearer {FLY_API_TOKEN}",
            "Content-Type": "application/json",
        }
        if not FLY_API_TOKEN:
            raise RuntimeError("FLY_API_TOKEN is not set — cannot create Fly sandbox")
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, url, headers=headers, json=json_body)
            if resp.status_code >= 400:
                body = resp.text[:500] if resp.text else "(empty)"
                print(f"[fly] API error: {method} {url} → {resp.status_code}: {body}")
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    def create(self) -> str:
        """Create Fly app and machine, return preview URL."""
        hex_suffix = secrets.token_hex(4)
        self.app_name = f"kith-sandbox-{hex_suffix}"
        with _lock:
            _creating_apps.add(self.app_name)

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
            self.preview_url = f"https://{self.app_name}.fly.dev"
            _allocate_public_ip(self.app_name)
            self._public_ip = _get_public_ip(self.app_name)
            print(f"[fly] Using shared IPv4 {self._public_ip} for {self.app_name}")

            # Wait for machine to be started
            print(f"[fly] Waiting for machine {self.machine_id} to start...")
            for i in range(60):
                m = self._api_request("GET", f"/apps/{self.app_name}/machines/{self.machine_id}")
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

            return self.preview_url
        finally:
            with _lock:
                if self.app_name:
                    _creating_apps.discard(self.app_name)

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
        return self.preview_url

    def wait_vite_ready(self, timeout: float = 45.0) -> str:
        deadline = time.time() + timeout
        last = "bridge unreachable"
        while time.time() < deadline:
            last = self.health_check()
            if last == "ok":
                return "ok"
            time.sleep(2)
        raise RuntimeError(f"Vite not ready after {timeout:.0f}s: {last}")

    def execute(self, cmd: str, args=None, timeout: float = 120.0) -> str:
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

    def destroy(self) -> None:
        if self.app_name:
            try:
                self._api_request("DELETE", f"/apps/{self.app_name}?force=true", timeout=30)
            except Exception as e:
                print(f"[fly] Warning: could not delete app {self.app_name}: {e}")
            self.app_name = None
            self.machine_id = None
            self.preview_url = None


def get_or_create_worker(project_id: str, max_retries: int = 2) -> FlySandboxWorker:
    """Get existing Fly sandbox worker or create new one."""
    project_lock = _get_project_lock(project_id)
    with project_lock:
        with _lock:
            existing = _workers.get(project_id)
            if existing and existing.preview_url:
                try:
                    if existing.health_check() == "ok":
                        return existing
                except Exception:
                    pass
                existing.destroy()
                _workers.pop(project_id, None)

        for attempt in range(max_retries):
            worker = FlySandboxWorker(project_id)
            try:
                worker.create()
                with _lock:
                    _workers[project_id] = worker
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
    with _lock:
        worker = _workers.pop(project_id, None)
    if worker:
        worker.destroy()
        print(f"[fly] Sandbox released for {project_id}")


def cleanup_stale_sandboxes() -> int:
    """Delete sandbox apps not tracked by this process (leaked from crashes)."""
    if not FLY_API_TOKEN:
        return 0
    headers = {"Authorization": f"Bearer {FLY_API_TOKEN}"}
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

        print(f"[fly] Cleaning up {len(stale)} stale sandbox(es): {stale}")
        deleted = 0
        for name in stale:
            try:
                httpx.delete(
                    f"{FLY_API_HOST}/v1/apps/{name}",
                    headers=headers,
                    timeout=30,
                )
                print(f"[fly] Deleted stale sandbox: {name}")
                deleted += 1
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
