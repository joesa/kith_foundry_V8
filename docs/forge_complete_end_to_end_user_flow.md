# Forge — Complete End-to-End User Flow
## Production-Ready System Flow Specification

This document defines the complete end-to-end user flow for Forge, from first login through ideation, executive analysis, planning, design, capability selection, secure secret handling, code generation, sandbox build, iterative editing, deployment, and learning feedback.

This file is intended to be production-ready and implementation-ready, with no conceptual retrofitting required.

---

# 1. System purpose

Forge is an AI-powered product creation platform that behaves like a coordinated AI-native company.

It is not a single assistant.
It is a system of specialized collaborative agents working in concert across:

- C-Suite strategy
- idea generation and curation
- product planning
- design intelligence
- engineering intelligence
- build/runtime orchestration
- deployment
- learning and optimization

The user experience must consistently reinforce that the platform is powered by specialized agents, not a generic chatbot.

---

# 2. Core platform stack

## Platform core
- React + Vite
- TailwindCSS
- Python FastAPI
- Nhost PostgreSQL
- Nhost Auth
- Fly.io MicroVM
- Upstash Redis
- Inngest
- OpenTelemetry
- Sentry

## Generated app runtime
Generated applications may optionally use:
- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage

Only when the generated application actually needs DB/Auth/Storage.

The platform core itself must not use Supabase.

## External cloud integrations
Generated apps may also integrate:
- Cloudflare
- AWS
- GCP
- other managed databases
- other auth providers
- other AI providers
- other managed cloud APIs

These are allowed only as external managed cloud integrations.
They must not be installed locally inside the sandbox.

---

# 3. Core product promise to the user

From the moment the user enters the product, Forge should communicate:

- you are working with a coordinated set of expert AI agents
- your product is being evaluated from business, product, architecture, design, cost, go-to-market, execution, and security perspectives
- every major output is reviewed and handed off intentionally
- secrets and credentials are handled securely
- unsupported infrastructure is blocked
- code changes are validated before being applied
- builds happen inside controlled sandboxes
- the system is reliable, observable, and built for scale

This trust framing is not optional. It is part of the product.

---

# 4. Specialized agent model

## 4.1 C-Suite agents
These are independent specialist agents that collaborate before planning begins.

### CEO
Responsible for:
- product vision
- market opportunity
- strategic differentiation
- top-level business direction

### CPO
Responsible for:
- product lifecycle
- prioritization
- roadmap logic
- feature sequencing
- value definition

### CTO
Responsible for:
- architecture direction
- stack fit
- technical feasibility
- scalability
- runtime implications

### CDO
Responsible for:
- design philosophy
- UX direction
- visual quality
- mode and style direction

### CFO
Responsible for:
- cost awareness
- revenue framing
- pricing assumptions
- financial viability

### CMO
Responsible for:
- positioning
- messaging
- urgency framing
- trust and persuasion

### COO
Responsible for:
- implementation sequencing
- operational dependency mapping
- execution order

### CISO
Responsible for:
- security architecture
- secret handling
- sandbox restrictions
- policy enforcement

### Executive Synthesizer
Responsible for:
- merging all executive outputs
- resolving cross-functional conflicts
- producing one aligned executive recommendation

## 4.2 Other agent families

### Idea & curation agents
- daily top idea generation
- guided ideation
- market analysis
- financial analysis
- idea presentation
- exclusivity logic
- saved idea expiry handling

### Planning agents
- PRD generation
- architecture planning
- database planning
- auth planning
- storage planning
- implementation guides

### Design agents
- mode classification
- style direction
- layout composition
- UX architecture
- pattern selection
- component architecture
- design compiler

### Engineering agents
- frontend architecture
- backend architecture
- code generation
- patch generation
- patch validation
- self-healing

### Runtime / sandbox agents
- sandbox provisioning
- sandbox policy enforcement
- build execution
- preview lifecycle
- log streaming

### Deployment agents
- git workflows
- deployment workflows

### Learning agents
- reflection
- feedback capture
- prompt optimization
- pattern ranking
- project-state summarization

---

# 5. End-to-end flow overview

The system supports three primary product-entry paths:

## Path A — User already has an idea
The user types their idea and can:
- send it AS-IS into the autonomous C-Suite
- enhance it first
- save draft context and continue later

## Path B — User uses AI-curated top idea
The user is shown one Top #1 curated idea first, before any questionnaire.

They can:
- accept it
- save it
- reject it

If rejected, the system moves to guided ideation.

## Path C — Guided ideation after rejection
The user answers questionnaire prompts.
The system then produces 5 curated ideas.
The user chooses one to continue.

All successful paths converge into the same autonomous execution pipeline.

---

# 6. First login flow

## 6.1 Authentication
The user logs in using Nhost Auth.

Possible states:
- new user
- returning user
- invited workspace member
- workspace owner

## 6.2 Post-login landing state
After authentication, the system loads:

- user profile
- workspaces
- recent projects
- saved ideas
- daily curated idea state
- provider/model preferences
- current system status indicators

## 6.3 First-run onboarding
If this is the user’s first time:
- show product overview
- explain multi-agent specialist model
- explain how ideas can be typed or generated
- explain that builds are validated in sandbox
- explain that DB/Auth/AI capabilities are selected before build
- explain that secrets are securely collected only when needed

The onboarding should emphasize that Forge behaves like an AI company, not a generic single model.

---

# 7. Main entry workspace

When the user enters the workspace, they should see:

- workspace shell
- system status
- project context
- top curated idea
- prompt entry surface
- saved ideas access
- explanation of start paths

The user should always be able to understand:

- what they can do next
- where they are in the pipeline
- which specialist agents are involved

---

# 8. Path A — User types their own idea

## 8.1 User enters idea
The user types something like:
“Build a compliance dashboard for multi-location healthcare clinics.”

## 8.2 Available actions
The system offers:
- Send AS-IS to C-Suite
- Enhance prompt first
- Save draft

## 8.3 If user chooses “Send AS-IS”
The raw idea becomes the source artifact and moves directly into executive analysis.

## 8.4 If user chooses “Enhance”
The prompt enhancer improves clarity, completeness, and product framing.
The user can then:
- accept enhanced prompt
- edit further
- send to C-Suite

## 8.5 Result
Whether raw or enhanced, the idea enters the same autonomous executive pipeline.

---

# 9. Path B — Top #1 curated idea first

## 9.1 Daily top idea generation
Each user should be shown one Top #1 curated idea first without questionnaires.

This idea must include:
- title
- concept summary
- target customer
- problem solved
- why it could make money
- market opportunity
- scenario-based monthly revenue
- scenario-based annual revenue
- urgency framing
- image/presentation asset

## 9.2 User choices
The user can:
- Accept
- Save
- Reject

## 9.3 If accepted
The idea is launched into the executive pipeline.
Its status becomes:
- `in_csuite`
- exclusivity lock becomes true

## 9.4 If saved
The idea enters Saved Ideas with:
- `status = saved_only`
- `saved_expires_at = now + 7 days`
- soft uniqueness hold starts

## 9.5 If rejected
The user enters guided ideation.

---

# 10. Path C — Guided ideation after rejection

## 10.1 Questionnaire
The system asks structured questions such as:
- industry preference
- B2B vs B2C
- venture-scale vs lifestyle preference
- operator vs builder preference
- pricing appetite
- support tolerance
- domain experience

## 10.2 Questionnaire submission
Answers are stored in `ideation_questionnaire_runs`.

## 10.3 C-Suite collaborative ideation
The questionnaire answers are then processed collaboratively by specialist executive agents.

The system generates 5 curated ideas tailored to the user.

Each idea must include:
- title
- summary
- target customer
- pain point
- monetization model
- market analysis
- financial analysis
- estimated monthly/annual revenue scenarios
- execution difficulty
- image or visual direction

## 10.4 User choices for each curated idea
The user can:
- Proceed
- Save
- Ignore

## 10.5 If the user proceeds
The chosen idea enters the executive pipeline and becomes exclusive.

## 10.6 If the user saves
The chosen idea enters Saved Ideas with the same 7-day soft-hold rules.

---

# 11. Saved ideas system

## 11.1 Saved idea behavior
Saved ideas are not permanently reserved.

Saved-only ideas receive:
- `status = saved_only`
- `saved_expires_at = saved_at + 7 days`

## 11.2 Hard 7-day timeline
If the user does not launch the saved idea into active execution within 7 days:
- uniqueness protection expires
- the idea becomes eligible to be shown to other users
- `uniqueness_degraded = true`
- the system may classify it as resurfaced later

## 11.3 Uniqueness degradation warning
If the original user later comes back after 7 days and launches the idea, the system must display:

> This idea was originally unique when shown to you, but because it was not started within 7 days, similar or identical ideas may have been shown to other users. If you continue now, uniqueness may have degraded.

## 11.4 Saved ideas workspace requirements
The user must be able to see:
- title
- saved date
- expiry date
- current status
- whether uniqueness degraded
- proceed/start
- archive/remove

---

# 12. Executive pipeline

No matter how the idea enters the system, once accepted it moves into executive analysis.

## 12.1 Executive phase start
The orchestrator triggers all C-Suite agents with structured context.

## 12.2 Individual specialist outputs
Each executive agent produces:
- summary
- recommendations
- risks
- role-specific analysis

## 12.3 User-facing executive review
The UI must show:
- separate panels for each executive agent
- role descriptions
- reasoning summaries
- progress/status
- final synthesis

This is one of the most important trust surfaces in the product.

## 12.4 Executive synthesis
The Executive Synthesizer merges all outputs into:
- one aligned direction
- one final executive recommendation
- one recommended product path

## 12.5 Transition
Once executive synthesis completes, the project status becomes `planning`.

---

# 13. Planning pipeline

## 13.1 PRD generation
Planning agents create:
- product goals
- users
- features
- user stories
- success criteria

## 13.2 Architecture planning
Agents define:
- app architecture
- required backend needs
- generated app runtime assumptions
- cloud integration patterns
- security concerns
- implementation phases

## 13.3 Database/auth/storage planning
The system determines:
- whether the generated app needs DB/Auth/Storage
- whether Supabase is relevant for the generated app
- whether external cloud integrations are likely

## 13.4 User-facing planning surfaces
The user can review:
- PRD
- architecture plan
- implementation phases
- versioned artifacts

## 13.5 Transition
Once accepted or completed, the project moves into `designing`.

---

# 14. Design intelligence pipeline

## 14.1 Mode and style classification
Design agents classify:
- product mode
- style mode
- layout direction
- component families

## 14.2 Design studio generation
The design system is applied to:
- landing patterns
- application shell
- workspace views
- idea cards
- executive panels
- build cockpit
- deployment surfaces

## 14.3 User-facing outputs
The user sees:
- mode/style
- page architecture
- component plans
- previews
- tokens
- design refinements

## 14.4 Design refinement
The user can:
- refine design
- change mode
- change style
- regenerate previews

## 14.5 Transition
Once design artifacts are ready, the project proceeds toward capability selection.

---

# 15. Capability gate

Before Autonomous/Automation build begins, the system must ask:

- Do you want database in the generated app?
- Do you want auth in the generated app?
- Do you want AI inside the generated app?

## 15.1 User may choose any combination
Allowed combinations:
- none
- DB only
- Auth only
- AI only
- DB + Auth
- DB + AI
- Auth + AI
- DB + Auth + AI

The user may also skip all and continue.

## 15.2 DB/Auth guidance
If the user wants generated-app DB/Auth:
the system must clearly explain that current built-in support is:
- Supabase Database
- Supabase Storage
- Supabase Auth

This applies to generated apps only, not the platform core.

## 15.3 External cloud integrations
The system must also explain that users can integrate:
- Cloudflare
- AWS
- GCP
- other managed DBs/Auth/APIs

Condition:
- they must be external cloud-managed integrations
- they must not be installed locally in the sandbox

## 15.4 AI provider choice
If the user selects AI:
- allow one or more providers
- allow model preferences when relevant
- collect credentials securely only if needed

## 15.5 Transition logic
If no credentials are needed, continue to build preparation.
If credentials are needed, route to secure secrets collection.

---

# 16. Secure secret handling

## 16.1 Collection
Secrets must be collected through secure UI flows, not normal editor chat.

Examples:
- AI provider API keys
- cloud service credentials
- external auth provider credentials

## 16.2 Encryption requirement
Persisted secrets must be encrypted using:
- AES-256-GCM

## 16.3 Approved storage strategy
Preferred:
- platform-controlled encrypted secret vault
- trusted backend-only decryption
- ephemeral runtime injection
- backend proxy when possible

## 16.4 Prohibited storage
Never store raw secrets in:
- browser localStorage
- plaintext files
- logs
- normal chat transcripts

## 16.5 AI without DB/Auth case
If the generated app does not need DB/Auth but still needs AI:
- still store keys in the platform secret vault
- expose AI through backend proxy or ephemeral runtime injection
- do not rely on browser localStorage

## 16.6 User-facing trust messaging
The product must clearly tell the user:
- secrets are encrypted at rest
- raw keys are not stored in browser localStorage
- keys are only made available through controlled runtime paths

## 16.7 Transition
Once required secrets are collected, the project moves into code generation.

---

# 17. Build preparation

At this point the system has:
- source idea/prompt
- executive synthesis
- PRD
- architecture plan
- design artifacts
- capability choices
- secret readiness if needed

The orchestrator compiles the build inputs into the code generation context.

---

# 18. Code generation pipeline

## 18.1 Engineering input
Engineering agents receive:
- project context
- build prompt
- design blueprint
- capability choices
- secret/runtime requirements
- sandbox rules

## 18.2 Generated app strategy
Depending on user choices:
- frontend-only app
- frontend + generated app Supabase integration
- frontend + AI provider integration
- frontend + external cloud integration scaffolding

## 18.3 Enforcement
The code generator must not produce:
- local MySQL
- local MongoDB server
- local Redis server
- local Postgres server
- Kafka/RabbitMQ/Elasticsearch
- privileged infra inside sandbox

## 18.4 Result
The project is turned into a runnable code bundle and moved into sandbox build.

---

# 19. Sandbox runtime pipeline

## 19.1 Provisioning
The system provisions a Fly.io MicroVM sandbox.

## 19.2 Runtime injection
If required:
- ephemeral secrets are injected
- runtime environment is prepared
- secure proxy patterns are enabled

## 19.3 Build stages
Typical stages:
- provisioning
- syncing
- installing
- building
- running

## 19.4 User-visible status
The UI must show:
- queued
- planning
- generating code
- building
- repairing
- ready for preview
- failed

## 19.5 Logs
Build and runtime logs are visible to the user.

---

# 20. Repair loop

If build fails:

## 20.1 Error analysis
The system analyzes:
- build failure
- syntax failure
- dependency failure
- runtime issue
- policy issue

## 20.2 Repair generation
A repair agent creates a minimal patch.

## 20.3 Validation
The patch is validated across:
- syntax
- dependencies
- runtime
- policy

## 20.4 Rebuild
The sandbox rebuilds.

## 20.5 Exit conditions
The repair loop ends when:
- preview is successfully running
- or the build fails irrecoverably and user sees a clear error state

---

# 21. Preview-ready state

When preview is running:
- project status becomes `ready_for_preview`
- sandbox status becomes `running`
- preview URL is available
- logs remain accessible

The user can now inspect the generated app.

---

# 22. Monaco build workspace

Once the app is ready, the user enters the build workspace.

## 22.1 Required surfaces
The workspace must include:
- Monaco editor
- file tree
- conversational AI panel
- patch preview
- sandbox logs
- preview panel or launcher
- orchestration/build state

## 22.2 Purpose
This is the iterative refinement environment where the user can keep building after initial generation.

---

# 23. Editor conversational AI

The editor assistant is not a generic chatbot.
It is a front door into specialist agents.

## 23.1 Supported requests
The user can ask:
- explain code
- add feature
- redesign UI
- refactor
- fix bug
- connect cloud service
- rebuild preview
- deploy app

## 23.2 Routing behavior
Requests are classified and routed to appropriate agent families:
- design
- engineering
- patch safety
- sandbox
- deployment
- planning

## 23.3 User-facing messages
The UI should show system messages like:
- routing to design-edit + patch-safety agents
- patch validated
- sandbox rebuilt successfully
- deployment started

This increases confidence.

---

# 24. Safe patch editing pipeline

All requested edits pass through:

1. intent classification
2. target scope resolution
3. AST parsing
4. safe edit boundary detection
5. minimal diff patch generation
6. syntax/type/dependency/policy validation
7. sandbox verification
8. apply or rollback

## 24.1 Protected areas
Patching must treat these as high-risk/protected:
- auth wiring
- router setup
- env config
- DB clients
- deployment config
- sandbox policy config
- secret handling codepaths

## 24.2 Concurrency protection
Use distributed locks to avoid conflicting patch application or rebuild operations.

---

# 25. Deployment flow

## 25.1 Available actions
The user can:
- connect git
- commit changes
- push
- deploy to Vercel

## 25.2 Deployment states
- connecting git
- committing
- deploying
- deployed
- failed

## 25.3 User-visible outputs
The user sees:
- deployment status
- deployment URL
- logs/history

---

# 26. Learning loop

The platform must capture feedback from:
- ideas selected/rejected/saved
- design refinements
- patch approvals/rejections
- build failures and repairs
- deployment outcomes

Learning agents use that to improve:
- prompt quality
- pattern ranking
- reflection
- future generation quality

---

# 27. Reliability and scaling behavior

Forge is designed for approximately 1M requests/day.

## 27.1 Redis
Used for:
- caching
- project summary caching
- request dedupe
- rate limiting
- distributed locks
- idempotency

## 27.2 Inngest
Used for:
- durable workflows
- retries
- scheduled jobs
- idea expiry
- secret rotation/revocation jobs
- repair/reflection workflows

## 27.3 Observability
Use:
- OpenTelemetry
- Sentry
- system logging
- sandbox log visibility

---

# 28. Security and policy rules

## 28.1 Mandatory security guarantees
- persisted secrets use AES-256-GCM
- raw secrets are never stored in localStorage
- raw secrets are never logged
- raw secrets are never persisted in chat transcripts
- only trusted backend contexts may decrypt
- all secret access is auditable

## 28.2 Sandbox restrictions
The following must be blocked inside sandbox:
- MySQL
- MariaDB
- MongoDB server
- Redis server
- Elasticsearch
- RabbitMQ
- Kafka
- self-hosted Postgres
- arbitrary daemons
- privileged containers

## 28.3 Allowed integrations
External cloud-managed services are allowed if:
- they are not installed locally in sandbox
- credentials are collected securely
- credentials are encrypted at rest
- runtime use is controlled

---

# 29. Full lifecycle status model

## Project statuses
- draft
- executive_review
- planning
- designing
- capability_gate
- waiting_for_secrets
- generating_code
- building
- repairing
- ready_for_preview
- deploy_ready
- deployed
- failed

## Idea statuses
- saved_only
- in_csuite
- planned
- designing
- building
- active_project
- archived
- resurfaced

## Job statuses
- queued
- running
- paused
- waiting_input
- retrying
- completed
- failed
- cancelled

## Sandbox statuses
- provisioning
- syncing
- installing
- building
- running
- stopped
- failed

---

# 30. Production readiness checklist

A production-ready implementation of this flow must ensure:

## User journey
- user can start with their own idea
- user can start with a curated idea
- user can reject into questionnaire flow
- user can save ideas
- user gets 7-day uniqueness behavior correctly

## Executive trust
- all C-Suite agents visible
- synthesis visible
- collaboration visible

## Planning and design
- PRD and architecture visible
- design studio visible and refinable

## Capability gate
- DB/Auth/AI selection explicit
- Supabase support explained
- external cloud integrations explained
- skipping supported

## Secret handling
- secure UI exists
- AES-256-GCM storage exists
- no raw secrets in localStorage
- runtime injection/proxy exists

## Build
- code generation follows capability choices
- sandbox policy is enforced
- build statuses are visible
- repair loop works

## Editor
- AI assistant routes to specialist systems
- patch preview exists
- validation exists
- rebuild loop exists

## Deployment
- git and Vercel flow exists
- deployment status visible

## Reliability
- workflow durability exists
- retries exist
- locks exist
- observability exists

---

# 31. Final implementation note

This document is the authoritative end-to-end user flow for Forge.

Any implementation should preserve:
- the specialized collaborative-agent model
- the capability gate before build
- the secure secret-management rules
- the distinction between platform core and generated-app backend
- the sandbox restrictions
- the saved-idea 7-day expiry logic
- the validated patching/build pipeline
- the visible trust surfaces throughout the product