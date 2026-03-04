"""
Destroy all Fly.io sandbox apps, EXCEPT kith-sandbox-base (which contains the Docker image).

Usage:
    cd backend && venv/Scripts/python.exe cleanup_sandboxes.py
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

PROTECTED = {"kith-sandbox-base"}

token = os.getenv("FLY_API_TOKEN")
if not token:
    print("❌ FLY_API_TOKEN not found in .env")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}
r = requests.get("https://api.machines.dev/v1/apps?org_slug=personal", headers=headers)
apps = r.json()
all_apps = apps.get("apps", apps.get("data", apps))
sandboxes = [
    a for a in all_apps
    if isinstance(a, dict)
    and "kith-sandbox" in a.get("name", "")
    and a["name"] not in PROTECTED
]

print(f"Found {len(sandboxes)} sandbox(es) to destroy (protecting: {', '.join(PROTECTED)})")

if not sandboxes:
    print("Nothing to clean up!")
    exit(0)

for a in sandboxes:
    name = a["name"]
    dr = requests.delete(f"https://api.machines.dev/v1/apps/{name}", headers=headers)
    status = "✅" if dr.status_code in (200, 202) else f"❌ {dr.status_code}"
    print(f"  {status} {name}")

print("Done!")
