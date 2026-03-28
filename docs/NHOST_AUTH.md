# Nhost Auth (login / register / logout)

The Forge UI uses [**Nhost Auth**](https://docs.nhost.io/products/auth) with `@nhost/react` for email + password sign-in and registration.

## Frontend environment

In **`.env.development`** (or **`.env`** at the repo root), set:

| Variable | Example | Notes |
|----------|---------|--------|
| `VITE_NHOST_SUBDOMAIN` | `abcdefgh` | Project subdomain from the Nhost dashboard URL |
| `VITE_NHOST_REGION` | `us-east-1` | Same region as the project |
| `VITE_NHOST_AUTH_PROXY` | *(omit)* | In **`npm run dev`**, Auth uses a **same-origin proxy** (`/__nhost/auth` → Nhost Auth) so the browser avoids CORS on `*.auth.*.nhost.run`. Set to `0` or `false` to disable and call Auth directly (then you must allow the dev origin in Nhost — see below). |

These must match **`NHOST_SUBDOMAIN`** / **`NHOST_REGION`** in `backend/.env` for the same Nhost project.

### CORS (blocked preflight to `/v1/signup/...` or `/v1/token`)

The browser only sees **cross-origin** CORS when the app calls `https://<subdomain>.auth.<region>.nhost.run` directly. This repo’s Vite config proxies **`/__nhost/auth`** to that host, and the Nhost client sets **`authUrl`** to `http://localhost:5173/__nhost/auth/v1` in dev (unless `VITE_NHOST_AUTH_PROXY=0`), so requests stay **same-origin** and CORS does not apply to Auth.

You should still add **`http://localhost:5173`** (and **`http://127.0.0.1:5173`**) under your Nhost project’s **allowed URLs / client URLs** where the dashboard offers them — that matches production origins and any flow that bypasses the proxy.

If you use **`vite preview`** (production build), `import.meta.env.DEV` is false: set **`VITE_NHOST_AUTH_PROXY=true`** in the env file you load for that command, or rely on Nhost’s allowlist alone.

If either variable is missing, the app **does not** mount `NhostProvider`: `/app/*` stays open without login, and the login page explains how to configure env vars.

## Nhost dashboard

1. Open your project in [Nhost](https://app.nhost.io) → **Authentication** → **Settings**.
2. Enable **Email and password** (and optionally **Email verification**).
3. Under **Site URL** and allowed redirects, add:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
   - Production origins when you deploy (e.g. `https://your-domain.com`).
4. If **email verification** is required, new users see an on-screen message to check email before they can sign in.

## Routes

| Path | Behavior |
|------|----------|
| `/login` | Sign in; tab **Register** or query `?mode=signup` |
| `/register` | Redirects to `/login?mode=signup` |
| `/app/*` | Requires a valid Nhost session when `VITE_NHOST_*` is set |

**Log out** is in the top command bar (session email + **Log out**).

## Control plane API and JWT

The FastAPI backend does not validate Nhost JWTs yet. To enforce server-side auth later, verify the `Authorization: Bearer <access_token>` header with Nhost’s JWT secret / JWKS and map `x-hasura-*` claims for Hasura.

## Troubleshooting: `POST …/v1/token` 500

The React SDK restores a **refresh token** from `localStorage` on startup and exchanges it at `https://<subdomain>.auth.<region>.nhost.run/v1/token`.

1. **Stale client session (most common after project changes)**  
   The app runs a **one-time storage reset** when our internal epoch bumps (see `bootstrapNhostStorageOnce` in `src/lib/nhost-session-storage.ts`).  
   To force a reset anytime, open: `http://localhost:5173/?clearNhost=1` (or your dev origin).  
   You can also use **“Clear saved session & reload”** (amber banner) or on `/login` **“Clear saved Nhost session”**, or delete keys starting with `nhost` in DevTools → Application → Local Storage.

2. **Nhost Auth service error**  
   In the Nhost dashboard, open **Logs** for the **Auth** service and check for panic/config errors (JWT secret, database, migrations).

3. **Email/password or verification**  
   Confirm **Authentication → Sign-in methods → Email+password** is enabled and **Site URL** / redirects include your dev origin (`http://localhost:5173`, etc.).

## Troubleshooting: `POST …/v1/signup/email-password` 500

This is handled entirely by **Nhost Auth** on their side. The app cannot fix a 500 with a code change; fix configuration or check service logs.

1. **Nhost dashboard → Logs**  
   Open **Auth** (or project) logs at the time of the request. Look for database errors, migration failures, or SMTP/email provider failures.

2. **Email + password**  
   Under **Authentication → Sign-in methods**, ensure **Email and password** is enabled.

3. **Email verification + SMTP**  
   If **email verification** is required, configure a working **SMTP** (or Nhost’s email integration). A missing or invalid SMTP setup can cause sign-up to fail on the server.

4. **Same project as env**  
   `VITE_NHOST_SUBDOMAIN` / `VITE_NHOST_REGION` must match the project you are debugging (wrong subdomain still “works” for HTTP but hits a different backend).

After submitting the form, the login page shows the **error message returned by Nhost** (when present) so you can distinguish validation errors from generic 500s.

### Postgres: `column "email" of relation "users" does not exist`

Auth logs may show:

`error inserting user with refresh token: ERROR: column "email" of relation "users" does not exist`

That means **`auth.users` is not the full Hasura Auth schema** (manual edits, partial restore, or broken migration). The Auth service issues inserts that match [Nhost’s auth migrations](https://github.com/nhost/nhost/tree/main/services/auth/go/migrations/postgres).

**Fix:** apply the repair migration in this repo: `nhost/migrations/default/20260320080000_repair_auth_users_schema/up.sql` (Nhost CLI deploy, or paste into **Database → SQL** if you have no production data in `auth.users` yet). It adds missing columns (including `email` and `metadata`) to align with upstream.

If anything fails (duplicate constraint names, wrong pre-existing types), compare your `auth.users` definition to a fresh Nhost project or open a ticket with Nhost support — do not hand-edit `auth.*` without matching the official migrations.
