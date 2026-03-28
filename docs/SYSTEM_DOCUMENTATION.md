# Kith Foundry — Complete System Documentation

> **Purpose**: Comprehensive reference for recreating the entire Kith Foundry application.  
> **Generated**: Session documentation from full codebase analysis.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Environment & Configuration](#3-environment--configuration)
4. [Database Schema](#4-database-schema)
5. [Backend Architecture](#5-backend-architecture)
6. [API Reference](#6-api-reference)
7. [Background Job System (Inngest)](#7-background-job-system-inngest)
8. [C-Suite Agent System](#8-c-suite-agent-system)
9. [Multi-Agent Code Generation Pipeline](#9-multi-agent-code-generation-pipeline)
10. [Design Engine](#10-design-engine)
11. [Fly.io Sandbox System](#11-flyio-sandbox-system)
12. [LLM Infrastructure](#12-llm-infrastructure)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Frontend Routing](#14-frontend-routing)
15. [Frontend Components](#15-frontend-components)
16. [Frontend Design System](#16-frontend-design-system)
17. [Authentication Flow](#17-authentication-flow)
18. [Real-Time Updates](#18-real-time-updates)
19. [Billing & Usage Limits](#19-billing--usage-limits)
20. [Export System](#20-export-system)
21. [Security & Encryption](#21-security--encryption)
22. [Deployment Configuration](#22-deployment-configuration)
23. [End-to-End User Flow](#23-end-to-end-user-flow)
24. [File Index](#24-file-index)

---

## 1. System Overview

Kith Foundry is a **multi-agent AI application builder** platform that takes users from idea → validated business plan → designed system → deployed code. The platform orchestrates:

1. **Ideation** — AI-powered idea generation, enhancement, and deduplication
2. **Executive Analysis** — 9 parallel C-Suite AI agents (CEO, CTO, CFO, CMO, CPO, COO, CDO, CISO, Synthesizer) evaluate the idea
3. **Artifact Generation** — 12+ document types (PRD, tech spec, financial model, design system, etc.)
4. **Design Engine** — GPT-powered design brief + design system generation with product/style mode classification
5. **Capability Gate** — User selects database, auth, AI capabilities
6. **Code Generation** — 4-stage multi-agent pipeline (Intent → Layout → Component → Code) with AST validation
7. **Sandbox Deployment** — Live preview via Fly.io Machines with Vite dev server
8. **Error Resolution** — Auto-fix loop with tree-sitter AST validation

---

## 2. Technology Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.13) |
| Server | uvicorn (dev) / gunicorn (prod, 4 workers) |
| ORM | SQLAlchemy 2.x (sync + async) |
| Async DB Driver | asyncpg |
| Database | PostgreSQL (Nhost-hosted) |
| Migrations | Alembic |
| Job Queue | Inngest (optional, with BackgroundTasks fallback) |
| Cache/PubSub | Redis (sync via redis-py, async via aioredis) |
| LLM Gateway | litellm (multi-provider) |
| AST Parsing | tree-sitter (TypeScript, JavaScript, CSS) |
| Rate Limiting | slowapi (30/min on LLM endpoints) |
| Export | python-docx, fpdf2 |
| Embeddings | litellm + pgvector |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 19.2.0 + TypeScript 5.9.3 |
| Build Tool | Vite 7.3.1 |
| Styling | TailwindCSS 4.2.1 + @tailwindcss/vite |
| State | React Context API (AuthContext, ThemeContext) |
| Auth Client | Nhost v4 (@nhost/nhost-js ^4.0.0) |
| Animation | Framer Motion 12.34.4 |
| Icons | Lucide React + Material Symbols Outlined |
| Markdown | React-Markdown 10.1.0 + remark-gfm |
| Router | React Router DOM 7.13.1 |
| Code Editor | Monaco Editor (@monaco-editor/react ^4.7.0) |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Sandbox Hosting | Fly.io Machines API |
| Auth Provider | Nhost (primary) / Supabase (alternative) |
| Payments | Stripe (Checkout Sessions) |
| DNS | Fly.io managed (*.fly.dev) |

---

## 3. Environment & Configuration

### Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql://...          # PostgreSQL DSN (required)
PGBOUNCER=true                         # Enable PgBouncer pooling (port 6543)

# Authentication
NHOST_DOMAIN=<subdomain>.nhost.run     # Nhost domain
NHOST_ADMIN_SECRET=<secret>            # Nhost admin secret
USE_NHOST=1                            # Enable Nhost auth (vs Supabase)
SUPABASE_URL=                          # Supabase URL (alternative)
SUPABASE_KEY=                          # Supabase anon key (alternative)

# API Keys (LLM Providers)
ANTHROPIC_API_KEY=                     # Claude models (primary)
OPENAI_API_KEY=                        # GPT models (optional)
GEMINI_API_KEY=                        # Gemini models (optional)
OPENROUTER_API_KEY=                    # OpenRouter (optional)

# Encryption
PROVIDER_ENCRYPTION_KEY=              # Base64url 32-byte key for AES-256-GCM
SECRET_ENCRYPTION_KEY=                # Fernet key for user secrets

# Inngest
USE_INNGEST=1                         # Enable Inngest job queue
INNGEST_PRODUCTION=1                  # Production mode (no dev server)
INNGEST_DEV_SERVER_URL=http://localhost:8288

# Fly.io
FLY_API_TOKEN=                        # Fly.io API token
KITH_PID_DIR=~/.kith-foundry          # PID lock directory

# Stripe Billing
STRIPE_SECRET_KEY=
STRIPE_PRICE_INDIE_MONTHLY=
STRIPE_PRICE_PRO_MONTHLY=
STRIPE_PRICE_TEAM_MONTHLY=
STRIPE_PRICE_ENTERPRISE_MONTHLY=
STRIPE_PRICE_INDIE_ANNUAL=
STRIPE_PRICE_PRO_ANNUAL=
STRIPE_PRICE_TEAM_ANNUAL=
STRIPE_PRICE_PACK_CSUITE=
STRIPE_PRICE_PACK_DESIGN=
STRIPE_COUPON_BYOK_20PCT=
STRIPE_COUPON_ANNUAL_20PCT=

# Runtime
KITH_FORCE_CLEAR_LOCK=1              # Force clear stale PID lock
```

### Frontend Environment Variables

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_NHOST_SUBDOMAIN=<subdomain>
VITE_NHOST_REGION=<region>
VITE_USE_NHOST=1
# Optional: VITE_WS_URL=ws://localhost:8000
```

### Development Commands

```bash
# Backend
cd backend && PYTHONPATH=. /home/joe/miniconda3/envs/kith_venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev    # Port 5173, proxies /api → localhost:8000

# Inngest Dev Server
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest

# Migrations
cd backend && /home/joe/miniconda3/envs/kith_venv/bin/alembic upgrade head

# Install deps
/home/joe/miniconda3/envs/kith_venv/bin/pip install -r backend/requirements.txt
```

---

## 4. Database Schema

### Enums

```python
ProjectStatus = [
    "ideation", "csuite_pending", "csuite_running", "csuite_complete",
    "prd_generating", "prd_complete", "design_generating", "design_complete",
    "capability_gate", "secrets_pending", "building", "build_complete", "deployed"
]

CSuiteRole = ["ceo", "cto", "cfo", "cmo", "cpo", "coo", "cdo", "ciso", "synthesizer"]

AgentStatus = ["pending", "running", "complete", "error"]

ArtifactType = [
    "exec_summary", "product_requirements", "tech_architecture", "db_plan",
    "auth_plan", "implementation_phases", "design_tokens", "design_system",
    "design_components", "financial_model", "gtm_plan", "api_docs",
    "bootstrap_prompt", "market_analysis", "user_personas", "competitive_matrix",
    "roadmap", "monetization"
]

IdeaSource = ["unique_gen", "questionnaire", "user_prompt"]

SubscriptionTier = ["free", "indie", "pro", "team", "enterprise"]
SubscriptionStatus = ["active", "trialing", "past_due", "canceled", "unpaid"]
```

### Core Tables

**User**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| email | String (unique) | |
| display_name | String | |
| is_super_admin | Boolean | Default false |
| created_at | DateTime | |
| last_login | DateTime | |

**Project**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| name | String | |
| description | Text | |
| target_audience | String | |
| problem_statement | Text | |
| status | ProjectStatus enum | |
| product_mode | String | Design mode |
| style_mode | String | Design style |
| mode_confidence | Float | |
| design_mode_locked | Boolean | |
| fly_sandbox_id | String | Fly machine ID |
| preview_url | String | Sandbox URL |
| auto_save_enabled | Boolean | |
| design_preferences | JSON | |

**Idea**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| name | String | |
| content | JSON | Full idea object |
| score | Integer | 0-100 |
| source | IdeaSource enum | |
| is_used | Boolean | |

**GeneratedIdeaGlobal** — Global dedup table
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| idea_hash | String (unique) | SHA256 of normalized content |
| summary | Text | |
| claimed_by | UUID (FK → User) | |
| claimed_at | DateTime | |

**SavedIdea** — User's saved ideas
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| name | String | |
| content | JSON | |
| score | Integer | |
| source | IdeaSource | |
| idea_hash | String | |
| is_claimed | Boolean | |
| saved_expires_at | DateTime | |
| uniqueness_degraded | Boolean | |

**CSuiteAnalysis** — C-Suite agent results
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK → Project) | |
| agent_role | CSuiteRole enum | |
| analysis | JSON | Full analysis payload |
| score | Integer | 0-100 |
| status | AgentStatus enum | |
| error_message | String | |
| Unique constraint | (project_id, agent_role) | |

**Artifact** — Generated documents
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK → Project) | |
| artifact_type | ArtifactType enum | |
| title | String | |
| content | JSON | |
| status | AgentStatus enum | |
| Unique constraint | (project_id, artifact_type) | |

**File** — Source code metadata
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK → Project) | |
| file_path | String | |
| content | Text (nullable) | Legacy - content now in storage |
| updated_at | DateTime | |
| Unique constraint | (project_id, file_path) | |

**Message** — Project chat history
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK → Project) | |
| role | String | "user" or "assistant" |
| content | Text | |
| created_at | DateTime | |

**ProviderKey** — User API keys
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| name | String | Display name |
| provider | String | openai, anthropic, etc. |
| api_key_encrypted | String | AES-256-GCM encrypted |
| base_url | String | Custom endpoint |
| is_default | Boolean | |
| is_active | Boolean | |
| created_at | DateTime | |
| last_used_at | DateTime | |

**ModelRouting** — Per-task model assignments
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| task_type | String | code_gen, csuite, design, ideation, artifacts |
| provider_id | UUID (FK → ProviderKey) | |
| model_id | String | |
| Unique constraint | (user_id, task_type) | |

### Billing Tables

**Subscription**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (unique FK → User) | |
| tier | SubscriptionTier | |
| status | SubscriptionStatus | |
| stripe_customer_id | String | |
| stripe_subscription_id | String | |
| stripe_price_id | String | |
| current_period_start | DateTime | |
| current_period_end | DateTime | |
| seat_count | Integer | |
| byok_discount_applied | Boolean | |
| is_annual | Boolean | |

**UsageRecord**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| billing_month | String | YYYY-MM |
| csuite_runs | Integer | |
| design_screens | Integer | |
| artifact_sets | Integer | |
| project_count | Integer | |
| Unique constraint | (user_id, billing_month) | |

**UsagePack** — Add-on usage packs
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| pack_type | String | csuite_runs or design_screens |
| pack_size | Integer | |
| remaining | Integer | |
| stripe_payment_intent | String | |
| purchased_at | DateTime | |
| expires_at | DateTime | |

### Project Brain Tables

**ProjectPage**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| page_name | String | |
| route | String | |
| description | Text | |
| layout_json | JSON | |
| status | String | |

**ProjectComponent**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| component_name | String | |
| file_path | String | |
| props_schema_json | JSON | |
| dependencies_json | JSON | |
| description | Text | |

**ProjectSection**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| page_id | UUID (FK → ProjectPage) | |
| section_name | String | |
| section_type | String | |
| description | Text | |
| component_refs_json | JSON | |
| sort_order | Integer | |

**ProjectFeature**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| feature_name | String | |
| status | String | |
| description | Text | |
| files_json | JSON | |

**ProjectDecision**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| decision_type | String | layout, component, routing, styling, data_model, library, architecture |
| decision_json | JSON | |
| rationale | Text | |
| agent_role | String | |

**ProjectEmbedding**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| content_type | String | file, page, component, section, decision, message |
| content_ref_id | String | |
| content_text | Text | |
| embedding | Vector (pgvector) | |
| created_at | DateTime | |

### Secrets & Capabilities Tables

**EncryptedUserSecret**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK) | |
| user_id | UUID (FK) | |
| provider | String | |
| label | String | |
| encrypted_value | String | |
| created_at | DateTime | |
| last_accessed_at | DateTime | |
| revoked_at | DateTime | Null = active |

**SecretAccessAudit**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| secret_id | UUID (FK) | |
| accessed_by | String | |
| action | String | created or revoked |
| created_at | DateTime | |

**CapabilityChoice**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| project_id | UUID (FK, unique) | |
| wants_database | Boolean | |
| wants_auth | Boolean | |
| wants_ai | Boolean | |
| notes | Text | |

---

## 5. Backend Architecture

### Entry Point: `main.py`

- **Port Guard**: PID locking prevents duplicate instances
- **Startup Recovery**: Resets orphaned CSuite 'running' rows to 'pending'
- **CORS**: Allow-all in dev, restricted in production
- **Rate Limiting**: Global limiter via slowapi (30/min on LLM endpoints)
- **Router Registration Order**: design_api, projects_api, ideation_api, csuite_api, artifacts_api, export_api, routing_api, billing_api, capabilities_api, secrets_api, deploy_api, sandbox_api
- **Inngest Integration**: `/api/inngest` endpoint for durable job queuing
- **Health Check**: `GET /api/health` → Redis + circuit breaker status
- **SSE Stream**: `GET /api/v1/projects/{project_id}/events` → Redis pub/sub

### Database Configuration: `models.py`

- PostgreSQL (production) or SQLite (dev fallback)
- Async engine via asyncpg for non-blocking I/O
- PgBouncer transaction-mode pooling support (`PGBOUNCER=true`)
- Connection pooling: 20 pool + 40 max_overflow (or 2/3 for PgBouncer)
- SSL: Explicit `ssl.SSLContext` with `CERT_NONE` for asyncpg (avoids OCSP timeout)
- `run_sync()` bridge: allows sync ORM code in async endpoints

### Core Backend Files

| File | Purpose |
|------|---------|
| `main.py` | App entry, middleware, WebSocket, health, SSE |
| `models.py` | SQLAlchemy models, engines, session factories |
| `csuite_agent.py` | 9 C-Suite agent orchestration |
| `csuite_api.py` | C-Suite API endpoints + background job triggers |
| `agent_pipeline.py` | 4-stage code generation pipeline |
| `agent.py` | Main agent/chat handler with streaming JSON parser |
| `artifacts_api.py` | Document generation (12 artifact types) |
| `design_api.py` | Design mode classification + engine endpoints |
| `design_engine.py` | GPT Design Engine pipeline |
| `design_mode_service.py` | Design mode classification from pack.json |
| `design_context.py` | Design context builder (CDO + CSS vars) |
| `design_intelligence.py` | Vendor lookup, brief generation |
| `fly_service.py` | Fly.io sandbox worker |
| `sandbox_pool.py` | Pre-warm sandbox pool management |
| `sandbox_policy.py` | Security policy validation |
| `bridge.py` | Sandbox microservice (runs inside Fly machines) |
| `brain_service.py` | Project brain/knowledge base |
| `error_resolver.py` | Auto error resolver (AST + rules + LLM) |
| `patch_engine.py` | tree-sitter AST validation |
| `context_compression.py` | 5-layer context compression |
| `model_resolver.py` | Central model routing/resolution |
| `circuit_breaker.py` | Per-provider circuit breaker |
| `embedding_service.py` | Text embedding + pgvector |
| `prompts.py` | All system prompts |
| `ideation_prompts.py` | Questionnaire + idea generation prompts |
| `auth_nhost.py` | Nhost JWT validation (HS256 + RS256 JWKS) |
| `storage_service.py` | File storage abstraction |
| `export_service.py` | MD/DOCX/PDF rendering |
| `billing_api.py` | Stripe integration + usage limits |
| `redis_client.py` | Redis sync/async singletons |
| `redis_state.py` | Redis pub/sub channels + state |
| `inngest_client.py` | Inngest client singleton |
| `inngest_functions.py` | Inngest function definitions |
| `rate_limiter.py` | slowapi rate limiter config |

---

## 6. API Reference

### Projects (`/api/v1/projects`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all user projects (ordered by updated_at DESC) |
| POST | `/` | Create new project |
| GET | `/{project_id}` | Get single project (with overall_score + verdict) |
| PATCH | `/{project_id}` | Update project fields |
| DELETE | `/{project_id}` | Delete project + all Storage files |
| POST | `/{project_id}/reindex` | Re-embed all entities for semantic search |
| GET | `/{project_id}/embeddings/status` | Check embedding index status |

### Ideation (`/api/v1/ideation`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enhance` | Return 3 enhanced idea variations via LLM |
| POST | `/accept` | Accept idea → create Project + Idea record |
| POST | `/generate-unique` | Generate globally unique idea (never shown before) |
| POST | `/questionnaire` | Process questionnaire → generate 3 personalized ideas |
| GET | `/questionnaire/questions` | Return 15-question survey definition |
| POST | `/save` | Save idea for later without claiming |
| GET | `/saved` | List user's saved ideas |
| POST | `/saved/{saved_id}/claim` | Claim saved idea → create Project |
| DELETE | `/saved/{saved_id}` | Delete saved idea |

**Dedup Strategy**: SHA256(name+desc+target_market+why_now, lowercase, slug) → `GeneratedIdeaGlobal` for uniqueness, `SavedIdea.is_claimed` for exclusivity.

### C-Suite (`/api/v1/csuite`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/{project_id}/run` | Start 7-agent parallel analysis |
| POST | `/{project_id}/stop` | Stop all pending/running agents |
| POST | `/{project_id}/stop/{role}` | Stop single agent by role |
| GET | `/{project_id}/status` | Real-time status of all agents |
| GET | `/{project_id}/results` | Completed analyses + overall verdict |
| POST | `/{project_id}/refine` | Re-run with user corrections |
| POST | `/{project_id}/improve` | AI self-analyze + generate improvement plan |
| GET | `/{project_id}/improve-plan/{job_id}` | Poll for async improvement plan |
| POST | `/{project_id}/improve/apply` | Re-run selected agents with enhanced context |

**Rate Limit**: 30/minute on /run, /refine, /improve/apply  
**Billing Gate**: `enforce_csuite_limit()` raises 402 if quota exceeded

### Artifacts (`/api/v1/projects`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{project_id}/artifacts` | List all artifact types + statuses |
| POST | `/{project_id}/artifacts/generate` | Queue all artifacts for generation |
| GET | `/{project_id}/artifacts/{id}` | Get single artifact by ID or key |
| POST | `/{project_id}/artifacts/generate-single/{key}` | Regenerate one artifact |
| POST | `/{project_id}/artifacts/regenerate-all` | Reset all to pending |
| POST | `/{project_id}/artifacts/{id}/regenerate` | Regenerate specific artifact |
| POST | `/{project_id}/bootstrap-prompt` | Build comprehensive code-gen prompt |
| GET | `/{project_id}/bootstrap-prompt` | Fetch previously generated bootstrap prompt |

**12 Artifact Types**: executive_brief, prd, tech_spec, db_plan, auth_plan, implementation_phases, market_analysis, go_to_market, user_personas, competitive_matrix, roadmap, monetization, design_system

### Design (`/api/v1/projects/{project_id}/design`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/mode-options` | All product modes + style modes |
| POST | `/classify-mode` | Auto-infer best mode+style |
| POST | `/lock-mode` | Lock user's design selection |
| POST | `/unlock-mode` | Unlock auto-classification |
| GET | `/mode-history` | Recent mode selections |
| POST | `/engine/brief` | Generate design intelligence brief |
| POST | `/engine/generate` | Run full pipeline (brief → system) |
| GET | `/engine/modes` | Same as /mode-options |
| GET | `/engine/system` | Fetch previously generated design system |

### Capabilities (`/api/v1/projects`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{project_id}/capabilities` | Get user's capability selections |
| POST | `/{project_id}/capabilities` | Set capability choices (database, auth, AI) |

### Secrets (`/api/v1`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{project_id}/secrets` | List active secrets |
| POST | `/projects/{project_id}/secrets` | Create encrypted secret |
| POST | `/secrets/{secret_id}/revoke` | Revoke secret |

### Sandbox (`/api/v1/projects`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{project_id}/sandbox/status` | Sandbox status + preview URL |
| GET | `/{project_id}/sandbox/logs` | Tail sandbox logs |

### Deploy (`/api/v1/projects`) — Stubs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/{project_id}/deploy/git-connect` | Git connection (stub) |
| POST | `/{project_id}/deploy/commit` | Commit (stub) |
| POST | `/{project_id}/deploy/vercel` | Vercel deploy (stub) |
| GET | `/{project_id}/deployments` | Deployment list (stub) |

### Providers (`/api/v1/providers`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List user's API keys (masked) |
| POST | `/` | Create new provider key |
| PUT | `/{id}` | Update provider |
| DELETE | `/{id}` | Delete provider |
| PATCH | `/{id}/default` | Set as default |
| PATCH | `/{id}/toggle` | Toggle active |
| POST | `/{id}/test` | Test API connectivity |
| GET | `/{id}/models` | Fetch available models |

**Supported Providers**: OpenAI, Anthropic, Google AI, OpenRouter, Ollama, LM Studio, Cohere, HuggingFace

### Model Routing (`/api/v1/model-routing`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all task routings |
| PUT | `/{task_type}` | Set/update routing |
| DELETE | `/{task_type}` | Clear routing (revert to default) |

**Task Types**: code_gen, csuite, design, ideation, artifacts

### Models (`/api/v1/models`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all available models across providers |

### Billing (`/api/v1/billing`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/subscription` | Current tier + usage + period |
| POST | `/checkout` | Create Stripe Checkout session |
| POST | `/pack/checkout` | Create Checkout for usage pack |

### Export (`/api/v1/projects`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{project_id}/export/{filename}` | Download artifact(s) as MD/DOCX/PDF |

**Filenames**: `csuite.{md|docx|pdf}`, `artifacts.{md|docx|pdf}`, `artifact/{key}.{md|docx|pdf}`

### Health & SSE

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Redis + circuit breaker status |
| GET | `/api/v1/projects/{project_id}/events?token=JWT` | SSE real-time updates |

---

## 7. Background Job System (Inngest)

### Configuration

- Dev server: `npx inngest-cli@latest dev -u http://localhost:8000/api/inngest`
- Toggle: `USE_INNGEST=1` env var
- Production: `INNGEST_PRODUCTION=1` (no local dev server needed)
- Fallback: 20s grace period watchdog — if rows still pending, run locally via BackgroundTasks

### Inngest Events & Functions

| Event | Function | Description |
|-------|----------|-------------|
| `csuite/run.requested` | `csuite_run_fn` | Run all C-Suite agents + generate artifacts |
| `csuite/refine.requested` | `csuite_refine_fn` | Re-run with correction context |
| `csuite/improve.requested` | `csuite_improve_fn` | Self-analyze + improvement plan |
| `csuite/improve.apply.requested` | `csuite_improve_apply_fn` | Re-run with enhanced context |
| `artifacts/generate.requested` | `artifacts_generate_fn` | Generate all artifacts |
| `artifacts/generate-single.requested` | - | Generate single artifact |
| `artifacts/regenerate-all.requested` | - | Reset all artifacts |
| `design/engine-generate.requested` | `design_engine_generate_fn` | Run full design pipeline |
| `forge.project.build.started` | `build_pipeline_fn` | Multi-step build orchestration |
| `sandbox/provision.requested` | `sandbox_provision_fn` | Create Fly.io sandbox |
| `sandbox/pool-fill` (cron: */10 min) | - | Refill pre-warm pool |
| `chat/message.requested` | - | Classify intent → code or conversation |

### Build Pipeline (`build_pipeline_fn`)

Multi-step orchestration:
1. PRD generation
2. Design system generation
3. Capability gate check
4. Sandbox provisioning
5. Code generation
6. Validation

---

## 8. C-Suite Agent System

### Architecture

9 parallel AI agents evaluate startup ideas:

| Role | Focus Area |
|------|-----------|
| **CEO** | Market viability, competitive moat, exit potential, founder-market fit |
| **CTO** | Technical feasibility, MVP architecture, scalability risks, security |
| **CFO** | Unit economics, CAC/LTV, burn rate, path to profitability |
| **CMO** | ICP definition, TAM/SAM/SOM, channel strategy, launch plan |
| **CPO** | Problem validation, solution clarity, MVP scope, user journey |
| **COO** | Operational processes, compliance, partner dependencies, staffing |
| **CDO** | UX complexity, screen inventory, design system, accessibility |
| **CISO** | Threat modeling, data classification, auth/access control, infra security |
| **Synthesizer** | Cross-functional consensus, go/no-go recommendation, 90-day action plan |

### Execution Flow

1. Create pending `CSuiteAnalysis` rows for each role
2. Set project status to `csuite_pending`
3. Send Inngest event OR run background task
4. **Phase 1**: 8 functional agents run in parallel (max 15 concurrent LLM calls via semaphore)
5. **Phase 2**: Synthesizer runs after all 8 complete (consumes their results)
6. Each agent outputs: score (0-100), verdict (go/conditional/no_go), analysis JSON
7. On completion → auto-generate artifacts → auto-trigger build pipeline

### Concurrency Controls

- `_LLM_SEMAPHORE = asyncio.Semaphore(15)` — max concurrent LLM calls
- `_CANCELLED_PROJECTS: set[str]` — projects marked for abort
- `_CANCELLED_ANALYSES: set[str]` — individual analyses marked for abort
- `_PROJECT_LOCKS: dict[str, asyncio.Lock]` — per-project mutual exclusion
- Per-project locks prevent concurrent runs (409 Conflict on overlap)

### JSON Repair

LLM responses often have truncated JSON. The system:
1. Strips markdown code fences
2. Extracts JSON via bracket-depth tracking
3. Repairs truncated JSON (close open strings, brackets, braces)
4. Falls back to `_build_fallback_result()` with regex score extraction

### DB Write Retry

`_write_analysis_result_with_retry()`:
- Max 3 attempts on transient DB errors (OperationalError, DisconnectionError)
- Fresh `SessionLocal` per attempt to survive stale connections
- 0.2s × attempt backoff

---

## 9. Multi-Agent Code Generation Pipeline

### 4-Stage Pipeline (`agent_pipeline.py`)

```
User Prompt → Intent Agent → Layout Agent → Component Agent → Code Agent
                                                                   ↓
                                                         AST Validation
                                                                   ↓
                                                    Design Contract Enforcement
```

#### Stage 1: Intent Agent
- Input: user prompt + project context
- Output: classified intent + decomposed sub-tasks
- Prompt: `INTENT_AGENT_PROMPT`

#### Stage 2: Layout Agent
- Input: intent + existing pages
- Output: page structure + routing decisions
- Prompt: `LAYOUT_AGENT_PROMPT`

#### Stage 3: Component Agent
- Input: layout + existing components
- Output: component manifest + props schemas
- Prompt: `COMPONENT_AGENT_PROMPT`

#### Stage 4: Code Agent (SURGEON_PROMPT)
- Input: component manifest + design system + full context
- Output: actual file contents (React/TypeScript/Tailwind)
- Prompt: `SURGEON_PROMPT` (1000+ lines of generation rules)
- Applies design contract CSS variables
- Enforces design token consistency

### AST Validation (`patch_engine.py`)

- **tree-sitter** parsers: TypeScript, JavaScript, CSS
- Validates generated code is syntactically correct
- Checks for critical AST errors (broken imports, unclosed tags)
- Returns pass/fail with error details

### Context Compression (`context_compression.py`)

**5-Layer Compression** (97% reduction: 150k LOC → 3-5k tokens):

| Layer | Content | Token Budget |
|-------|---------|-------------|
| 1. Project Summary | Name, description, status | ~500 |
| 2. Architecture Map | Pages, routes, components | ~1000 |
| 3. Dependency Graph | Import relationships | ~500 |
| 4. Relevant Files | Semantic search via embeddings | ~2500 |
| 5. Active Snippets | Current file context | ~500 |

### Auto-Error Resolver (`error_resolver.py`)

4-step auto-fix loop:

1. **AST Scan** (tree-sitter) — precise line/col error identification
2. **Deterministic Rule Fixes** (no LLM) — brace mismatch, missing semicolons, empty exports
3. **Focused File Selection** — only broken files + 1-hop importers
4. **LLM Repair** (`FIX_PROMPT`) — targeted fix with temperature 0.3

**Loop Prevention**:
- Max 3 attempts per cycle
- 10-second cooldown between attempts
- Same error hash = likely unfixable → abort

---

## 10. Design Engine

### Pipeline (`design_engine.py`)

```
Mode Selection → Design Brief → Design System → Persist to Artifacts
```

#### Step 1: Mode Selection

Priority order:
1. Locked mode (user override)
2. Stored mode (previous selection)
3. User-specified mode
4. LLM auto-classify via `MODE_CLASSIFIER_PROMPT`

**Product Modes**: Dashboard, SaaS, Admin, Editor, etc.  
**Style Modes**: Stripe SaaS, Apple, Figma, Linear, etc.

Loaded from `design_mode_engine_pack.json`:
- Product modes (categorized)
- Style modes
- Design type profiles: layout model, density, recommended patterns
- Composition blueprints: default pages, section order, responsive rules

#### Step 2: Design Brief

- Input: project context + mode + style
- LLM call with `DESIGN_BRIEF_PROMPT`
- Output: design intelligence brief JSON including:
  - Color palette recommendations
  - Typography selections
  - Layout patterns
  - Component recommendations
  - Interaction patterns

#### Step 3: Design System

- Input: brief + project context
- LLM call with `DESIGN_ARCHITECT_PROMPT`
- Output: comprehensive design system JSON:
  - Design tokens (colors, typography, spacing, radius)
  - Component specifications
  - Animation definitions
  - Responsive breakpoints

#### Step 4: Persistence

Upserts three artifacts:
- `design_tokens` — CSS variable definitions
- `design_system` — Full system specification
- `design_components` — Component library specs

### Design Intelligence (`design_intelligence.py`)

- Vendor data lookup from 5 CSVs: products, styles, colors, landing, typography
- Fallback rules for 4 categories: Regulated, Healthcare, Fintech, Creative
- `format_design_brief()` — Human-Centered Intelligence Brief
- `format_compiled_design_spec()` — Compiled Design Spec

### Design Context (`design_context.py`)

- Builds design context for code agents
- CDO analysis + design system + contract CSS
- `extract_design_tokens_css()` — Convert tokens → CSS `:root` block
- `build_design_context_for_agent()` — Compact reference for code agents

### Design Contract CSS Priority

1. GPT Engine design tokens (structured)
2. Design System Foundation artifact `:root` block
3. Persisted `design_tokens` artifact (stable reuse)
4. Vendor brief palette → synthetic CSS vars (auto-persisted)

---

## 11. Fly.io Sandbox System

### Architecture

Each project gets an isolated Fly.io Machine running:
- **Vite dev server** (port 5173) — live React app
- **Bridge API** (port 9999) — file management + command execution
- **Nginx** — reverse proxy (port 80/443)

### Sandbox Creation Flow (`fly_service.py`)

```
POST /apps                        → Create Fly app
POST /apps/{name}/machines        → Create machine (2 CPU, 4GB RAM)
POST /apps/{name}/ip_assignments  → Allocate public IP
Poll machine state                → Wait for "started"
Health check via bridge           → DNS + IP override
Wait for Vite + DNS               → Up to 120s
```

**Machine Config**:
- Region: `ord` (Chicago)
- CPU: shared, 2 cores
- Memory: 4GB
- Image: from `kith-sandbox-base` app
- Services: TCP 80 + 443 (TLS via Fly Proxy)
- `auto_stop=off` (keep running)

### Sandbox Reuse Strategy

1. Check in-process cache (`_workers` dict)
2. Check Redis metadata (cross-worker persistence)
3. **Lease from pre-warm pool** (refill via Inngest cron every 10 min)
4. Create new sandbox (3 retries with exponential backoff)

### Pre-Warm Pool (`sandbox_pool.py`)

- Redis-backed pool of idle sandboxes
- Target: 3 warm sandboxes
- Max: 5 machines
- `fill_pool()` runs every 10 minutes via Inngest cron
- Lease/return semantics for reuse
- Machine TTL: 7 days (inactive projects release sandbox)

### Bridge Microservice (`bridge.py`)

Runs inside each Fly.io sandbox machine:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /write_files` | Write files to sandbox filesystem |
| `POST /run_cmd` | Execute shell command |
| `GET /check_vite_errors` | Check Vite build errors |

### Security Policy (`sandbox_policy.py`)

- Blocked packages list
- Blocked file paths
- Suspicious script detection
- Validates all user-provided content before execution

---

## 12. LLM Infrastructure

### Model Resolution (`model_resolver.py`)

Resolution order:
1. Task-specific routing (`ModelRouting` table)
2. User's default provider (`is_default=True`)
3. Any active user provider
4. Server env fallback (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`)

**Provider Prefix Normalization**:
| Provider | litellm Prefix |
|----------|---------------|
| anthropic | `anthropic/` |
| openai | (none) |
| google_ai | `gemini/` |
| lm_studio | `openai/` + api_base |
| ollama | `ollama/` |

### Circuit Breaker (`circuit_breaker.py`)

Per-provider circuit breaker pattern:

```
CLOSED → (5 failures) → OPEN → (60s) → HALF_OPEN → (success) → CLOSED
                                                   → (failure) → OPEN
```

- Failure threshold: 5 consecutive failures
- Open duration: 60 seconds
- Call timeout: 120 seconds
- Provider extracted from model ID: `"anthropic/claude-3-5"` → `"anthropic"`

### Embedding Service (`embedding_service.py`)

- Uses litellm for text embedding generation
- Stores in PostgreSQL via pgvector extension
- Max embedding text: 24,000 chars (~6k tokens)
- Used for semantic search in context compression (Layer 4)

### System Prompts (`prompts.py`)

| Prompt | Purpose |
|--------|---------|
| `SURGEON_PROMPT` | Core code generation (1000+ lines of rules) |
| `ARCHITECT_PROMPT` | File structure planning |
| `ROUTER_PROMPT` | Intent classification (code vs conversation) |
| `CONVERSATIONAL_PROMPT` | Discussion mode |
| `FIX_PROMPT` | Error repair (targeted fixes only) |
| `MODE_CLASSIFIER_PROMPT` | Design mode classification |
| `DESIGN_ARCHITECT_PROMPT` | Design system generation |
| `DESIGN_BRIEF_PROMPT` | Design intelligence summary |
| `INTENT_AGENT_PROMPT` | Intent decomposition |
| `LAYOUT_AGENT_PROMPT` | Page structure planning |
| `COMPONENT_AGENT_PROMPT` | Component manifest generation |

---

## 13. Frontend Architecture

### Entry Point

```tsx
// main.tsx
<BrowserRouter>
  <AuthProvider>
    <App />
  </AuthProvider>
</BrowserRouter>
```

### App Structure (`App.tsx`)

- Lazy-loaded routes with `React.Suspense`
- `ThemeProvider` wrapper
- Protected routes via `ProtectedRoute` component
- Redirects unauthenticated users to `/login`

### Contexts

**AuthContext**:
```tsx
interface AuthContextType {
  user: AuthUser | null;
  session: AuthSession | null;
  loading: boolean;
  signUp(email, password): Promise<{ error: string | null }>;
  signIn(email, password): Promise<{ error: string | null }>;
  signOut(): Promise<void>;
  getAccessToken(): Promise<string | null>;
}
```
- Uses Nhost v4: `nhost.auth.signUpEmailPassword()`, `signInEmailPassword()`
- Restores session from localStorage
- 3s fallback timeout if auth state doesn't fire

**ThemeContext**:
```tsx
interface ThemeContextType {
  theme: "dark" | "light";
  toggleTheme(): void;
  setTheme(mode): void;
}
```
- Persists to localStorage (key: `forge-theme`)
- Default: dark
- Sets `data-theme="light"` on `<html>` for light mode

### API Client Layer (`lib/api/`)

```tsx
async function apiRequest<T>(path: string, token: string, init?: RequestInit): Promise<T>
```

API modules:
- `projectsApi` — list, get, delete
- `ideationApi` — enhance, accept, save, listSaved, deleteSaved, questionnaire
- `csuiteApi` — status, run, refine, stop, stopAgent, improve, applyImprovement
- `artifactsApi` — list
- `capabilitiesApi` — get, set
- `secretsApi` — list, submit, revoke
- `sandboxApi` — status, logs
- `deployApi` — connectGit, commit, deployVercel, list

### Hooks

**Core**:
- `useApiFetch()` — Injects Bearer token, redirects to `/login` on 401
- `useScreenState<S>()` — Generic state machine for multi-stage flows

**Feature State Machines**:
- `useBuildState()` → idle|queued|planning|generating_code|building|repairing|ready_for_preview|failed
- `useCapabilityState()` → idle|editing|submitting|needs_secrets|complete|error
- `useDeployState()` → idle|connecting_git|committing|deploying|deployed|failed
- `useDesignState()` → loading|loaded|refining|regenerating|error
- `useExecutiveState()` → loading|running|loaded|error
- `useIdeationState()` → PromptState, CuratedIdeaState, QuestionnaireState, Top5State, SavedIdeasState
- `useSecretsState()` → idle|collecting|submitting|stored|revoking|error

**Build Workspace**:
- `useFoundry(projectId)` — WebSocket-based live editor, file tree, sandbox status, streaming code gen, preview URL with DNS retry
- `useAutoSave(projectId, files, delayMs)` — Debounced autosave (1.5s default)

---

## 14. Frontend Routing

### Public Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | LandingPage / redirect | Redirects to `/app/projects` if authenticated |
| `/login` | LoginPage | Email/password login |
| `/signup` | SignUpPage | Email/password registration |
| `/pricing` | PricingPage | Subscription tiers |

### Authenticated Routes (`/app`)

Wrapped in `<ProtectedRoute><AppShell /></ProtectedRoute>`

#### Dashboard

| Path | Component |
|------|-----------|
| `/app/projects` | DashboardPage |
| `/app/settings` | SettingsPage |
| `/app/profile` | ProfilePage |
| `/app/billing` | BillingPage |

#### Ideation

| Path | Component |
|------|-----------|
| `/app/ideation` | IdeationLanding |
| `/app/ideation/prompt` | IdeaPromptPage |
| `/app/ideation/discover` | DiscoverIdeaPage |
| `/app/ideation/saved` | SavedIdeasPage |

#### Project Context (`/app/projects/:projectId`)

Under `<ProjectShell>`:

| Path | Component | Pipeline Stage |
|------|-----------|---------------|
| `:projectId/` | ProjectDashboardPage | — |
| `:projectId/prompt` | IdeaPromptPage | ideation |
| `:projectId/ideas` | IdeationLanding | ideation |
| `:projectId/saved-ideas` | SavedIdeasPage | ideation |
| `:projectId/executive` | CSuiteAnalysisPage | executive |
| `:projectId/prd` | PrdArchitecturePage | prd |
| `:projectId/design` | DesignStudioPage | design |
| `:projectId/capabilities` | CapabilityGatePage | capabilities |
| `:projectId/build` | Workspace | build |
| `:projectId/secrets` | SecretsPage | secrets |
| `:projectId/deploy` | DeploymentPage | deploy |

---

## 15. Frontend Components

### System Components

| Component | Purpose |
|-----------|---------|
| `AppShell` | Three-part layout: SidebarNav + TopCommandBar + Content |
| `SidebarNav` | Fixed left nav with brand, project context, stage rail, nav links |
| `TopCommandBar` | Sticky header with search, "+ New Project", theme toggle, user menu |
| `ProjectShell` | Minimal wrapper with motion entrance animation |
| `ProtectedRoute` | Auth guard component |
| `ExportMenu` | Download artifacts as MD/DOCX/PDF |
| `ProgressRail` | Pipeline stage progress indicator |

**AppShell Brand**: "FORGE_OS v5.0.0-LUX"

**Pipeline Stages** (ProgressRail):
```typescript
PROJECT_STAGES = ['ideation', 'executive', 'prd', 'design', 'capabilities', 'build', 'deploy']
```

**Stage Status Mapping** (`STATUS_TO_STAGE`):
- Maps `ProjectStatus` enum values → pipeline stage index
- Green checkmark = completed, pulse = current, gray = future

### UI Components Library

**Layout & Structure**:
- `Button` — Primary, secondary, ghost, danger, contrast variants + loading
- `Input` / `Textarea` — Form inputs with labels, errors
- `GlassPanel` — Glassmorphism container with blur backdrop
- `Card` — Steel gradient card with hover animation
- `Modal` — Center modal with overlay, Escape-to-close
- `EmptyState` — Icon + title + description + action

**Progress & Status**:
- `ProgressRail` — Multi-stage progress bar
- `StatusPill` — Semantic status badge (idle/running/success/warning/error)
- `ScoreRing` — Circular progress ring (0-100)
- `TelemetryStrip` — System status bar

**Data Display & Feedback**:
- `AgentBadge` — Role badge for C-Suite/engineering agents
- `AnimatedCounter` — Animated number transitions
- `Skeleton` / `SkeletonText` — Loading placeholders
- `Tooltip` — Hover tooltip with configurable position
- `TrustBanner` — Security/info banners

**Forms & Input**:
- `SecureInput` — Password input with visibility toggle, no autocomplete
- `SectionHeader` — Card header with icon, title, subtitle, badge

### Feature Pages

**Ideation**:
- `IdeationLanding` — "I Have an Idea" vs "Discover Ideas" paths + saved ideas quick-view
- `IdeaPromptPage` — User prompts engine, receives 3 enhancements
- `DiscoverIdeaPage` — Curated idea discovery
- `SavedIdeasPage` — List saved ideas with build/delete

**Executive (C-Suite)**:
- `CSuiteAnalysisPage` — Live SSE streaming, 9 role cards (status, score, recommendation, strengths, risks, verdict), "Refine" modal, "Improve" plan generation, export menu

**Design**:
- `DesignStudioPage` — Mode selector modal, product × style classification, auto-detect with confidence, lock override

**Build**:
- `Workspace` — Monaco editor, file tree explorer, live chat (streaming), code patches, sandbox logs, preview iframe, auto-save, WebSocket updates, build stage progress
- `BUILD_STAGES = ["prd", "design", "capability_gate", "secrets", "sandbox", "code_gen", "validation", "complete"]`

**Capabilities**:
- `CapabilityGatePage` — Database/Auth/AI toggles, conditional redirect to secrets

**Secrets**:
- `SecretsPage` — Provider grid (OpenAI, Anthropic, Supabase, Google AI, Custom), SecureInput, encryption banners

**Deploy**:
- `DeploymentPage` — Git connection, commit + push, Vercel deploy, deployment history

---

## 16. Frontend Design System

### Color Palette (Dark Theme — Default)

```css
/* Primary (Ember Orange) */
--sys-primary: #ffb4a2;
--sys-primary-container: #ed6746;

/* Secondary (Cyan Blue) */
--sys-secondary: #86d0f5;
--sys-secondary-container: #01698a;

/* Tertiary (Warm Gray) */
--sys-tertiary: #bcc8d4;

/* Surfaces */
--sys-background: #10131a;
--sys-surface: #1d2026;
--sys-surface-container: #272a31;
```

Light theme: inverted color strategy via `data-theme="light"` on `<html>`.

### CSS Utilities

| Class | Effect |
|-------|--------|
| `.glass-panel` | Blur backdrop (glassmorphism) |
| `.steel-gradient` | Linear gradient |
| `.ghost-border` | Soft border |
| `.ember-glow` | Primary shadow glow |
| `.cinematic-tracking` | Tight letter-spacing (-0.05em) |

### Typography

- Font family: Inter (body, headline, label, sans)
- Sizes: micro (11px), label (12px), caption (13px)

### Radius

```css
--radius-module: 1rem;
--radius-lg: 2rem;
--radius-xl: 3rem;
```

### Motion Presets (`lib/utils/motion.ts`)

| Preset | Description |
|--------|-------------|
| Page transitions | Opacity + Y offset, easing [0.22, 1, 0.36, 1] |
| Card entrance | Spring: stiffness 300, damping 24 |
| Modal | Overlay fade, content scale + slide |
| List item | Stagger children by 0.08s |
| Button hover/tap | Hover: scale 1.02, Tap: scale 0.98 |

---

## 17. Authentication Flow

### Nhost v4 Implementation

**Frontend** (`lib/nhost.ts`):
- `NhostClient` initialized with subdomain + region from env vars
- `nhost.auth.signUpEmailPassword({ email, password })`
- `nhost.auth.signInEmailPassword({ email, password })`
- Session stored in Nhost's session storage
- Cross-tab sync via localStorage events
- Refresh token management with 60s buffer
- 3s fallback timeout if auth state doesn't fire

**Backend** (`auth_nhost.py`):
- JWT validation: HS256 (NHOST_ADMIN_SECRET) + RS256 (JWKS endpoint)
- `get_current_user()` dependency extracts user from Bearer token
- Creates/upserts User record on first authentication
- Falls back to `/userinfo` endpoint if JWT decode fails

### Auth Interface

```tsx
interface AuthClient {
  getSession(): Promise<AuthSession | null>;
  onAuthStateChange(callback): () => void;
  signUp(email, password): Promise<{ error }>;
  signIn(email, password): Promise<{ error }>;
  signOut(): Promise<void>;
  getAccessToken(): Promise<string | null>;
}
```

---

## 18. Real-Time Updates

### Server-Sent Events (SSE)

**URL**: `GET /api/v1/projects/{project_id}/events?token=JWT`

**Mechanism**:
- Client subscribes once per project
- Backend subscribes to Redis pub/sub channel: `kith:project:{project_id}:updates`
- Messages streamed as JSON payloads (type: "build_stage", "csuite_status", etc.)

### WebSocket (Build Workspace)

- Used by `useFoundry()` hook for live code generation streaming
- File tree updates, sandbox status, build progress
- URL: `ws://localhost:8000/ws` (proxied via Vite)

### Redis Pub/Sub (`redis_state.py`)

**Channel Patterns**:
- `kith:project:{project_id}:updates` — General project updates
- `kith:sandbox:{project_id}:*` — Sandbox events
- `kith:fix:{project_id}:state` — Error fix state

---

## 19. Billing & Usage Limits

### Tier Limits

| Plan | Projects | C-Suite/mo | Design/mo | Artifacts/mo | Price |
|------|----------|-----------|----------|--------------|-------|
| Free | 1 | 50 | 5 | 50 | $0 |
| Indie | 5 | 20 | 30 | 3 sets | $39/mo |
| Pro | ∞ | 100 | 150 | ∞ | $89/mo |
| Team | ∞ | 100×seats | 150×seats | ∞ | $249/mo |
| Enterprise | ∞ | ∞ | ∞ | ∞ | Custom |

### Add-On Packs

- C-Suite runs: 25 for $9
- Design screens: 50 for $9

### Enforcement Functions

- `enforce_csuite_limit(db, user)` — 402 if over monthly quota
- `enforce_design_screen_limit(db, user)` — 402 if over monthly quota
- `enforce_artifact_limit(db, user)` — 402 if free tier without BYOK
- `enforce_project_limit(db, user)` — 402 if at project cap

### Usage Recording

- `record_csuite_run(db, user_id)` — Increment monthly counter
- `record_design_screen(db, user_id, count?)` — Increment counter
- `record_artifact_set(db, user_id)` — Increment counter
- `record_project_created(db, user_id)` — Increment counter

### Stripe Integration

- Checkout Sessions for subscriptions and packs
- BYOK discount (20% off with own API keys)
- Annual billing discount (20% off)

---

## 20. Export System

### Supported Formats

| Format | Library | Notes |
|--------|---------|-------|
| Markdown (.md) | Built-in | Section headers, bullet lists, tables |
| Word (.docx) | python-docx | Title block, headings, shaded table rows |
| PDF (.pdf) | fpdf2 | Header/footer, Arial/Helvetica, shaded rows |

### Export Types

| Filename Pattern | Content |
|-----------------|---------|
| `csuite.{md\|docx\|pdf}` | C-Suite analysis report |
| `artifacts.{md\|docx\|pdf}` | All artifacts bundled |
| `artifact/{key}.{md\|docx\|pdf}` | Single artifact by type key |

### Rendering Functions (`export_service.py`)

- `render_csuite(project_name, analyses, fmt)` → (bytes, media_type, filename)
- `render_artifact(project_name, title, content, fmt)` → (bytes, media_type, filename)
- `render_all_artifacts(project_name, artifacts, fmt)` → (bytes, media_type, filename)

---

## 21. Security & Encryption

### API Key Encryption (`provider_api.py`)

- **Current**: AES-256-GCM (base64url: `"gcm:..."`)
- **Legacy fallback**: Fernet
- Key: `PROVIDER_ENCRYPTION_KEY` (32-byte base64url)
- All provider keys stored encrypted, displayed masked to user

### User Secret Encryption (`secrets_api.py`)

- Fernet encryption for user-provided secrets
- Key: `SECRET_ENCRYPTION_KEY`
- Audit trail: `SecretAccessAudit` records (created/revoked)
- Secrets have `revoked_at` field (null = active)

### Sandbox Security (`sandbox_policy.py`)

- Blocked packages list
- Blocked file paths
- Suspicious script detection
- Content validation before execution

### Rate Limiting

- Global: 30/minute on LLM endpoints (via slowapi)
- Default: 300/minute per user
- 429 status on excess

### HTTP Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request |
| 401 | Unauthorized (JWT invalid/missing) |
| 402 | Payment required (billing limit) |
| 404 | Not found |
| 409 | Conflict (CSuite already running) |
| 422 | Unprocessable entity |
| 500 | Server error |
| 503 | Service unavailable |

---

## 22. Deployment Configuration

### Backend Dockerfile

```dockerfile
# Python 3.13 slim + gunicorn
FROM python:3.13-slim
# Install system deps (build-essential, etc.)
# Copy requirements.txt, install Python deps
# Copy backend code
# Expose port 8000
# CMD: gunicorn with uvicorn workers
```

### Gunicorn Config (`gunicorn_config.py`)

- Workers: 4 (default)
- Timeout: 300s
- Preload app: True

### Sandbox Dockerfile (`Dockerfile.sandbox`)

- Node.js + Python base
- Installs Vite, React, Tailwind
- Copies bridge.py + start.sh
- Runs nginx + bridge + vite

### Sandbox Startup (`start.sh`)

```bash
# Start Vite dev server (port 5173)
# Start Bridge API (port 9999)
# Start Nginx reverse proxy (port 80)
```

### Fly.io Config (`fly.toml`)

```toml
app = "kith-sandbox-base"
primary_region = "ord"

[http_service]
  internal_port = 80
  force_https = true
  auto_stop_machines = false

[[vm]]
  cpu_kind = "shared"
  cpus = 2
  memory_mb = 4096
```

---

## 23. End-to-End User Flow

### Complete Pipeline

```
1. SIGN UP / LOG IN
   └─ Nhost email/password auth
   └─ JWT token issued
   └─ User record created/upserted in DB

2. IDEATION (Stage 1)
   ├─ Path A: "I Have an Idea" → Prompt → 3 AI enhancements → Accept one
   ├─ Path B: "Discover Ideas" → Unique AI-generated idea → Accept
   └─ Path C: Questionnaire → 15 questions → 3 personalized ideas → Accept
   └─ Result: Project created with Idea record

3. EXECUTIVE ANALYSIS (Stage 2)
   └─ 9 C-Suite agents run in parallel
   └─ Live SSE streaming of results
   └─ Each agent: score 0-100, verdict, analysis
   └─ Synthesizer: cross-functional consensus
   └─ Optional: Refine with corrections, Improve with AI suggestions
   └─ Auto-generates 12+ artifacts on completion

4. PRD & ARCHITECTURE (Stage 3)
   └─ View generated PRD artifact
   └─ View tech architecture artifact
   └─ View implementation phases

5. DESIGN STUDIO (Stage 4)
   └─ Product mode × style mode selection (or auto-detect)
   └─ Design brief generation (vendor data + LLM)
   └─ Full design system generation (tokens, components, animations)
   └─ CSS variable contract for code generation

6. CAPABILITY GATE (Stage 5)
   └─ Toggle: Database, Auth, AI capabilities
   └─ If needs external APIs → redirect to Secrets page
   └─ Choices saved to CapabilityChoice record

7. SECRETS (Optional)
   └─ Enter API keys for external services
   └─ AES-256-GCM encrypted storage
   └─ Injected into sandbox environment

8. BUILD (Stage 6)
   ├─ Sandbox provisioned (Fly.io Machine)
   ├─ Multi-agent code generation:
   │   └─ Intent → Layout → Component → Code
   │   └─ AST validation (tree-sitter)
   │   └─ Design contract enforcement (CSS vars)
   ├─ Live preview in iframe
   ├─ Chat with AI assistant for modifications
   ├─ Auto-error resolution (3 attempts with cooldown)
   └─ Auto-save (1.5s debounce)

9. DEPLOY (Stage 7)
   └─ Git connection (stub)
   └─ Commit + push (stub)
   └─ Vercel deploy (stub)
```

### State Transition Flow

```
ideation
  → csuite_pending → csuite_running → csuite_complete
    → prd_generating → prd_complete
      → design_generating → design_complete
        → capability_gate
          → secrets_pending (if needed)
            → building → build_complete
              → deployed
```

### Background Job Orchestration

```
User clicks "Run Analysis"
  → API creates pending CSuiteAnalysis rows
  → Inngest event: csuite/run.requested
  → (fallback: BackgroundTasks with 20s watchdog)
  → 8 agents run in parallel (semaphore: 15)
  → Synthesizer runs after all 8 complete
  → Auto-generate artifacts (12+ types)
  → Auto-trigger build pipeline:
      → PRD generation
      → Design system generation
      → Capability gate check
      → Sandbox provisioning
      → Code generation
      → Validation
```

---

## 24. File Index

### Backend (31+ files)

| File | Purpose |
|------|---------|
| `main.py` | App entry, middleware, WebSocket, SSE |
| `models.py` | SQLAlchemy models, engines, sessions |
| `csuite_agent.py` | 9 C-Suite agent orchestration |
| `csuite_api.py` | C-Suite API + background triggers |
| `agent_pipeline.py` | 4-stage code gen pipeline |
| `agent.py` | Chat handler with streaming JSON |
| `artifacts_api.py` | 12 artifact types generation |
| `design_api.py` | Design mode + engine endpoints |
| `design_engine.py` | GPT Design Engine pipeline |
| `design_mode_service.py` | Mode classification from pack.json |
| `design_context.py` | Design context builder |
| `design_intelligence.py` | Vendor lookup + brief gen |
| `fly_service.py` | Fly.io sandbox worker |
| `sandbox_pool.py` | Pre-warm pool management |
| `sandbox_policy.py` | Security policy validation |
| `bridge.py` | Sandbox microservice |
| `brain_service.py` | Project brain/knowledge base |
| `error_resolver.py` | Auto error resolver |
| `patch_engine.py` | tree-sitter AST validation |
| `context_compression.py` | 5-layer compression |
| `model_resolver.py` | Model routing/resolution |
| `circuit_breaker.py` | Per-provider circuit breaker |
| `embedding_service.py` | Text embedding + pgvector |
| `prompts.py` | All system prompts |
| `ideation_prompts.py` | Questionnaire + idea prompts |
| `auth_nhost.py` | Nhost JWT validation |
| `auth.py` | Auth dispatcher |
| `storage_service.py` | File storage abstraction |
| `storage_nhost.py` | Nhost storage implementation |
| `export_api.py` | Export endpoints |
| `export_service.py` | MD/DOCX/PDF rendering |
| `billing_api.py` | Stripe + usage limits |
| `projects_api.py` | Project CRUD |
| `ideation_api.py` | Idea management |
| `capabilities_api.py` | Capability selection |
| `secrets_api.py` | Encrypted secret storage |
| `sandbox_api.py` | Sandbox status endpoints |
| `deploy_api.py` | Deploy stubs |
| `provider_api.py` | API key management |
| `routing_api.py` | Model routing config |
| `models_api.py` | Model discovery |
| `redis_client.py` | Redis singletons |
| `redis_state.py` | Redis pub/sub + state |
| `inngest_client.py` | Inngest client singleton |
| `inngest_functions.py` | Inngest function definitions |
| `rate_limiter.py` | slowapi config |
| `Dockerfile` | Production backend image |
| `Dockerfile.sandbox` | Sandbox image |
| `fly.toml` | Fly.io deployment config |
| `fly-backend.toml` | Backend Fly config |
| `gunicorn_config.py` | Gunicorn settings |
| `start.sh` | Sandbox startup script |
| `nginx.conf` | Sandbox nginx config |
| `requirements.txt` | Python dependencies |
| `alembic.ini` | Migration config |

### Frontend Key Files

| File | Purpose |
|------|---------|
| `src/main.tsx` | App entry, provider setup |
| `src/App.tsx` | Route definitions, theme wrapper |
| `src/index.css` | Design system CSS variables |
| `src/contexts/AuthContext.tsx` | Auth state + Nhost |
| `src/contexts/ThemeContext.tsx` | Dark/light theme |
| `src/lib/auth.ts` | Auth client interface |
| `src/lib/nhost.ts` | Nhost v4 implementation |
| `src/lib/runtimeConfig.ts` | API/WS URL resolution |
| `src/lib/api/client.ts` | API request helper |
| `src/lib/utils/cn.ts` | clsx + tailwind-merge |
| `src/lib/utils/motion.ts` | Framer Motion presets |
| `src/components/system/AppShell.tsx` | Main layout + sidebar + progress rail |
| `src/components/system/ProjectShell.tsx` | Project wrapper |
| `src/components/system/ProtectedRoute.tsx` | Auth guard |
| `src/components/ui/Button.tsx` | Button variants |
| `src/components/ui/ProgressRail.tsx` | Pipeline progress |
| `src/components/ui/StatusPill.tsx` | Status badges |
| `src/components/ui/ScoreRing.tsx` | Circular score display |
| `src/components/ui/GlassPanel.tsx` | Glassmorphism container |
| `src/components/ui/Modal.tsx` | Modal dialog |
| `src/features/ideation/*.tsx` | Ideation feature pages |
| `src/features/executive/*.tsx` | C-Suite analysis pages |
| `src/features/design/*.tsx` | Design studio pages |
| `src/features/build/Workspace.tsx` | Build workspace |
| `src/features/capabilities/*.tsx` | Capability gate |
| `src/features/secrets/*.tsx` | Secrets management |
| `src/features/deploy/*.tsx` | Deployment pages |
| `src/features/dashboard/*.tsx` | Dashboard pages |
| `src/features/settings/*.tsx` | Settings pages |
| `src/types/*.ts` | TypeScript type definitions |
| `src/hooks/*.ts` | Custom React hooks |
| `vite.config.ts` | Vite build config |
| `tsconfig.json` | TypeScript config |
| `package.json` | Dependencies |

### Configuration Files

| File | Purpose |
|------|---------|
| `design_mode_engine_pack.json` | Design mode definitions |
| `design_mode_engine_pack.yaml` | Design mode definitions (YAML) |
| `inngest.json` | Inngest configuration |
| `backend/.env` | Backend environment variables |
| `frontend/.env` | Frontend environment variables |

---

## Critical Configuration Values

### Timeouts
| Setting | Value |
|---------|-------|
| Circuit breaker call | 120s |
| Auto-fix cooldown | 10s |
| Auto-fix max attempts | 3 |
| Sandbox creation | ~120s |
| Gunicorn timeout | 300s |

### Limits
| Setting | Value |
|---------|-------|
| Max concurrent LLM calls | 15 (semaphore) |
| Max embedding text | 24,000 chars |
| Max C-Suite output | 8,000 tokens |
| Rate limit default | 300/min per user |
| Design context truncate | 12,000 chars |
| Compression target | 5,000 tokens |

### Ports
| Service | Port |
|---------|------|
| Backend (uvicorn) | 8000 |
| Frontend (Vite) | 5173 |
| Inngest Dev | 8288 |
| Redis | 6379 |
| Bridge (sandbox) | 9999 |
| Nginx (sandbox) | 80/443 |
