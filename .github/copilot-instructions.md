# Copilot Instructions for kith_foundry

## Environment

- **OS:** Linux (Ubuntu)
- **Project root:** `/home/joe/repos/kith_foundry_V8`
- **Backend:** Python/FastAPI, uvicorn port 8000
  - **Runtime:** conda environment `kith_venv`
  - **conda executable:** `/home/joe/miniconda3/bin/conda`
  - **conda env path:** `/home/joe/miniconda3/envs/kith_venv`
  - **Python executable:** `/home/joe/miniconda3/envs/kith_venv/bin/python`
  - **alembic executable:** `/home/joe/miniconda3/envs/kith_venv/bin/alembic`
  - **No `venv/` folder in backend** — always use the conda env paths above
  - Activate: `conda activate kith_venv`
  - Start: `cd backend && PYTHONPATH=. /home/joe/miniconda3/envs/kith_venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000`
  - Install packages: `/home/joe/miniconda3/envs/kith_venv/bin/pip install <package>`
- **Frontend:** React/TypeScript, Vite port 5173
  - Start: `cd frontend && npm run dev`
- **Inngest:** Dev server port 8288
  - Start: `npx inngest-cli@latest dev -u http://localhost:8000/api/inngest`

## Fly.io Infrastructure

- Fly API token stored in `backend/.env` as `FLY_API_TOKEN`
- Org slug: `personal`
- Sandbox base app: `kith-sandbox-base`
- Sandbox image: resolved dynamically at runtime
- Sandbox URL pattern: `https://kith-sandbox-{8hex}.fly.dev`
- Machines API base: `https://api.machines.dev/v1`

## Common Tasks

### Restart backend
```bash
cd backend && PYTHONPATH=. /home/joe/miniconda3/envs/kith_venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Run alembic migrations
```bash
cd backend && /home/joe/miniconda3/envs/kith_venv/bin/alembic upgrade head
```

### Check migration state
```bash
cd backend && /home/joe/miniconda3/envs/kith_venv/bin/alembic current
```

### Install Python dependencies
```bash
/home/joe/miniconda3/envs/kith_venv/bin/pip install -r backend/requirements.txt
```

### Cloudflare Deployment
When any change is made that affects the frontend UI, always deploy to Cloudflare Pages automatically. Include this exact command to deploy the frontend:
```bash
cd frontend && npx wrangler pages deploy dist --project-name forge-operator --branch main
```
