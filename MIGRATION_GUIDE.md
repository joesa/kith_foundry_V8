# Migration Guide: Nhost + Fly.io

This guide covers Kith Foundry setup with **Nhost** (auth, storage, database) and **Fly.io** (sandboxes). Supabase is no longer used.

## 1. Single-Port Guard (Already Active)

The Python server now **refuses to start** if:
- Port 8000 is already in use
- Another instance holds the PID lock (`~/.kith-foundry/server-8000.pid`)

**No more killing other processes** — stop the existing server first, then start a new one.

---

## 2. Fly.io Sandboxes

### Prerequisites
- Fly.io account and `flyctl` CLI
- `FLY_API_TOKEN` in `.env` (run `fly tokens deploy` to create)

### Steps

1. **Build and push the sandbox image:**
   ```bash
   cd backend
   fly auth login
   fly deploy -a kith-sandbox-base -c fly.toml
   ```

2. **Set env vars in `.env`:**
   ```
   FLY_API_TOKEN=<your token>
   FLY_ORG_SLUG=personal
   FLY_BRIDGE_SECRET=<random 32+ char secret, or leave blank to auto-generate>
   ```

3. **Restart the backend.** Sandboxes run on Fly Machines.

---

## 3. Migrate to Nhost

### Prerequisites
- Nhost project at [app.nhost.io](https://app.nhost.io)
- Nhost Auth, Storage, and Postgres enabled

### Backend `.env` (Nhost)

```
USE_NHOST=1

NHOST_AUTH_URL=https://<your-subdomain>.auth.<region>.nhost.run
NHOST_BACKEND_URL=https://<your-subdomain>.backend.<region>.nhost.run
NHOST_ADMIN_SECRET=<from Nhost dashboard>
NHOST_GRAPHQL_URL=https://<your-subdomain>.graphql.<region>.nhost.run
NHOST_STORAGE_URL=https://<your-subdomain>.storage.<region>.nhost.run
DATABASE_URL=<Nhost Postgres connection string from Dashboard → Settings → Database>
```

### Frontend `.env` (Nhost)

```
VITE_USE_NHOST=1
VITE_NHOST_SUBDOMAIN=<your-subdomain>
VITE_NHOST_REGION=<region>
```

### Nhost Setup
1. Create a bucket `project-files` in Storage (or use default)
2. Configure Storage permissions for your app
3. Run DB migrations against Nhost Postgres (or create tables manually from `models.py`)

### Frontend Package
```bash
cd frontend
npm install @nhost/nhost-js
```

---

## 4. Env Var Reference

| Variable | Purpose |
|----------|---------|
| `FLY_API_TOKEN` | Fly Machines API token for sandboxes |
| `USE_NHOST` | `1` = Nhost auth/storage (required) |
| `VITE_USE_NHOST` | `1` = Nhost frontend auth |
| `FLY_BRIDGE_SECRET` | Secret for bridge API (optional, auto-generated if blank) |
| `NHOST_AUTH_URL` | Nhost Auth base URL |
| `NHOST_BACKEND_URL` | Nhost Backend URL |
| `NHOST_STORAGE_URL` | Nhost Storage URL (`https://<subdomain>.storage.<region>.nhost.run`) |
| `NHOST_ADMIN_SECRET` | Nhost admin secret |
| `DATABASE_URL` | Nhost Postgres connection string |

---

## 5. Inngest (C-Suite Background Jobs)

### Local development

Inngest Cloud **cannot reach localhost**. For local dev with Inngest:

1. **Set dev mode in `backend/.env`:**
   ```
   USE_INNGEST=1
   INNGEST_PRODUCTION=0
   ```

2. **Start the Inngest Dev Server** (in a separate terminal):
   ```bash
   npx --ignore-scripts=false inngest-cli@latest dev -u http://localhost:8000/api/inngest
   ```

3. **Open** [http://localhost:8288](http://localhost:8288) for the Inngest UI (functions, events, runs).

4. Start your backend. C-Suite runs will send events to the local Dev Server, which executes them.

### Production

- Set `INNGEST_PRODUCTION=1`
- Ensure your app’s public URL (e.g. `https://your-app.fly.dev`) is registered in the [Inngest dashboard](https://app.inngest.com) → App → Sync URL
- The `/api/inngest` endpoint must be reachable from the internet

### Fallback (no Inngest)

Set `USE_INNGEST=0` to run C-Suite via FastAPI `BackgroundTasks` (in-process, no Dev Server needed).
