"""
Inngest client — shared singleton for the whole backend.

Env vars:
  INNGEST_SIGNING_KEY   — from Inngest dashboard (required in production)
  INNGEST_EVENT_KEY     — from Inngest dashboard (required in production)
  INNGEST_PRODUCTION    — set to "1" when deployed; "0" = dev mode (local Dev Server)
  INNGEST_DEV           — set to "1" to force dev mode (same as INNGEST_PRODUCTION=0)
  INNGEST_EVENT_API_BASE_URL — when in dev mode, set to http://localhost:8288 so
                               events go to the local Dev Server (not Inngest Cloud)
  USE_INNGEST           — set to "1" to route C-Suite jobs through Inngest;
                          "0" (default) keeps the existing FastAPI BackgroundTasks path

When USE_INNGEST=0 the client is still initialised so the /api/inngest endpoint
works for testing, but csuite_api.py won't send events to it.

LOCAL DEV: Inngest Cloud cannot reach localhost. Use INNGEST_PRODUCTION=0 (or
INNGEST_DEV=1) and run the Inngest Dev Server:
  npx --ignore-scripts=false inngest-cli@latest dev -u http://localhost:8000/api/inngest
"""
import os
import inngest

# Dev mode: INNGEST_DEV=1 or INNGEST_PRODUCTION=0 — events go to local Dev Server
_inngest_dev = os.environ.get("INNGEST_DEV", "").strip() == "1"
_inngest_prod = os.environ.get("INNGEST_PRODUCTION", "0").strip() == "1"
_is_production = _inngest_prod and not _inngest_dev

# When in dev mode, point event API at local Dev Server (default port 8288)
_event_base_url = None
if not _is_production:
    _event_base_url = os.environ.get(
        "INNGEST_EVENT_API_BASE_URL", "http://localhost:8288"
    )

client = inngest.Inngest(
    app_id="kith-foundry",
    signing_key=os.environ.get("INNGEST_SIGNING_KEY", ""),
    is_production=_is_production,
    event_key=os.environ.get("INNGEST_EVENT_KEY") or None,
    event_api_base_url=_event_base_url,
)

def use_inngest() -> bool:
    """Return True if Inngest routing is enabled via USE_INNGEST=1."""
    return os.environ.get("USE_INNGEST", "0").strip() == "1"
