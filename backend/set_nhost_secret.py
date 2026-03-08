"""
One-time script: push PROVIDER_ENCRYPTION_KEY to Nhost Config as a secret.

Usage:
    cd backend && venv/Scripts/python.exe set_nhost_secret.py

Uses the Nhost CLi management GraphQL API (same backend the CLI uses).
The secret will appear under Settings → Secrets in the dashboard.
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

NHOST_SUBDOMAIN = os.getenv("NHOST_SUBDOMAIN", "kbdcjctqvdyoiolohuwc")
NHOST_PAT       = os.getenv("NHOST_PAT", "")
ENCRYPTION_KEY  = os.getenv("PROVIDER_ENCRYPTION_KEY", "")

if not NHOST_PAT:
    print("ERROR: Set NHOST_PAT=<your-token> in .env or environment.")
    print("       Generate at: https://app.nhost.io/account/pat")
    sys.exit(1)

if not ENCRYPTION_KEY:
    print("ERROR: PROVIDER_ENCRYPTION_KEY not set in .env")
    sys.exit(1)

# These are the Nhost management plane endpoints (from the CLI source)
MGMT_AUTH_URL  = "https://otsispdzcwxyqzbfntmj.auth.eu-central-1.nhost.run/v1"
MGMT_GQL_URL   = "https://otsispdzcwxyqzbfntmj.graphql.eu-central-1.nhost.run/v1"

GET_APPS_QUERY = """
query GetOrgsAndApps {
  organizations { name apps { id name subdomain } }
  workspaces     { name apps { id name subdomain } }
}
"""

INSERT_SECRET = """
mutation CreateSecret($appID: uuid!, $name: String!, $value: String!) {
  insertSecret(appID: $appID, secret: {name: $name, value: $value}) {
    name
  }
}
"""

UPDATE_SECRET = """
mutation UpdateSecret($appID: uuid!, $name: String!, $value: String!) {
  updateSecret(appID: $appID, secret: {name: $name, value: $value}) {
    name
  }
}
"""

GET_SECRETS = """
query GetSecrets($appID: uuid!) {
  appSecrets(appID: $appID) { name }
}
"""

with httpx.Client(timeout=20) as client:
    # 1. Exchange PAT for a bearer token
    print("Authenticating with PAT...")
    r = client.post(
        f"{MGMT_AUTH_URL}/signin/pat",
        json={"personalAccessToken": NHOST_PAT},
        headers={"Content-Type": "application/json"},
    )
    if r.status_code != 200:
        print(f"ERROR: PAT auth failed ({r.status_code}): {r.text}")
        sys.exit(1)
    access_token = r.json()["session"]["accessToken"]
    print("  Authenticated OK")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # 2. Find app ID by subdomain
    r = client.post(MGMT_GQL_URL, json={"query": GET_APPS_QUERY}, headers=headers)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        print(f"ERROR fetching apps: {data['errors']}")
        sys.exit(1)

    app_id = None
    for group in (data["data"].get("organizations", []) + data["data"].get("workspaces", [])):
        for app in group.get("apps", []):
            if app["subdomain"] == NHOST_SUBDOMAIN:
                app_id = app["id"]
                print(f"Found app: {app['name']} ({app_id})")
                break
        if app_id:
            break

    if not app_id:
        print(f"ERROR: No app found with subdomain '{NHOST_SUBDOMAIN}'")
        sys.exit(1)

    # 3. Check if secret already exists
    r = client.post(MGMT_GQL_URL, json={"query": GET_SECRETS, "variables": {"appID": app_id}}, headers=headers)
    r.raise_for_status()
    existing = {s["name"] for s in r.json().get("data", {}).get("appSecrets", [])}
    exists = "PROVIDER_ENCRYPTION_KEY" in existing

    # 4. Insert or update
    mutation = UPDATE_SECRET if exists else INSERT_SECRET
    r = client.post(
        MGMT_GQL_URL,
        json={"query": mutation, "variables": {"appID": app_id, "name": "PROVIDER_ENCRYPTION_KEY", "value": ENCRYPTION_KEY}},
        headers=headers,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        print(f"GraphQL error: {data['errors']}")
        sys.exit(1)

    action = "Updated" if exists else "Created"
    print(f"✓ {action} PROVIDER_ENCRYPTION_KEY in Nhost Secrets.")
    print("  Visible at: Nhost dashboard → your project → Settings → Secrets")
