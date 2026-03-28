# Control plane: Nhost, Inngest, observability (v10 doc 08)

## Data layer (Nhost PostgreSQL / Hasura)

1. Apply migration: `nhost/migrations/default/20260319120000_builder_control_plane/up.sql` via [Nhost migrations](https://docs.nhost.io/platform/cli/migrations) or paste SQL in the project database console.
2. Ensure Hasura tracks `builder_projects` and `builder_meta` (Nhost usually tracks new `public` tables automatically).
3. Set environment variables:
   - `DATA_BACKEND=nhost`
   - `NHOST_GRAPHQL_URL` — on **regional** Nhost clusters this is typically `https://<subdomain>.graphql.<region>.nhost.run/v1` (Hasura accepts POSTed GraphQL **at `/v1`**, not only `/v1/graphql`). The Hasura **console** lives under `https://<subdomain>.hasura.<region>.nhost.run/`.
   - `NHOST_ADMIN_SECRET` (Hasura admin secret; server-side only; never ship to the browser)

**Hasura metadata API** (track tables, etc.) uses `https://<subdomain>.hasura.<region>.nhost.run/v1/metadata` with `X-Hasura-Admin-Secret`.

If Hasura metadata references tables that no longer exist in Postgres, `reload_metadata` can surface inconsistencies; run **drop inconsistent metadata** (Hasura console → Settings, or Metadata API `drop_inconsistent_metadata`) before tracking new tables.

**Shell tip:** do not `source` a `.env` that contains unquoted `$`, `&`, or `<` in secrets; use a small parser (see `scripts/seed_control_plane.py`) or `fly secrets set`.
4. Seed rows from fixtures:
   ```bash
   cd backend && export NHOST_GRAPHQL_URL=... NHOST_ADMIN_SECRET=... && python -m scripts.seed_control_plane
   ```

Project documents are stored as JSONB (`payload`) matching the structure produced by `app.store.build_store()`. Meta keys: `workspace`, `orchestration_active_index`, `editor_threads`.

## Inngest (durable workflows)

Per **08_scaling_and_reliability_stack.md**: background jobs, retries, idea-expiry scans, fan-out.

- Set `INNGEST_EVENT_KEY` (and in production `INNGEST_SIGNING_KEY`) from the Inngest dashboard.
- For local dev with [Inngest Dev Server](https://www.inngest.com/docs/dev-server): set `INNGEST_DEV=1`; the API mounts `POST/PUT /api/inngest`.
- Events emitted today (non-blocking): `forge/editor.message`, `forge/capabilities.updated`, `forge/ideation.completed`.
- Cron: `forge-idea-expiry-scan` every 6 hours (stub — wire to Nhost `saved_idea_events` / notifications).

## Upstash Redis (optional)

- **TCP** — set `UPSTASH_REDIS_URL` (or `REDIS_URL`) to the `rediss://` URL from the console. Used by `redis-py` in `app/cache/redis_client.py`.
- **REST** — set `UPSTASH_REDIS_REST_URL` (HTTPS origin only, e.g. `https://xxx.upstash.io`) and `UPSTASH_REDIS_REST_TOKEN`. Wrong paste shapes like `http://host:6379` are normalized to `https://host`. If both TCP and REST are set, **TCP wins**.

`GET /api/health?deep=1` includes `redis_reachable` after a live `PING` when Redis is configured.

## OpenTelemetry + Sentry

- `OTEL_EXPORTER_OTLP_ENDPOINT` — e.g. `https://otel.example.com/v1/traces` (HTTP OTLP). Sets service name via `OTEL_SERVICE_NAME` (default `operator-one-control-plane`).
- `SENTRY_DSN` — FastAPI integration + traces sample rate `SENTRY_TRACES_SAMPLE_RATE` (default `0.1`).

## Health

`GET /api/health` reports `data_backend`, and whether Inngest / OTel / Sentry / Redis are configured.

## Fly.io (control-plane API)

The backend can run on Fly with the included `backend/Dockerfile` and `backend/fly.toml` (app name `aoc-control-plane`). Example:

```bash
cd backend
fly secrets set DATA_BACKEND=nhost NHOST_GRAPHQL_URL=... NHOST_ADMIN_SECRET=... INNGEST_EVENT_KEY=... INNGEST_SIGNING_KEY=...
fly deploy
```

Deployed URL (current): `https://aoc-control-plane.fly.dev` — use this as `VITE_API_BASE_URL` if the UI talks to the cloud API (add its **origin** to `main.py` CORS if you use a different frontend host).
