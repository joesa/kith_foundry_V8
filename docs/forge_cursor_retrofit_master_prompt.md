# Forge — Cursor Retrofit Master Prompt
## Complete detailed implementation prompt to retrofit the current system with all new requirements

Use this prompt in Cursor against the **existing Forge codebase**.  
This is **not** a greenfield prompt. This is a **retrofit / migration / hardening prompt**.

Your job is to inspect the current implementation, identify every place where the new requirements are missing or incomplete, and retrofit the system so the final result matches the full architecture and product behavior already defined.

You must act like a principal full-stack architect, platform engineer, product systems engineer, security engineer, and frontend integration lead working together.

Do not omit any requirement.
Do not silently simplify any requirement.
Do not leave partially-wired placeholder flows.
Do not add generic “coming soon” surfaces.
Do not create fake UI that is not backed by real state and real API contracts.

---

# 1. PRIMARY OBJECTIVE

Retrofit the current Forge system so it fully supports the following, end to end:

1. typed user idea → send AS-IS into autonomous C-Suite
2. prompt enhancement before C-Suite
3. Top #1 curated idea shown first with no questionnaire
4. rejection of Top #1 idea triggers questionnaire flow
5. questionnaire leads to 5 curated ideas
6. saving ideas with a hard 7-day soft-hold timer
7. uniqueness degradation warning after 7 days
8. specialist multi-agent C-Suite collaboration visible in UI
9. downstream planning/design/engineering/runtime/deployment agent collaboration visible in UI
10. capability gate before build:
   - DB?
   - Auth?
   - AI?
11. explicit generated-app backend guidance:
   - Supabase Database
   - Supabase Storage
   - Supabase Auth
12. support for external cloud integrations:
   - Cloudflare
   - AWS
   - GCP
   - other managed services
   provided they are not installed locally inside sandbox
13. secure secret collection UI
14. AES-256-GCM encrypted persisted secrets
15. no raw API keys in browser localStorage
16. backend proxy and/or ephemeral runtime secret injection patterns
17. build-contract-driven code generation
18. static validation before sandbox build
19. smoke tests after build
20. self-healing repair loop
21. AST-safe patching and guarded edit flow
22. build readiness and deployment readiness gating
23. fully observable stage/status model
24. frontend and backend aligned 1:1
25. industrial cinematic design system applied consistently
26. no architectural drift from the existing Forge system blueprint

---

# 2. IMPORTANT OPERATING MODE

This is a retrofit of an existing system.

You must:

- inspect the existing repository structure first
- map current implementation against required architecture
- identify gaps, mismatches, and regressions
- preserve anything already correct
- replace only what is wrong, missing, or inconsistent
- minimize destructive rewrites where safe
- use patch-oriented editing where possible
- keep the system buildable at every major phase

Do not restart the app from scratch unless a subsystem is irreparably misaligned.
Prefer **incremental architectural correction**.

---

# 3. SOURCE OF TRUTH HIERARCHY

Treat the following as the source of truth, in this order:

1. Forge system blueprint and collaborative multi-agent architecture
2. execution-contract pack
3. end-to-end user flow
4. autonomous build reliability requirements
5. secret management and capability gate requirements
6. design system and token set
7. existing codebase, only where it already matches the above

If the existing code conflicts with the architecture/spec, the architecture/spec wins.

---

# 4. RETROFIT GOALS BY SUBSYSTEM

## 4.1 Product entry and ideation subsystem

Retrofit the product entry flow so it supports all of these paths:

### Path A — User types their own idea
User enters a prompt/idea.
User can:
- send AS-IS to C-Suite
- enhance first
- save as draft

### Path B — User sees Top #1 curated idea first
No questionnaire required first.
The system shows one curated idea with:
- title
- concept summary
- target customer
- problem solved
- monetization
- market analysis
- financial analysis
- monthly/annual scenario-based revenue
- urgency framing
- image/presentation asset
- proceed / save / reject actions

### Path C — Questionnaire only after rejection
If user rejects the Top #1 idea:
- launch ideation questionnaire
- persist answers
- run C-Suite collaborative ideation logic
- show 5 curated ideas with rich presentation

### Saved idea rules
Retrofit saved ideas so:
- saved_only ideas get a hard 7-day soft-hold
- after 7 days uniqueness may degrade
- if user launches after 7 days, show warning
- ideas in active product/build states become reserved

You must ensure database, API, job logic, and UI are all aligned on this rule.

---

## 4.2 C-Suite subsystem

Retrofit the system so the C-Suite is not presented as a single blended AI blob.

The UI and backend artifacts must clearly reflect separate specialist agents:
- CEO
- CPO
- CTO
- CDO
- CFO
- CMO
- COO
- CISO
- Executive Synthesizer

You must ensure:
- each agent has a distinct role description
- each agent produces independent analysis
- synthesis merges them after specialist reasoning
- executive review UI shows each agent distinctly
- downstream planning consumes the synthesized result, not fragmented ad hoc text

The user must feel multiple experts are working in concert.

---

## 4.3 Planning subsystem

Retrofit the planning flow so every project can produce:
- PRD artifact
- architecture artifact
- implementation phases
- DB/Auth/Storage recommendation
- feature sequencing
- constraints list

Planning outputs must be versioned and retrievable through real APIs and real frontend states.

---

## 4.4 Design subsystem

Retrofit the design studio so it is not just decorative.

It must:
- consume planning artifacts
- show design mode and style mode
- expose page architecture
- show design previews / HTML previews
- show component recommendations
- show design tokens
- allow refinement/regeneration

The design system must use the existing extracted tokens:
- canvas `#090C12`
- panel `#101721`
- primary `#F2F7FB`
- secondary `#C4D0DC`
- ember `#E86443`
- cyan `#8FD9FF`
- glass and subtle overlays
- Inter typography
- hero/module radii
- industrial glass / steel / telemetry language

Retrofit any conflicting generic SaaS styling.

---

## 4.5 Capability gate subsystem

Before any autonomous build starts, the system must ask:

- Do you want database in the generated app?
- Do you want auth in the generated app?
- Do you want AI in the generated app?

The user must be allowed to:
- choose any combination
- skip everything and continue

If DB/Auth is selected:
- clearly explain that current managed generated-app support is Supabase Database / Storage / Auth

If external cloud services are needed:
- explain Cloudflare / AWS / GCP / other managed integrations are allowed
- explicitly state they must not be installed locally in sandbox
- allow AI assistant-guided integration

Retrofit:
- frontend UI
- backend persistence
- decision logic
- downstream build-contract logic

---

## 4.6 Secret management subsystem

Retrofit secure credential handling end to end.

Requirements:
- secure secret intake UI
- no raw secret collection in ordinary chat where secure intake UI exists
- persisted secrets encrypted with AES-256-GCM
- no raw secrets in logs
- no raw secrets in browser localStorage
- no plaintext secrets committed into project files
- audit trail for create/read_for_runtime/rotate/revoke
- backend-controlled runtime decryption only
- ephemeral runtime injection and/or backend proxy patterns

If generated app needs AI but does not need DB/Auth:
- still use platform secret vault
- still avoid localStorage
- prefer backend proxy or runtime injection

Retrofit:
- DB schema
- API contracts
- crypto utility layer
- backend service boundaries
- frontend trust messaging
- runtime injection flow

---

## 4.7 Code generation subsystem

Retrofit code generation so it is driven by a **Build Contract** artifact, not loose freeform prompting.

Build Contract must include:
- app summary
- route map
- component inventory
- backend requirements
- auth requirement
- AI requirement
- external cloud integration requirement
- required secrets
- disallowed infra
- design tokens/style rules
- acceptance test checklist

Retrofit generator logic so it:
- uses approved templates where possible
- respects capability choices
- respects sandbox restrictions
- emits buildable code with fewer hidden assumptions

---

## 4.8 Validation subsystem

Retrofit pre-build validation so it checks:
- route completeness
- file completeness
- import resolution
- type safety
- dependency policy
- environment variable references
- banned package and banned infra detection
- secret requirement completeness

Retrofit post-build smoke tests so preview is not marked ready unless the app is minimally functional.

Smoke tests must be derived from project/build contract:
- homepage or root route loads
- main routes render
- auth page exists if auth enabled
- DB initialization exists if DB enabled
- AI routes/components exist if AI enabled
- critical components mount
- runtime does not fatal-crash

---

## 4.9 Sandbox subsystem

Retrofit the NorthFlank sandbox flow so it enforces:
- no heavy backend installs
- no forbidden daemons
- no unsafe infra
- runtime secret injection only through approved paths
- build/install/start lifecycle visibility
- logs visibility
- repair loop compatibility

Disallowed local sandbox installs include:
- MySQL
- MariaDB
- MongoDB server
- Redis server
- Elasticsearch
- RabbitMQ
- Kafka
- self-hosted Postgres
- arbitrary privileged daemons

Retrofit enforcement both:
- before build
- during validation
- during sandbox runtime checks

---

## 4.10 Repair and patch safety subsystem

Retrofit safe editing and repair logic so all edits use guarded flow:

1. intent classification
2. target scope resolution
3. AST parsing
4. safe edit boundary detection
5. minimal diff patch generation
6. validation
7. sandbox verification
8. apply or rollback

Protected areas:
- auth wiring
- router setup
- env config
- DB clients
- deployment config
- sandbox policy config
- secret handling codepaths

Retrofit patch previews, approval paths for risky edits, and rebuild triggering.

---

## 4.11 Monaco build workspace subsystem

Retrofit the build workspace so it is a real cockpit, not just an editor.

Must include:
- Monaco
- file tree
- conversational AI
- patch preview area
- sandbox logs
- preview surface
- orchestration/build status
- artifact awareness

The editor AI must be framed as a front door into specialist subsystems:
- design agents
- code agents
- repair agents
- sandbox agents
- deployment agents
- planning agents

The user should see messages like:
- routing to design-edit + patch-safety agents
- patch validated
- sandbox rebuilt successfully

---

## 4.12 Deployment subsystem

Retrofit deployment surfaces and backend flows for:
- git connect
- branch/commit/push
- Vercel deploy
- deployment status
- logs/history

No deployment should proceed unless deployment-readiness checks pass:
- preview is running
- smoke tests passed
- required secrets present
- no unresolved policy violations
- build state is valid

---

## 4.13 Reliability and observability subsystem

Retrofit the system for resilience and visibility using:
- Upstash Redis
- Inngest
- OpenTelemetry
- Sentry

Must support:
- request dedupe
- distributed locks
- stage caching where appropriate
- resumable workflows
- retries
- timed idea expiry jobs
- secret rotation/revocation jobs
- repair jobs
- observable build/deploy flows

The UI must expose meaningful state, not generic spinners.

---

# 5. EXACT FRONTEND REQUIREMENTS TO RETROFIT

You must retrofit or implement the following screens/routes if missing or incomplete:

- `/`
- `/app`
- `/app/projects`
- `/app/projects/:projectId`
- `/app/projects/:projectId/prompt`
- `/app/projects/:projectId/ideas`
- `/app/projects/:projectId/saved-ideas`
- `/app/projects/:projectId/executive`
- `/app/projects/:projectId/prd`
- `/app/projects/:projectId/design`
- `/app/projects/:projectId/capabilities`
- `/app/projects/:projectId/secrets`
- `/app/projects/:projectId/build`
- `/app/projects/:projectId/deploy`
- `/app/settings`

Each route must have real loading, loaded, empty, error, and transition states where appropriate.

Retrofit state machines for:
- prompt workspace
- top idea
- questionnaire
- top 5 ideas
- saved ideas
- executive review
- PRD/architecture
- design studio
- capability gate
- secret intake
- build workspace
- deployment

---

# 6. EXACT BACKEND REQUIREMENTS TO RETROFIT

You must retrofit or implement APIs and services for:

- prompt submission
- daily top idea
- idea action accept/save/reject
- questionnaire fetch/submit
- curated idea batch fetch
- saved idea listing/start/archive
- executive reports
- PRD fetch
- architecture fetch
- design artifact fetch/refine
- capability choices get/set
- secret intake and secret persistence
- project build start
- job status
- sandbox status/logs
- editor chat
- patch fetch/apply
- git connect/commit
- Vercel deploy

All must use typed request/response contracts.
All must have authorization checks.
All must return consistent error shapes.

---

# 7. DATABASE RETROFIT REQUIREMENTS

Retrofit schema to ensure the system has all necessary entities for:

- workspaces
- membership
- projects
- prompts
- ideas
- idea batches
- questionnaire runs
- saved idea events
- idea warnings
- idea expiry events
- executive reports
- PRDs
- architecture plans
- design artifacts
- capability choices
- generated app AI providers
- encrypted secrets
- secret audit
- secret runtime injections
- sandboxes
- sandbox builds
- sandbox logs
- patches
- patch validations
- deployments

If tables exist but are incomplete, extend them safely through migrations.
Do not break existing data without a deliberate migration strategy.

---

# 8. REQUIRED USER-FACING TRUST MESSAGING

Retrofit the product so users clearly understand:

- the system uses specialist agents working together
- builds are validated before preview
- secrets are encrypted with AES-256-GCM where applicable
- raw API keys are not stored in browser localStorage
- unsupported heavy backend systems are blocked
- generated-app backend support currently includes Supabase
- external cloud-managed services can be integrated through AI guidance
- saved ideas are only soft-held for 7 days unless launched

This trust messaging must appear in the right surfaces:
- onboarding
- prompt workspace
- executive review
- capability gate
- secret intake
- build workspace
- deployment workspace

---

# 9. DO NOT MISS THESE EDGE CASES

You must explicitly handle:

1. user accepts top curated idea immediately
2. user saves top curated idea and comes back within 7 days
3. user saves top curated idea and comes back after 7 days
4. user rejects top curated idea and completes questionnaire
5. user rejects top curated idea and abandons questionnaire midway
6. user selects AI but no DB/Auth
7. user selects DB/Auth but no AI
8. user selects external cloud integrations only
9. user skips all capability choices
10. build blocked because required secrets missing
11. build blocked because user requested prohibited local backend infra
12. patch edit attempts to touch protected auth/secret areas
13. sandbox build succeeds but smoke tests fail
14. deploy requested before preview readiness
15. old secrets rotated/revoked and runtime injection must stop using them

---

# 10. REQUIRED IMPLEMENTATION STRATEGY

You must execute the retrofit in phases and keep the system working as you go.

## Phase 1 — Audit and gap map
- inspect existing repo
- document what already exists
- compare against requirements
- create a gap list by subsystem

## Phase 2 — Data and contract correction
- retrofit DB schema/migrations
- retrofit API contracts
- retrofit typed frontend/backed models

## Phase 3 — Ideation and executive pipeline correction
- top idea
- questionnaire
- top 5 ideas
- saved idea timer rules
- C-Suite visibility

## Phase 4 — Planning and design correction
- PRD
- architecture
- design studio
- artifact retrieval/versioning

## Phase 5 — Capability gate and secrets correction
- capability UI
- capability persistence
- secret vault
- secure intake
- trust messaging

## Phase 6 — Build/reliability correction
- build contract
- static validation
- smoke tests
- sandbox rules
- repair loop

## Phase 7 — Editor/deploy correction
- Monaco workspace
- specialist-routed AI chat
- patch preview / guarded patching
- git / deploy

## Phase 8 — Polish, observability, and final hardening
- stage visibility
- error states
- retries
- logging
- Sentry / telemetry
- final regression pass

---

# 11. REQUIRED ACCEPTANCE CRITERIA

The retrofit is not complete unless all of the following are true:

## A. Idea flow
- typed user idea works AS-IS into C-Suite
- prompt enhancement works
- top curated idea appears first
- rejection leads to questionnaire
- questionnaire produces 5 curated ideas
- save/proceed behaviors work
- 7-day expiry logic works
- uniqueness warning works

## B. Executive flow
- all C-Suite agents visible separately
- Executive Synthesizer visible
- synthesis is real artifact, not fake UI copy

## C. Capability gate
- DB/Auth/AI questions appear before build
- Supabase guidance appears correctly
- external cloud service guidance appears correctly
- skip path works

## D. Secrets
- secure intake UI works
- persisted secrets use AES-256-GCM storage model
- no raw localStorage key storage
- audit trail exists
- runtime injection/proxy path exists

## E. Build
- build contract exists
- codegen respects build contract
- static validation exists
- sandbox enforcement exists
- smoke tests exist
- repair loop exists

## F. Editor
- editor chat routes to specialist systems
- patch preview exists
- risky patch approval exists where needed
- AST-safe guarded edit flow exists

## G. Deployment
- git flow works
- deploy flow works
- deploy-readiness gating exists

## H. Design system
- industrial cinematic design system applied consistently
- no major generic SaaS drift remains

## I. Observability
- stage statuses visible
- logs visible
- failure states meaningful
- retry/resume behavior implemented where required

---

# 12. OUTPUT EXPECTATION FROM CURSOR

You must not respond with only analysis.

You must:
- inspect current code
- retrofit the repository
- add or modify files
- create migrations
- wire frontend and backend
- remove or correct conflicting legacy behavior
- produce a working implementation aligned to all requirements

If something in the existing code conflicts with these requirements, correct it.

Do not leave TODOs for core behavior.
Do not leave fake mock data as final system behavior.
Do not leave placeholder pages in critical flows.
Do not skip difficult wiring.

Build the actual retrofit completely and carefully so not a single required behavior/detail is missed.