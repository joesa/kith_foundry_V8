# Kith Foundry — Scale, Capacity & Revenue Analysis
**Date:** March 12, 2026  
**Prepared by:** GitHub Copilot (Claude Sonnet 4.6)

---

## Q1: Is the current state of the application able to support and scale to 1M customers per day?

**No — not even close.** Here's the honest breakdown:

### Scale Assessment: 1M Customers/Day

1M customers/day ≈ **12 req/sec average**, easily **120–600 req/sec at peak** (assuming 10:1 peak ratio and multiple API calls per session).

---

### Hard Blockers

| Issue | Current State | What 1M/day Needs |
|---|---|---|
| **Single process** | One uvicorn process, no multi-worker config | Horizontally scaled workers behind a load balancer |
| **DB connection pool** | Default: `pool_size=5`, `max_overflow=10` → max 15 DB connections | Minimum `pool_size=20`, `max_overflow=40` + PgBouncer in front of Postgres |
| **No caching** | Every request hits Postgres cold | Redis for hot-path queries (project lists, user lookups) |
| **No rate limiting** | Zero middleware protecting LLM-calling endpoints | Per-user/IP rate limits, especially on `/csuite`, `/design`, `/artifacts` |
| **In-memory global state** | `_workers`, `_fix_state`, `_cancelled_mockups` all in-process | Must move to Redis — loses all state on any restart, incompatible with multiple instances |
| **Fly sandbox cold start** | Up to 60s for IP allocation (20 retries × 3s) | Pre-warming, pooling strategy, or async hand-off |
| **WebSocket per project** | Single-process tracker, no distributed fanout | Redis pub/sub or a dedicated WS gateway for horizontal scaling |

---

### Compounding Problems at Scale

- **C-Suite = 7 parallel LLM calls per request.** At 1% of daily users triggering this = 10,000 C-Suite runs/day = 70,000 LLM calls just for that feature. LLM providers will rate-limit you, and costs spike fast.
- **`retries=0` on all Inngest jobs.** At scale, transient failures become frequent. Silent data loss at 1M users is catastrophic.
- **`PROVIDER_ENCRYPTION_KEY` not set = random key per boot.** Every restart invalidates all stored API keys for all users. Completely blocks operation after any deployment.
- **`BRIDGE_SECRET` not set = random per boot.** Every backend restart disconnects all live sandbox sessions.
- **No CDN** — static frontend assets served without a CDN at 1M users will saturate egress.
- **Nhost Postgres** — the hosted Nhost plan imposes strict connection limits; the default SQLAlchemy pool will hit ceiling immediately under any real concurrency.

---

### What's Actually Production-Ready Today

- Auth JWT decode (fast path via `python-jose`) ✓
- LiteLLM abstraction layer (provider-agnostic) ✓
- Alembic migrations ✓
- Per-user API key encryption (once `PROVIDER_ENCRYPTION_KEY` is stable) ✓
- File storage retry logic with exponential backoff ✓

---

### What Must Change Before 1M/day Is Viable

1. **Deploy multiple uvicorn workers** (`--workers 4+` or Gunicorn + uvicorn workers) behind nginx/Caddy.
2. **Add PgBouncer** (transaction pooling mode) in front of Postgres + set `pool_size=20, max_overflow=40, pool_recycle=300` on the engine.
3. **Redis** for session state, `_workers`/`_fix_state`/`_cancelled_mockups` globals, and query caching on hot reads.
4. **Set `PROVIDER_ENCRYPTION_KEY` and `BRIDGE_SECRET` as stable secrets** in your deployment environment — this is a pre-production blocker regardless of scale.
5. **Enable Inngest retries** (`retries=3` minimum) on all functions.
6. **Rate limiting middleware** (e.g., `slowapi` or a reverse proxy rule) on LLM-heavy endpoints.
7. **CDN** (Cloudflare, CloudFront) in front of the frontend build.
8. **Fly sandbox pre-warming** — queue-based machine creation instead of blocking the request.
9. **Database read replicas** for project/idea list queries.

Realistically you're looking at **3–5 significant engineering efforts** before the architecture can handle that load, not a config tweak.

---

## Q2: At the current state, how many users can we support per day and how many requests per minute?

### The Three Binding Constraints

**1. Sync SQLAlchemy in `async def` handlers — the worst bottleneck**

Every `db.query(...)` call inside an `async def` route **blocks the asyncio event loop** entirely. While one DB call runs, zero other requests can make progress. This is the architecture in every single route handler.

```python
# Current engine config — no pool_size, max_overflow, or pool_recycle set
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

- Remote Postgres (Nhost) query latency: ~10–50ms avg
- Typical request: 3–5 DB calls = **30–150ms of total event loop blocking**
- Event loop blocking frequency → **~7–30 requests/sec** for DB-touch endpoints in isolation

**2. DB connection pool**

- `pool_size=5` (SQLAlchemy default), `max_overflow=10` → **max 15 simultaneous connections**
- Since the event loop is single-threaded and sync DB calls block it, only 1 connection is exercised at a time anyway

**3. Inngest concurrency ceilings**

All jobs have `retries=0`, and the global concurrency limits are:

| Function | Concurrency Limit |
|---|---|
| `csuite-run` | 5 |
| `csuite-refine` | 5 |
| `design-generate` | 3 |
| `design-generate-all` | 3 |
| `artifacts-generate` | 3 |
| `artifacts-generate-single` | 5 |

---

### Requests Per Minute — By Endpoint Type

| Endpoint type | Avg response time | Est. sustained req/min |
|---|---|---|
| Simple reads (GET /projects, auth check) | 30–80ms (2–3 DB calls) | **750–1,200** |
| Project writes (POST /projects) | 50–150ms (3–5 DB calls) | **400–900** |
| C-Suite `POST /csuite/{id}/run` | 15–60s (LLM async, DB blocking at start/end) | **5–10** (Inngest limit=5) |
| Design generation | 10–30s per mockup | **6–18** (Inngest limit=3–5) |
| Artifacts generation | 10–20s | **6–15** (Inngest limit=3–5) |
| **Overall mixed workload** | — | **~600–900 req/min realistic peak** |

---

### Concurrent Active Users

- **At any instant:** ~15–30 users can have in-flight requests
- **Users with active LLM jobs:** max **11 simultaneous** across all Inngest workers (3 design + 5 csuite + 3 artifacts)
- **Polling/idle users** (just watching a status): ~50–100

---

### Daily Active Users

Assumptions: login + load 2 projects + 1 C-Suite run + 3 design screens + check results = ~20 API calls/session.

| Scenario | Logic | Est. DAU |
|---|---|---|
| **Heavy users** (full LLM workflows) | C-Suite: 5 concurrent × ~3 runs/hr = 15/hr; Design: 3 × ~6 screens/hr → ~33 full workflows/hr × 10hr | **~330 full-workflow users/day** |
| **Realistic mixed** (80% light, 20% heavy) | ~600 req/min steady × 10hr × 60 ÷ 20 req/session | **~3,000–5,000 DAU** before degradation |

---

### Summary Table

| Metric | Current Capacity |
|---|---|
| **Peak requests/min (mixed)** | ~600–900 |
| **Simple reads/min only** | ~1,000–1,200 |
| **Concurrent active users** | 15–30 |
| **Concurrent LLM jobs** | 11 |
| **Sustainable DAU (light)** | ~3,000–5,000 |
| **Sustainable DAU (full workflows)** | **~300–500** |

> **The single biggest quick win:** Swapping to `asyncpg` + `AsyncSession` (async SQLAlchemy) would multiply throughput by **5–10×** with no infrastructure changes.

---

## Q3: What can we ideally charge for this app, and what model is ideal compared to others on the market?

### What Kith Foundry Actually Is

This is not just an app builder. It's a **full-stack startup acceleration platform** — a single loop from zero to working prototype:

```
Idea → Validation → C-Suite Advisory → Brand/UI Design → Live Code → Business Docs
```

Specifically:
- **Ideation Engine** — questionnaire → 3 curated startup ideas with TAM, CAC/LTV, 90-day launch plan, strategic moat
- **C-Suite Simulation** — 7 parallel AI advisors (CEO, CTO, CFO, CMO, CPO, COO, CDO) doing real financial modeling, go-to-market, tech architecture
- **Design Studio** — brand-consistent UI mockup generation with locked design tokens (prevents visual drift)
- **Live Code Sandbox** — React/TypeScript app with live preview, per-project Fly.io VM
- **Artifact Generation** — PRD, Executive Brief, Tech Spec, Design System docs

---

### Competitive Market Landscape

| Product | What it does | Price/mo | Gap vs Kith |
|---|---|---|---|
| **Lovable** | AI app builder (code gen only) | $20–$80 | No ideation, no advisory, no strategy |
| **Bolt.new** | AI app builder | $20 | No ideation, no advisory, no design system |
| **v0 (Vercel)** | UI component generation | $20–$30 | UI only, no business layer |
| **Cursor** | AI code editor | $20 | Code only, IDE-based |
| **Tome** | AI pitch deck / narrative | $16–$25 | No code, no advisory, no design |
| **Beautiful.ai** | Slide/deck generation | $12–$40 | No code, limited advisory |
| **Builder.ai** | Managed app building (human+AI) | $499–$2,000+ | Enterprise, human-assisted, slow |
| **ChatGPT / Claude direct** | General AI | $20 | No product workflow, no live preview |
| **Miro AI** | Whiteboarding + ideation | $8–$20 | No code, no C-Suite simulation |

**No single product combines all five layers** (ideation → advisory → design → code → docs). The closest bundle would be Lovable + v0 + a strategy consultant = **$40–$80/mo + $150–$500/hr consulting.**

---

### Pricing Tier Recommendation

| Tier | Target | Price | Limits |
|---|---|---|---|
| **Free** | Hobbyists, eval | $0 | 1 project, 3 C-Suite runs/mo, 5 design screens, BYOK only |
| **Indie** | Solo founders, freelancers | **$39/mo** | 5 projects, 20 C-Suite runs, 30 design screens, 3 artifact sets |
| **Pro** | Serious founders, product managers | **$89/mo** | Unlimited projects, 100 C-Suite runs, 150 design screens, all artifacts, priority sandbox spin-up |
| **Team** | Startups, agencies (3–10 seats) | **$249/mo** | Everything Pro × team, shared project workspace, team API keys |
| **Enterprise** | Studios, VCs, accelerators | **$999+/mo** | Custom seats, white-label mockups, dedicated sandbox region, SLA |

### Why These Numbers Work

- **$39 Indie** is cheaper than Lovable's $80/mo plan and provides significantly more value (advisors + design + code). It's an easy "yes" for any founder spending $150/hr on a consultant.
- **$89 Pro** competes with Lovable Pro + v0 Pro combined (~$100/mo) while adding the C-Suite layer that has no equivalent in the market.
- **$249 Team** undercuts Builder.ai's entry tier ($499+) massively while still being a high-margin SaaS product.
- **BYOK on free** is a smart acquisition hook — zero LLM cost to you, user still gets hooked on the workflow.

---

### Ideal Business Model

**SaaS subscription + usage ceiling** (not pure token billing — founders hate surprise invoices):

1. **Primary revenue:** Monthly subscription per tier
2. **Expansion revenue:** Extra C-Suite run packs ($9 for 25 runs), extra design screen packs ($9 for 50 screens)
3. **BYOK discount path:** Users who connect their own API keys get 20% off
4. **Annual pre-pay:** 20% discount = strong cash flow + churn reduction

---

### Unit Economics at Current LLM Costs

At ~$0.012/1K tokens (Claude Sonnet) and typical usage:

| Action | LLM Cost |
|---|---|
| C-Suite run (~150K tokens, 7 agents) | ~$0.80–1.50 |
| Design screen | ~$0.15–0.40 |
| Artifact generation | ~$0.20–0.60 |

At Pro tier ($89/mo, BYOK off):
- 100 C-Suite runs × $1.00 avg = ~$100 LLM cost
- At realistic usage (~30–40% of limits): LLM cost per Pro user ≈ **$25–40/mo**
- **Gross margin per Pro user: ~55–72%** before hosting

---

## Q4: What is the ideal monthly net revenue ballpark?

### Scenario 1: Early Stage (~6 months post-launch)

| Tier | Subscribers | MRR |
|---|---|---|
| Indie $39 | 50 | $1,950 |
| Pro $89 | 20 | $1,780 |
| Team $249 | 5 | $1,245 |
| Enterprise $999 | 1 | $999 |
| **Gross MRR** | | **$5,974** |

**Monthly costs at ~30% avg utilization:**

| Cost | Amount |
|---|---|
| LLM (Claude Sonnet, ~30% BYOK offset) | ~$800 |
| Fly.io sandboxes (~75 active projects × $8) | ~$600 |
| Nhost DB + storage | ~$50 |
| Stripe fees (2.9%) | ~$175 |
| Inngest + misc | ~$75 |
| **Total costs** | **~$1,700** |

**Net: ~$4,300/mo (~72% margin)**

---

### Scenario 2: Growth (~18 months)

| Tier | Subscribers | MRR |
|---|---|---|
| Indie $39 | 300 | $11,700 |
| Pro $89 | 150 | $13,350 |
| Team $249 | 40 | $9,960 |
| Enterprise $1,499 avg | 5 | $7,495 |
| **Gross MRR** | | **$42,505** |

**Monthly costs:**

| Cost | Amount |
|---|---|
| LLM (~35% BYOK, ~30% utilization) | ~$6,000 |
| Fly.io (~500 projects × $8) | ~$4,000 |
| Nhost Pro | ~$200 |
| Stripe fees | ~$1,250 |
| Inngest + CDN + monitoring | ~$450 |
| **Total costs** | **~$11,900** |

**Net: ~$30,600/mo (~72% margin) → ~$367K ARR net**

---

### Scenario 3: Scale (~3 years)

| Tier | Subscribers | MRR |
|---|---|---|
| Indie $39 | 1,000 | $39,000 |
| Pro $89 | 500 | $44,500 |
| Team $249 | 150 | $37,350 |
| Enterprise $1,999 avg | 20 | $39,980 |
| Annual prepay uplift | — | +$10,000 |
| **Gross MRR** | | **~$170,830** |

**Monthly costs (~30–35% of gross):**

| Cost | Amount |
|---|---|
| LLM (~40% BYOK, ~25% avg utilization) | ~$18,000 |
| Infrastructure (Fly.io, DB, CDN, monitoring) | ~$18,000 |
| Stripe + payment ops | ~$5,000 |
| Compliance/security tools | ~$2,000 |
| **Total costs** | **~$43,000** |

**Net: ~$127,800/mo (~75% margin) → ~$1.53M ARR net**

---

### Key Levers That Move These Numbers

| Lever | Impact |
|---|---|
| **BYOK adoption hits 50%+** | Saves $3–15K/mo in LLM costs at growth/scale |
| **Annual prepay at 20% discount** | 30% annual conversion = ~20% effective MRR boost, cash upfront |
| **Usage packs add-on** | +$9 packs at 15% attachment rate adds ~$2–8K/mo at growth |
| **Sandbox sleep-on-idle working well** | Active time drops from 8hr to 2–3hr/day → Fly costs cut by 60% |
| **Enterprise tier at $2,500+** | 5 more enterprise logos = +$12,500/mo at near-zero marginal cost |

---

### Net Revenue Milestones Summary

| Stage | Timeline | Subscribers | Net MRR | Net ARR |
|---|---|---|---|---|
| Early | ~6 months | ~76 paying | ~$4,300 | ~$51,600 |
| Growth | ~18 months | ~495 paying | ~$30,600 | ~$367,200 |
| Scale | ~3 years | ~1,670 paying | ~$127,800 | ~$1,533,600 |

> The **$1M net ARR milestone requires ~1,700 paying subscribers** — roughly when you'd need to invest in the async DB refactor and horizontal scaling. Conveniently, $1M ARR also funds exactly that engineering work.

---

*Analysis based on codebase review of Kith Foundry V8 as of March 12, 2026.*
