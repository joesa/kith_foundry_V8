import os
import requests
import uuid
from dotenv import load_dotenv

# Load environment variables from backend/.env if it exists
load_dotenv()

FLY_API_TOKEN = os.getenv("FLY_API_TOKEN")
FLY_ORG_SLUG = os.getenv("FLY_ORG_SLUG", "personal") # Default to personal org

def get_latest_sandbox_image() -> str:
    """
    Resolves the current deployed image from the kith-sandbox-base app at runtime.
    This avoids hardcoding stale image tags in .env — any new deployment is picked
    up automatically.
    Falls back to a known-good tag if the API call fails.
    """
    fallback = "registry.fly.io/kith-sandbox-base:deployment-01KJVFT0SHPXXB1CSHHK86RX38"
    if not FLY_API_TOKEN:
        return fallback
    try:
        resp = requests.get(
            "https://api.machines.dev/v1/apps/kith-sandbox-base/machines",
            headers={"Authorization": f"Bearer {FLY_API_TOKEN}"},
            timeout=10,
        )
        resp.raise_for_status()
        machines = resp.json()
        if machines:
            image = machines[0].get("config", {}).get("image")
            if image:
                print(f"[sandbox] Resolved sandbox image: {image}")
                return image
    except Exception as e:
        print(f"[sandbox] Could not resolve image from kith-sandbox-base, using fallback: {e}")
    return fallback

def create_and_boot_sandbox():
    """
    Creates a new Fly.io app, allocates an IP, and boots a machine using the sandbox image.
    Returns preview_url and ipv6.
    """
    if not FLY_API_TOKEN:
        print("WARN: FLY_API_TOKEN not set. Returning mock sandbox.")
        return "http://localhost:3000", "0:0:0:0:0:0:0:1"
    
    app_name = f"kith-sandbox-{uuid.uuid4().hex[:8]}"
    headers = {
        "Authorization": f"Bearer {FLY_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # 1. Create App
    print(f"Creating Fly App: {app_name}")
    create_url = f"https://api.machines.dev/v1/apps"
    payload = {
        "app_name": app_name,
        "org_slug": FLY_ORG_SLUG
    }
    resp = requests.post(create_url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()

    # 2. Allocate IPv4
    # The requirement asks for an IP, but standard fly apps only get IPv6 Anycast by default.
    # We must allocate a shared IPv4 via flyctl so it resolves on non-IPv6 Windows networks!
    import subprocess
    import shutil
    print(f"Allocating Shared IPv4 for {app_name}...")
    flyctl_path = shutil.which("flyctl") or "C:/Users/treas/.fly/bin/flyctl.exe"
    try:
        subprocess.run([flyctl_path, "ips", "allocate-v4", "-a", app_name, "--shared"], check=True, capture_output=True)
    except Exception as e:
        print(f"Warning: Failed to allocate IPv4 via flyctl: {e}")

    # 3. Create Machine
    create_machine_url = f"https://api.machines.dev/v1/apps/{app_name}/machines"
    
    machine_config = {
        "config": {
            "image": get_latest_sandbox_image(),
            "guest": {
                "cpu_kind": "shared",
                "cpus": 1,
                "memory_mb": 1024
            },
            "services": [
                {
                    "ports": [
                        {"port": 443, "handlers": ["tls", "http"]},
                        {"port": 80, "handlers": ["http"]}
                    ],
                    "protocol": "tcp",
                    "internal_port": 80,
                    "autostart": True,
                    "autostop": "suspend"
                }
            ]
        }
    }
    
    print(f"Booting Machine for {app_name}")
    try:
        machine_resp = requests.post(create_machine_url, json=machine_config, headers=headers, timeout=30)
        machine_resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Machine creation failed: {e.response.text}")
        raise e
        
    machine_data = machine_resp.json()
    machine_id = machine_data["id"]
    
    # 4. Wait for it to start
    import time
    for _ in range(30):
        print(f"Polling state for {machine_id}...")
        state_resp = requests.get(f"https://api.machines.dev/v1/apps/{app_name}/machines/{machine_id}", headers=headers, timeout=10)
        if state_resp.ok and state_resp.json().get("state") == "started":
            print(f"Machine {machine_id} started successfully!")
            break
        time.sleep(1)
    
    ipv6 = machine_data.get("private_ip")
    preview_url = f"https://{app_name}.fly.dev"
    
    print(f"Machine booted. IP: {ipv6}, URL: {preview_url}")
    return preview_url, ipv6

def send_edit_to_machine(app_name: str, file_path: str, search: str, replace: str):
    """
    Sends an edit request directly to the bridge.py running inside the Fly machine.
    We route it through the public fly proxy on port 9999 because port 80/443 points to the Vite app.
    """
    url = f"https://{app_name}.fly.dev/api/v1/edit"
    payload = {
        "file_path": file_path,
        "search_block": search,
        "replace_block": replace
    }
    
    if not FLY_API_TOKEN:
        print(f"WARN: FLY_API_TOKEN not set. Mocking edit request to {url}")
        # In a real local dev without Fly, we might hit localhost:9999 if standard docker was used.
        # For now, just return success if we are mocking.
        return {"status": "success", "mocked": True}
        
    import time
    for attempt in range(15):
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 14:
                raise e
            time.sleep(1)

def read_file_from_machine(app_name: str, file_path: str):
    """
    Reads a file from the bridge.py API running inside the Fly machine.
    """
    url = f"https://{app_name}.fly.dev/api/v1/read"
    payload = {"file_path": file_path}
    
    if not FLY_API_TOKEN:
        print(f"WARN: FLY_API_TOKEN not set. Mocking read request to {url}")
        # Return mock Vite template content if no Fly token
        if file_path == "src/App.tsx":
            return "import { useState } from 'react'\nimport reactLogo from './assets/react.svg'\nimport viteLogo from '/vite.svg'\nimport './App.css'\n\nfunction App() {\n  const [count, setCount] = useState(0)\n\n  return (\n    <>\n      <div>\n        <a href=\"https://vite.dev\" target=\"_blank\">\n          <img src={viteLogo} className=\"logo\" alt=\"Vite logo\" />\n        </a>\n        <a href=\"https://react.dev\" target=\"_blank\">\n          <img src={reactLogo} className=\"logo react\" alt=\"React logo\" />\n        </a>\n      </div>\n      <h1>Vite + React</h1>\n      <div className=\"card\">\n        <button onClick={() => setCount((count) => count + 1)}>\n          count is {count}\n        </button>\n        <p>\n          Edit <code>src/App.tsx</code> and save to test HMR\n        </p>\n      </div>\n      <p className=\"read-the-docs\">\n        Click on the Vite and React logos to learn more\n      </p>\n    </>\n  )\n}\n\nexport default App\n"
        return ""
        
    import time
    for attempt in range(15):
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 404:
                return "" # File doesn't exist yet
            resp.raise_for_status()
            return resp.json().get("content", "")
        except Exception as e:
            if attempt == 14:
                raise e
            time.sleep(1)

def write_file_to_machine(app_name: str, file_path: str, content: str):
    """
    Writes complete file content to the bridge.py API running inside the Fly machine.
    This replaces the entire file, used for full-file LLM generation.
    """
    url = f"https://{app_name}.fly.dev/api/v1/write"
    payload = {"file_path": file_path, "content": content}
    
    if not FLY_API_TOKEN:
        print(f"WARN: FLY_API_TOKEN not set. Mocking write request to {url}")
        return {"status": "success", "mocked": True}
        
    import time
    for attempt in range(15):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 14:
                raise e
            time.sleep(1)

def get_file_tree(app_name: str):
    """
    Fetches the file tree from the sandbox's /api/v1/tree endpoint.
    Raises on DNS/connection errors so callers know the sandbox is unreachable.
    """
    url = f"https://{app_name}.fly.dev/api/v1/tree"
    
    if not FLY_API_TOKEN:
        return {"tree": [
            {"name": "src", "path": "src", "type": "dir", "children": [
                {"name": "App.tsx", "path": "src/App.tsx", "type": "file"},
                {"name": "App.css", "path": "src/App.css", "type": "file"},
                {"name": "main.tsx", "path": "src/main.tsx", "type": "file"}
            ]}
        ]}
    
    import time
    last_error = None
    for attempt in range(15):
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            # DNS failure = sandbox destroyed, don't retry
            if "NameResolutionError" in str(e) or "getaddrinfo" in str(e):
                raise RuntimeError(f"Sandbox {app_name} DNS resolution failed — likely destroyed") from e
            last_error = e
            if attempt == 14:
                raise RuntimeError(f"Sandbox {app_name} unreachable after 15 attempts") from e
            time.sleep(1)
        except Exception as e:
            last_error = e
            if attempt == 14:
                raise RuntimeError(f"Sandbox {app_name} unreachable after 15 attempts") from e
            time.sleep(1)
    raise RuntimeError(f"Sandbox {app_name} unreachable") from last_error

def write_batch_to_machine(app_name: str, files: list):
    """
    Writes multiple files to the sandbox atomically via /api/v1/write_batch.
    files is a list of dicts with 'file_path' and 'content' keys.
    """
    url = f"https://{app_name}.fly.dev/api/v1/write_batch"
    payload = {"files": files}
    
    if not FLY_API_TOKEN:
        print(f"WARN: FLY_API_TOKEN not set. Mocking batch write to {url}")
        return {"status": "success", "mocked": True, "count": len(files)}
        
    import time
    for attempt in range(15):
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code in (502, 503):
                # Sandbox may be suspended/booting — longer backoff
                wait = min(3 + attempt, 10)
                print(f"[write_batch] Got {resp.status_code} (attempt {attempt + 1}), waiting {wait}s...")
                if attempt == 3:
                    # Try waking the sandbox after a few failures
                    try:
                        wake_sandbox_if_needed(app_name)
                    except Exception:
                        pass
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError:
            raise
        except Exception as e:
            if attempt == 14:
                raise e
            time.sleep(2)


def get_machine_state(app_name: str):
    """
    Return (machine_id, state) for the first machine in the app, or (None, None).
    """
    if not FLY_API_TOKEN:
        return None, None

    headers = {
        "Authorization": f"Bearer {FLY_API_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"https://api.machines.dev/v1/apps/{app_name}/machines"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        machines = resp.json() or []
        if not machines:
            return None, None
        first = machines[0]
        return first.get("id"), first.get("state")
    except Exception as e:
        print(f"Warning: failed to get machine state for {app_name}: {e}")
        return None, None


def start_machine(app_name: str, machine_id: str):
    """
    Start an existing Fly machine.
    """
    if not FLY_API_TOKEN or not machine_id:
        return False

    headers = {
        "Authorization": f"Bearer {FLY_API_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"https://api.machines.dev/v1/apps/{app_name}/machines/{machine_id}/start"
    try:
        resp = requests.post(url, headers=headers, timeout=10)
        if resp.status_code in (200, 202, 204, 409):
            return True
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Warning: failed to start machine {machine_id} for {app_name}: {e}")
        return False


def wake_sandbox_if_needed(app_name: str):
    """
    Attempt to wake an existing sandbox machine if it is suspended/stopped.
    Returns True when app appears runnable after wake attempt.
    """
    machine_id, state = get_machine_state(app_name)
    if not machine_id:
        return False

    # started/starting already fine
    if state in ("started", "starting"):
        return True

    if state in ("suspended", "stopped", "created"):
        if not start_machine(app_name, machine_id):
            return False

        import time
        for _ in range(20):
            _, current_state = get_machine_state(app_name)
            if current_state in ("started", "starting"):
                return True
            time.sleep(1)

    return False
