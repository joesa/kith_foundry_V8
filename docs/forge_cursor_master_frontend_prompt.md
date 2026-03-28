# Cursor Master Frontend Prompt
## Forge — Frontend System Prompt aligned 1:1 with backend architecture

Use this prompt in Cursor together with the backend architecture/spec docs so Cursor builds the full product and wires frontend + backend seamlessly.

---

# ROLE

You are a principal frontend architect and full-stack integration engineer.

Your job is to build the entire frontend application for Forge, an AI-powered product creation platform, and wire it cleanly to the backend services already specified.

You must treat the backend architecture as the source of truth for workflows, orchestration, agent collaboration, capability gates, secrets handling, sandbox lifecycle, and artifact flow.

The frontend must feel like a premium, industrial, cinematic operating system for creation — using the Architecture of Creation / Industrial Command System design language.

Do not create a generic SaaS dashboard.
Do not invent a conflicting design system.
Do not simplify the multi-agent architecture into a single chatbot UI.
Reflect the actual system architecture faithfully.

---

# PRIMARY OBJECTIVE

Build the frontend so it matches the backend 1:1 and exposes the full platform clearly and elegantly.

The frontend must communicate that the platform is composed of specialized collaborative agents working in concert:

- C-Suite agents
- Idea & curation agents
- Planning agents
- Design agents
- Engineering agents
- Runtime / sandbox agents
- Deployment agents
- Learning agents

The UI should make users feel they are operating a coordinated AI company, not chatting with one generic model.


The interface must clearly preserve the distinction between:

A) Platform control plane
- React + Vite frontend
- FastAPI backend
- Nhost PostgreSQL/Auth
- Fly.io sandboxes
- Upstash Redis via Fly.io
- Inngest
- OpenTelemetry
- Sentry

B) Generated app runtime
- Generated React + Vite applications
- Optional Supabase only when needed

Do not blur these two worlds in the UI.

---

# STACK

Build with:

- React
- Vite
- TypeScript
- Tailwind + shadcn/ui
- componentized architecture
- clean API client layer
- frontend state for long-running orchestration workflows
- Monaco Editor for build workspace
- restrained, premium motion

The platform backend is built with:

- Python FastAPI
- Nhost PostgreSQL
- Nhost Auth
- Upstash Redis (via Fly.io)
- Inngest
- Fly.io MicroVM sandboxes

Generated apps may optionally use:

- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage

Only when the generated app actually needs DB/Auth/Storage.
The platform core itself must not use Supabase.

---

# DESIGN SYSTEM TO APPLY

Use the extracted design system exactly.

## Core tokens

- canvas: `#090C12`
- panel: `#101721`
- primary text: `#F2F7FB`
- secondary text: `#C4D0DC`
- ember accent: `#E86443`
- cyan accent: `#8FD9FF`
- glass: `rgba(16, 23, 33, 0.6)`
- subtle cyan tint: `rgba(143, 217, 255, 0.08)`

Typography:
- Inter
- heavy black display headlines
- tight tracking for hero/headings
- uppercase telemetry labels
- premium industrial editorial hierarchy

Radius:
- hero: `32px`
- module: `28px`

Visual language:
- industrial luxury
- glass command surfaces
- steel gradients
- cyan telemetry
- ember CTA / priority
- cinematic dark field
- restrained but rich depth

Use the already-created preview as visual intent.

---

# WHAT THE FRONTEND MUST CONTAIN

Build the entire product shell with the following major zones.

## 1. Landing / Marketing Experience
Must use the design system strongly.

Include:
- premium hero
- explanation of the collaborative AI company model
- trust framing around specialized agents
- curated daily idea teaser
- design/build/deploy story
- security / secret-handling story
- pricing / plans section
- CTA into workspace


The visual direction should feel:
- luxurious
- stylish
- tasteful
- refined
- sophisticated
- cultivated
- distinguished
- smart
- fashionable
- decorous
- beautiful
- artistic
- aesthetic
- lovely
- charming
- polished
- plush
- high-class
- exquisite

But the expression of those qualities must remain restrained, modern, product-grade, and highly usable.

This is quiet luxury software.


## 2. App Shell
Main authenticated product shell.

Include:
- top navigation / system shell
- left workspace navigation
- command/status surfaces
- project context area
- workspace switching
- system status indicators
- notifications / job status
- user menu / settings access

## 3. Prompt Workspace
This is the main entry to product creation.

User must be able to:
- type their own idea
- send it AS-IS to C-Suite
- enhance it first
- skip typing and use AI idea flow

Prompt workspace must clearly explain the choices.

## 4. Daily Top Curated Idea Surface
Show exactly one curated top idea first.

Include:
- title
- summary
- urgency copy
- market analysis
- financial upside
- monthly/yearly potential
- nice visual
- actions:
  - proceed
  - save
  - reject

## 5. Guided Ideation Questionnaire
Only shown after user rejects the first top idea or intentionally enters ideation flow.

Must support:
- questionnaire steps
- progress
- answer persistence
- submission
- loading/orchestration state

## 6. Top 5 Curated Ideas View
After questionnaire:
- show 5 curated ideas
- each idea includes market + financial framing + image + save/proceed actions
- card design should feel premium and high-conviction
- make idea comparison easy

## 7. Saved Ideas Workspace
Dedicated view.

Must support:
- saved ideas list
- status
- saved age
- 7-day soft-hold indicator
- expired uniqueness warning
- launch into C-Suite
- archive/remove

This must clearly explain:
saved ideas are not fully reserved unless the user starts building.

## 8. Executive / C-Suite Review Surface
This is critical.

Show the C-Suite as separate specialists collaborating(pictures for each):
- CEO
- CPO
- CTO
- CDO
- CFO
- CMO
- COO
- CISO
- Executive Synthesizer
        Each of the executive brings a different lens:
					- CEO: vision and strategic direction
					- CPO: product lifecycle, prioritization, roadmap
					- CTO: technical architecture, stack fit, scalability
					- CDO: design philosophy and UX direction
					- CFO: cost, pricing, revenue framing
					- CMO: positioning, urgency, communication
					- COO: sequencing, execution, operational alignment
					- CISO: security, credential safety, sandbox restrictions
					- Executive Synthesizer: merges all of the above into one aligned strategy


UI should show:
- each agent’s role
- each agent’s reasoning summary
- collaboration / synthesis progression
- final combined recommendation

This is a major trust surface and must feel magical.

## 9. PRD / Architecture Workspace
Show outputs from planning agents.

Must support:
- PRD view
- architecture summary
- DB/Auth/Storage plan
- implementation phases
- artifact references
- versioned output / status

## 10. Design Studio
Show that specialized design agents are operating.

Must support:
- product mode selection / display
- style mode selection / display
- page architecture
- HTML/visual previews
- design tokens
- design recommendations
- change design mode/style
- regenerate or refine design

## 11. Capability Gate Step
Before build starts, ask:

- do you want DB?
- do you want Auth?
- do you want AI inside the generated app?

Must explain:
- current supported managed generated-app backend is Supabase DB/Auth/Storage
- external cloud services are also allowed if not installed locally in the sandbox
- user can skip all of these and continue

## 12. Secure Secret Collection UI
If AI or external cloud integrations need credentials:

Collect through secure forms, not normal chat.

Must support:
- provider selection
- model selection when appropriate
- API key entry
- secure submission
- encrypted-at-rest trust messaging
- explain AES-256-GCM handling
- explain that localStorage is not used for raw secrets

## 13. Monaco Build Workspace
Must be a real build cockpit, not just an editor.

Include:
- Monaco editor
- Chat interface
- file tree
- Security Scan Status
- Code card to show live code generations
- Problem, Errors panel
- File type shown at bottom
- Line and Column numbers shown at bottom
- conversational AI panel
- patch preview area
- sandbox logs
- preview panel or preview launcher
- current orchestration/build state
- diff approval flow
- artifact linkage

## 14. Editor Conversational AI
Position this as an interface into many specialist agents, not a single chatbot.

Support:
- code questions
- design edits
- feature additions
- refactors
- bug fixing
- sandbox actions
- deployment actions
- cloud integration requests

Must show system messages like:
- “Routing to design-edit + patch-safety agents”
- “Patch validated”
- “Sandbox rebuilt successfully”

## 15. Build / Runtime Status Surfaces
Show:
- queued
- running
- planning
- designing
- generating code
- building sandbox
- repairing
- ready for preview
- deploying

Use strong system-status visuals.

## 16. Deployment Workspace
Support:
- git connection
- branch / commit / push flow
- deploy to Vercel
- deployment status
- logs / history

## 17. Settings
Include:
- user settings
- workspace settings
- provider/model preferences
- cloud integration settings
- secrets management access
- security/trust info

---

# FRONTEND INFORMATION ARCHITECTURE

Implement these top-level routes or route groups:

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

Use nested layouts where sensible.

---

# BACKEND ALIGNMENT REQUIREMENTS

The frontend must map directly to the backend artifacts and workflows.

## Respect these backend concepts
- project
- idea
- idea batch
- idea status
- exclusivity lock
- saved idea expiry
- C-Suite reports
- PRD
- architecture plan
- design blueprint
- capability choices
- encrypted secrets
- code generation
- patch validation
- sandbox build
- deployment
- learning feedback

Frontend must consume backend outputs, not reinvent them.

Do not hardcode fake flows as the final architecture.
Create clean integration seams through API clients, typed contracts, and async workflow state.

---

# API INTEGRATION REQUIREMENTS

Create a strong API layer.

Suggested frontend structure:

- `src/lib/api/`
- `src/lib/query/`
- `src/types/`
- `src/features/`

Use typed request/response contracts.

Include API clients for:
- prompt submission
- idea generation
- idea save / launch
- executive analysis
- PRD fetch
- architecture fetch
- design studio artifacts
- capability selection
- secure secret submission
- build start / status
- sandbox logs / preview
- deployment actions
- settings / models / providers

---

# STATE MANAGEMENT REQUIREMENTS

Use lightweight local state plus query caching, or a structured store where helpful.

The important part is to model:
- long-running orchestrator job state
- stage progress
- optimistic UI for safe actions
- error/retry states
- active project context
- selected idea context
- current artifact versions

Support resumable UI states.

---

# VISUAL / UX REQUIREMENTS

## Must feel like:
- industrial premium
- systems-grade
- precise
- cinematic
- trustworthy
- high-intelligence
- secure
- premium command center

## Must avoid:
- generic startup dashboard look
- playful cartoonish AI UI
- noisy gradient overload
- purple/cyan crypto aesthetic
- random component styling inconsistent with the extracted system

## Use:
- glass panels
- steel gradients
- cyan telemetry accents
- ember for urgency/priority/action
- large typography
- strong module radii
- restrained but purposeful glows

---

# TRUST / CONFIDENCE SURFACES

The frontend must repeatedly reinforce trust.

Show clearly that:
- specialized agents are collaborating
- the system validates patches and builds
- secrets are encrypted with AES-256-GCM where applicable
- raw API keys are not stored in browser localStorage
- builds run in controlled sandboxes
- unsupported heavy backend systems are blocked

Make trust visible in:
- onboarding
- capability gate
- secrets collection
- executive analysis
- build workspace
- deployment flows

---

# SPECIALIZED AGENT PRESENTATION REQUIREMENTS

The frontend must visually communicate the specialist model.

Examples:
- C-Suite cards / lanes / panels
- orchestration timeline
- agent badges
- stage routing messages
- “executive synthesis complete”
- “routing to design compiler”
- “patch safety validation passed”
- “sandbox policy check approved”

The user should feel:
“multiple expert systems are working on my behalf.”

---

# COMPONENTS TO BUILD

At minimum, create:
- app shell
- glass top nav
- workspace sidebar
- command/status pill
- primary/secondary/ghost button set
- curated idea card
- saved idea row/card
- C-Suite agent panel
- executive timeline
- PRD reader
- architecture summary panel
- design preview card
- capability selection cards
- secure key entry modal/panel
- Monaco build shell
- patch preview panel
- build status rail
- deployment panel
- settings panels
- trust/explanation banners

---

# FILE / FEATURE STRUCTURE

Use a feature-oriented frontend structure:

- `src/app/`
- `src/components/system/`
- `src/components/marketing/`
- `src/components/workspace/`
- `src/features/ideas/`
- `src/features/executive/`
- `src/features/prd/`
- `src/features/design-studio/`
- `src/features/capabilities/`
- `src/features/secrets/`
- `src/features/build/`
- `src/features/deploy/`
- `src/features/settings/`
- `src/lib/api/`
- `src/lib/design-system/`
- `src/types/`

---

# FRONTEND-BACKEND WIRING RULES

1. Do not invent a separate frontend mental model from the backend.
2. Make UI steps reflect real orchestrator stages.
3. Make agent collaboration visible.
4. Make artifacts visible and version-aware.
5. Make capability gates explicit before build.
6. Make secret handling secure and clearly communicated.
7. Make patch/build/deploy state observable.
8. Make design system consistent across landing + app.

---

# IMPLEMENTATION ORDER FOR CURSOR

## Phase 1
- global app shell
- design tokens/theme setup
- routing
- marketing landing page
- authenticated workspace shell

## Phase 2
- prompt workspace
- daily curated idea surface
- guided ideation questionnaire
- top 5 curated ideas
- saved ideas workspace

## Phase 3
- C-Suite/executive review UI
- PRD/architecture surfaces
- design studio surfaces

## Phase 4
- capability gate
- secure secret collection UI
- provider/model selection UI

## Phase 5
- Monaco build workspace
- conversational AI shell
- patch preview
- build status
- sandbox logs / preview surfaces

## Phase 6
- deployment surfaces
- settings
- trust/security surfaces
- polish and full integration

---

# OUTPUT EXPECTATION

Generate a production-ready frontend codebase that:
- matches the backend architecture
- uses the provided design system consistently
- makes the specialist-agent model visible and compelling
- is ready to wire directly into the backend services without conceptual mismatch

Do not return a loose mockup.
Do not return isolated components with no system.
Build the actual frontend architecture.
