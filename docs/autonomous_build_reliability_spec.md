# Autonomous Build Reliability Specification

This document explains how to ensure an autonomous/automated system can reliably produce a working application from idea to build to deployment in the sandbox.

## Core principle

The system should not rely on a single giant prompt that jumps straight from idea to code.

Instead, it should move through a controlled chain:

**idea → executive validation → product spec → architecture spec → design spec → capability gate → secret readiness → codegen plan → code generation → static validation → sandbox build → repair loop → preview verification → deploy**

Every stage should produce machine-checkable artifacts, and the next stage should proceed only if the previous stage passed validation.

---

## 1. Convert ideas into structured artifacts first

An idea should never go straight to code.

No matter where it comes from:
- typed user idea
- curated top idea
- guided ideation result

the system should first generate:
- executive synthesis
- PRD
- architecture plan
- feature list
- data/auth/integration needs
- design blueprint
- build plan

This keeps the build grounded.

### Hard rule
No code generation unless required upstream artifacts exist and pass validation.

---

## 2. Make each stage pass a gate

Every major stage should have explicit exit criteria.

### Executive gate
Must answer:
- who is this for
- what problem is being solved
- what the MVP is
- what the constraints are

### PRD gate
Must include:
- goals
- core features
- out-of-scope items
- user flows
- acceptance criteria

### Architecture gate
Must include:
- app type
- frontend/backend shape
- DB/auth/AI requirements
- external cloud integrations
- runtime constraints
- sandbox compliance

### Design gate
Must include:
- mode/style
- key pages
- components
- interaction logic
- layout hierarchy

### Capability gate
Must resolve:
- DB
- Auth
- AI
- external cloud services
- required secrets

### Build gate
Must confirm:
- all required secrets collected
- all required artifacts present
- stack is sandbox-safe
- banned infrastructure not requested

If any gate fails, the system must stop and repair upstream.

---

## 3. Use a constrained build contract

Before code generation, create one **Build Contract** artifact.

This contract should contain:
- app name
- product summary
- route map
- page list
- component inventory
- backend requirements
- Supabase usage yes/no
- AI provider usage yes/no
- external cloud integrations yes/no
- required secrets list
- disallowed infrastructure list
- design tokens/style rules
- acceptance tests to satisfy

This prevents code generation from improvising.

---

## 4. Force capability clarity before codegen

A major cause of broken builds is hidden assumptions around DB/Auth/AI.

Before generation, the system must ask:
- do you want DB
- do you want Auth
- do you want AI
- do you want external cloud integrations

Then it locks those choices into the build contract.

### Examples

#### Frontend-only app
Generate no backend assumptions.

#### App with DB/Auth
Use approved generated-app path:
- Supabase DB/Auth/Storage

#### App with AI
Require secure secret setup and choose:
- backend proxy
- ephemeral runtime injection
- provider SDK usage pattern

#### App with external cloud
Generate integration scaffolding only.
Do not install infrastructure locally.

This removes ambiguity.

---

## 5. Generate from templates plus patches

Autonomous systems become more reliable when they generate from approved base templates.

Use:
- approved frontend template
- approved Supabase integration template
- approved auth flow template
- approved AI integration template
- approved cloud integration adapters

Then customize those templates with controlled patches.

### Hard rule
Prefer composition over freeform invention.

---

## 6. Add static validation before sandbox build

Before sandbox execution, validate:
- file tree completeness
- route completeness
- import resolution
- type safety
- dependency allowlist
- secrets references
- forbidden package usage
- banned infrastructure detection
- required env variables

This catches many failures cheaply.

---

## 7. Build only inside a controlled sandbox

The sandbox is the truth-test.

Inside Northflank sandbox, run:
1. install
2. build
3. start
4. smoke test
5. preview verification

The sandbox should enforce:
- no heavy backend installs
- no forbidden daemons
- no unsafe infra
- resource limits
- secret injection only through approved paths

---

## 8. Add a smoke-test layer after build

A build succeeding is not enough.
The app must also be minimally functional.

After preview starts, run smoke tests such as:
- homepage loads
- expected routes render
- no fatal runtime errors
- auth page renders if auth enabled
- DB client initializes if DB enabled
- AI route/client loads if AI enabled
- key components mount
- API health endpoints respond if relevant

### Hard rule
No “ready” status unless smoke tests pass.

---

## 9. Add self-healing repair loops

If the sandbox build fails:
- classify the error
- identify the failing stage
- generate a minimal repair patch
- validate the patch
- rebuild
- rerun smoke tests

Common failure classes:
- missing import
- dependency mismatch
- route mismatch
- type error
- missing env reference
- unsupported package
- bad AI wiring
- broken Supabase setup
- component prop mismatch

The repair system should patch narrowly.

---

## 10. Use AST-safe patching for repairs and edits

After the project exists, all modifications should use a guarded patch pipeline:
- intent classification
- file/target selection
- AST boundary detection
- minimal diff generation
- validation
- sandbox verification
- apply/rollback

This prevents one fix from breaking unrelated code.

---

## 11. Enforce a deployment readiness checklist

Before deployment, require:
- preview running
- smoke tests passing
- no blocked policy violations
- required secrets present
- capability selections resolved
- no unresolved repair errors
- deployment config generated
- environment variables mapped correctly

Only then allow:
- git commit
- Vercel deploy

---

## 12. Make the system observable

Track:
- current stage
- current agent family
- artifact versions
- sandbox status
- build logs
- repair attempts
- smoke test results
- secret readiness
- deployment status

This helps both users and the system debug failures.

---

## 13. Add acceptance criteria per project before codegen

For every project, derive acceptance checks from the PRD.

### Example: SaaS dashboard
- dashboard page loads
- nav works
- settings page exists
- forms render
- auth route exists if enabled
- DB config present if enabled

### Example: landing page
- homepage loads
- CTAs visible
- sections present
- responsive shell intact

This makes the system product-aware, not just code-aware.

---

## 14. Separate “buildable” from “interesting”

Some ideas are good businesses but poor autonomous-build candidates.

Before build, the system should score:
- market quality
- product clarity
- buildability
- dependency complexity
- secret/integration burden
- sandbox fit

If buildability is weak, the system should:
- narrow scope
- simplify MVP
- stage the build
- defer complex integrations

### Hard rule
The C-Suite and planning agents should optimize not just for opportunity, but for autonomous build success.

---

## 15. Recommended hard guarantees

1. No codegen without executive synthesis.
2. No codegen without PRD.
3. No codegen without architecture plan.
4. No build without capability gate resolution.
5. No AI-enabled app without secret readiness.
6. No local heavy backend installs in sandbox.
7. No preview-ready status without smoke-test pass.
8. No deploy without deployment-readiness checklist pass.
9. All edits after generation must use patch-safety validation.
10. All failures must either repair or stop with a clear reason.

---

## 16. Practical end-to-end success architecture

The full reliable flow should be:

**Idea intake**
→ validate and classify

**Executive phase**
→ C-Suite specialist analysis
→ executive synthesis

**Planning phase**
→ PRD
→ architecture
→ MVP and route map

**Design phase**
→ mode/style
→ page/component blueprint

**Capability phase**
→ DB/Auth/AI decision
→ external cloud decision
→ secret requirements derived

**Secret phase**
→ secure collection
→ encrypted storage
→ runtime strategy selected

**Build contract generation**
→ exact app spec
→ exact routes/components/integrations/tests

**Code generation**
→ approved templates plus constrained generation

**Static validation**
→ type/import/dependency/policy/env checks

**Sandbox build**
→ install/build/start

**Smoke tests**
→ app behavior checks

**Repair loop**
→ minimal patches
→ rebuild
→ re-test

**Preview ready**
→ user inspects and edits

**Editor refinement**
→ AST-safe patching
→ verified rebuilds

**Deployment readiness**
→ deploy only when checks pass

**Deployment**
→ git plus Vercel

---

## 17. Bottom line

To ensure the system reliably produces a working application from idea to build to deployment, you need:
- structured artifacts before code
- hard gates between stages
- capability clarity before build
- secure secret handling
- approved templates
- static validation
- sandbox verification
- smoke tests
- repair loops
- safe patching
- deployment readiness checks
- full observability

That is what turns an autonomous builder from a demo into a dependable system.
