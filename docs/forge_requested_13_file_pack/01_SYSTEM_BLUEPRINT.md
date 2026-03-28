# 01_SYSTEM_BLUEPRINT.md

## Core trust message
Forge is a coordinated team of specialized agents working together in concert.

### C-Suite
- CEO
- CPO
- CTO
- CDO
- CFO
- CMO
- COO
- CISO
- Executive Synthesizer

### Other agent families
- Idea & Curation Agents
- Planning Agents
- Design Agents
- Engineering Agents
- Runtime / Sandbox Agents
- Deployment Agents
- Learning Agents

## Stack
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

Only when required by the generated application.

## User entry paths
- user types own idea and sends AS-IS to C-Suite
- user enhances prompt first
- user sees Top #1 curated idea first
- if rejected, questionnaire flow begins
- then 5 curated ideas are shown
- saved-only ideas have a hard 7-day uniqueness timer

## Capability gate
Before build:
- ask if generated app needs DB
- ask if generated app needs Auth
- ask if generated app needs AI
- explain Supabase support for generated apps
- allow external cloud services if not installed locally in sandbox
- allow user to skip all and continue

## Secrets
- persisted secrets encrypted with AES-256-GCM
- no raw secret storage in localStorage
- prefer platform secret vault + backend proxy or ephemeral runtime injection
