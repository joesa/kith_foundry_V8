# 05_EVENT_AND_WORKFLOW_CONTRACTS.md

Workflow engine: Inngest

## Event naming convention
`forge.<domain>.<action>`

## Core events
- `forge.idea.saved`
- `forge.idea.expiry.check`
- `forge.project.executive.started`
- `forge.project.executive.completed`
- `forge.project.design.started`
- `forge.project.design.completed`
- `forge.project.build.started`
- `forge.project.build.completed`
- `forge.project.build.failed`
- `forge.project.repair.started`
- `forge.project.repair.completed`
- `forge.project.deploy.started`
- `forge.project.deploy.completed`

## Full build workflow
1. executive phase
2. planning phase
3. design phase
4. capability gate completion check
5. secrets completeness check
6. codegen
7. sandbox build
8. repair if needed
9. preview ready

## Saved idea expiry workflow
- scheduled exactly at `savedExpiresAt`
- if idea still `saved_only`, mark `uniqueness_degraded = true`
- create warning event
- idea becomes eligible for resurfacing

## Secret rotation workflow
- receive rotation request
- mark old secret as rotated or revoked
- persist new encrypted secret
- emit audit record
