# 00_READ_FIRST_MASTER_PROMPT.md

You are building **Forge**, an AI-powered product creation platform.

## Read order
1. 00_READ_FIRST_MASTER_PROMPT.md
2. 01_SYSTEM_BLUEPRINT.md
3. 02_FRONTEND_MASTER_PROMPT.md
4. 03_BACKEND_MASTER_PROMPT.md
5. 04_DATABASE_SCHEMA.md
6. 05_MICROSERVICES_ARCHITECTURE.md
7. 06_AI_ORCHESTRATOR.md
8. 07_AGENT_LIBRARY.md
9. 08_DESIGN_SYSTEM.md
10. 09_FIGMA_READY_TOKENS.json
11. 10_SECRET_MANAGEMENT_AND_CAPABILITY_GATE.md
12. 11_SCALING_AND_RELIABILITY.md
13. 12_BUILD_SEQUENCE.md

## Core rules
- Platform core uses React + Vite, TailwindCSS, Python FastAPI, Nhost PostgreSQL, Nhost Auth, Fly.io MicroVM, Upstash Redis, and Inngest.
- Generated apps may optionally use Supabase DB/Auth/Storage only when selected and needed.
- Platform core itself must not use Supabase.
- Do not install heavy backend systems inside sandbox.
- Preserve the multi-agent collaboration model.
- Preserve the industrial cinematic design system exactly.
- Build in phases from the build sequence.
