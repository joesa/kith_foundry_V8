"""
Bridge API — runs inside the Fly sandbox container.
Receives file writes and commands from the Kith Foundry backend.
Protected by X-Bridge-Secret header (must match BRIDGE_SECRET env).

Endpoints expected by fly_service.py:
  GET  /health       → {"ok": true, "vite_ready": bool}
  POST /health       → same
  POST /write_files  → write files to /workspace
  POST /setup_vite   → no-op (Vite is pre-installed in the Docker image)
  POST /start_vite   → no-op (Vite is started by start.sh on boot)
  POST /run_cmd      → run arbitrary shell command
  GET  /fetch?url=   → HTTP GET from inside the sandbox
"""
import os
import subprocess
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
WORKSPACE = Path("/workspace")
WORKSPACE.mkdir(parents=True, exist_ok=True)


def _verify_secret(x_bridge_secret: str | None) -> None:
    expected = os.environ.get("BRIDGE_SECRET", "")
    if not expected or not x_bridge_secret or x_bridge_secret != expected:
        raise HTTPException(status_code=403, detail="Invalid bridge secret")


def _check_vite() -> bool:
    """Return True if Vite dev server is responding on localhost:5173."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


@app.get("/health")
@app.post("/health")
async def health(x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret")):
    _verify_secret(x_bridge_secret)
    vite_ready = _check_vite()
    return {"ok": True, "vite_ready": vite_ready}


@app.post("/setup_vite")
async def setup_vite(x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret")):
    """No-op — Vite project is pre-installed in the Docker image (npm install ran at build time)."""
    _verify_secret(x_bridge_secret)
    return {"ok": True}


@app.post("/start_vite")
async def start_vite(x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret")):
    """No-op — Vite is started by start.sh on container boot. Return the local URL."""
    _verify_secret(x_bridge_secret)
    return {"ok": True, "url": "http://localhost:5173"}


@app.post("/write_files")
async def write_files(
    request: Request,
    x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret"),
):
    _verify_secret(x_bridge_secret)
    body = await request.json()
    files = body.get("files", [])
    written = 0
    for f in files:
        fp = f.get("file_path", "")
        content = f.get("content", "")
        if not fp:
            continue
        path = WORKSPACE / fp
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or "", encoding="utf-8")
        written += 1
    return {"ok": True, "written": written}


@app.post("/run_cmd")
async def run_cmd(
    request: Request,
    x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret"),
):
    _verify_secret(x_bridge_secret)
    body = await request.json()
    cmd = body.get("cmd", [])
    cwd = body.get("cwd", str(WORKSPACE))
    if not cmd:
        raise HTTPException(status_code=400, detail="cmd required")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fetch")
async def fetch(
    url: str,
    x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret"),
):
    """HTTP GET from inside the sandbox (e.g. localhost:5173)."""
    _verify_secret(x_bridge_secret)
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return {"status": r.status, "body": r.read().decode("utf-8", errors="replace")[:5000]}
    except Exception as e:
        return {"status": 0, "error": str(e)}


@app.post("/check_vite_errors")
async def check_vite_errors(
    x_bridge_secret: str | None = Header(None, alias="X-Bridge-Secret"),
):
    """Probe each .tsx file in /workspace/src through Vite and return any that return HTTP 500.

    Vite returns 200 on the root page even when lazy-loaded components have
    syntax errors — those only fail when the browser actually requests the file.
    This endpoint eagerly requests every TSX file so compilation errors are
    detected immediately after write_files.
    """
    _verify_secret(x_bridge_secret)
    errors = []
    src_dir = WORKSPACE / "src"
    if not src_dir.exists():
        return {"errors": []}
    for tsfile in sorted(src_dir.rglob("*.tsx")):
        if "node_modules" in tsfile.parts:
            continue
        rel = str(tsfile.relative_to(WORKSPACE))
        url = f"http://127.0.0.1:5173/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                pass  # 200 = compiled OK
        except urllib.error.HTTPError as e:
            if e.code == 500:
                body = e.read().decode("utf-8", errors="replace")[:800]
                errors.append({"file": rel, "error": body})
        except Exception:
            pass
    return {"errors": errors}
