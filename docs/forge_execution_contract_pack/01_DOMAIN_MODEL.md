# 01_DOMAIN_MODEL.md

## Primary entities

### User
A human account authenticated through Nhost Auth.

### Workspace
A collaboration boundary containing projects, saved ideas, settings, and secrets.

### Project
A product creation effort, possibly originating from:
- typed prompt
- curated top idea
- guided ideation selection
- saved idea launch

### Idea
An opportunity record that may be:
- curated
- generated
- saved
- launched into active execution

### Artifact
A versioned system output such as:
- executive summary
- PRD
- architecture plan
- design blueprint
- build prompt
- patch validation result

### Job
A long-running orchestrator workflow.

### Sandbox
A Fly.io MicroVM runtime created for a project build/preview.

### Secret
An encrypted credential record stored in the platform secret vault.

## Key statuses

### Idea status
- `saved_only`
- `in_csuite`
- `planned`
- `designing`
- `building`
- `active_project`
- `archived`
- `resurfaced`

### Project status
- `draft`
- `executive_review`
- `planning`
- `designing`
- `capability_gate`
- `waiting_for_secrets`
- `generating_code`
- `building`
- `repairing`
- `ready_for_preview`
- `deploy_ready`
- `deployed`
- `failed`

### Job status
- `queued`
- `running`
- `paused`
- `waiting_input`
- `retrying`
- `completed`
- `failed`
- `cancelled`

### Sandbox status
- `provisioning`
- `syncing`
- `installing`
- `building`
- `running`
- `stopped`
- `failed`
