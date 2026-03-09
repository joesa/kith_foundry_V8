# Copilot Instructions for kith_foundry

## Environment

- **OS:** Windows
- **Project root:** `c:\Users\treas\projects\kith_foundry_V8`
- **Backend:** Python/FastAPI, uvicorn port 8000
  - **Runtime:** conda environment `kith_venv`
  - **conda executable:** `C:\Users\treas\miniconda3\Scripts\conda.exe`
  - **Python executable:** `C:\Users\treas\miniconda3\envs\kith_venv\python.exe`
  - **alembic executable:** `C:\Users\treas\miniconda3\envs\kith_venv\Scripts\alembic.exe`
  - **No `venv/` folder in backend** — always use the conda env paths above
  - Start: `cd backend && set PYTHONPATH=. && "C:\Users\treas\miniconda3\envs\kith_venv\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000`
- **Frontend:** React/TypeScript, Vite port 5173
  - Start: `cd frontend && npm run dev`

## CLI Tools Available

- `fly.exe` — Fly.io CLI (alias for flyctl)
- `flyctl.exe` — Fly.io CLI
  - Use these directly in the terminal for Fly.io operations (deploy, status, logs, machine management, etc.)
  - Example: `fly apps list`, `fly machines list -a <app-name>`, `fly logs -a <app-name>`

## Fly.io Infrastructure

- Fly API token stored in `backend/.env` as `FLY_API_TOKEN`
- Org slug: `personal`
- Sandbox base app: `kith-sandbox-base`
- Sandbox image: resolved dynamically at runtime by querying the `kith-sandbox-base` app machines list (no hardcoded tag needed)
  - Fallback tag in `fly_service.py` `get_latest_sandbox_image()` kept for when Fly API is unreachable
  - `FLY_SANDBOX_IMAGE` env var no longer used; removed from `.env`
- Sandbox URL pattern: `https://kith-sandbox-{8hex}.fly.dev`
- Machines API base: `https://api.machines.dev/v1`

## Common Tasks

### Check sandbox apps
```bash
fly apps list | grep kith-sandbox
```

### Clean up stale sandbox apps
```bash
cd backend && "C:\Users\treas\miniconda3\envs\kith_venv\python.exe" cleanup_sandboxes.py
```

### Restart backend
```bash
taskkill /F /IM python.exe 2>nul
cd backend && set PYTHONPATH=. && "C:\Users\treas\miniconda3\envs\kith_venv\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Run alembic migrations
```bash
cd backend && "C:\Users\treas\miniconda3\envs\kith_venv\Scripts\alembic.exe" upgrade head
```

### Check migration state
```bash
cd backend && "C:\Users\treas\miniconda3\envs\kith_venv\Scripts\alembic.exe" current
```
