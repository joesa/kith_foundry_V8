# Python environment (Conda)

The backend uses a dedicated Conda env **`operatorone-v2`** (Python 3.12), defined in [`environment.yml`](../environment.yml) at the repo root.

## Create or refresh

From the repo root:

```bash
conda env create -f environment.yml    # first time
conda env update -f environment.yml --prune   # after dependency changes
```

## Activate (interactive shells)

```bash
conda activate operatorone-v2
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Cursor / VS Code

The workspace [`.vscode/settings.json`](../.vscode/settings.json) points the Python interpreter at this env.

## npm

`npm run dev:api` runs Uvicorn via `conda run -n operatorone-v2` so it does not rely on a pre-activated shell. Override the Conda install path with `CONDA_EXE` if your `conda` binary is not `$HOME/miniconda3/bin/conda`.

### Inngest (local)

1. Set **`INNGEST_PRODUCTION=0`** (or **`INNGEST_DEV=1`**) in `backend/.env` so the Python SDK uses Dev Server mode.
2. Start the API: `npm run dev:api`.
3. Start the dev server: `npm run dev:inngest` → UI at **http://127.0.0.1:8288**, syncing **http://127.0.0.1:8000/api/inngest**.
