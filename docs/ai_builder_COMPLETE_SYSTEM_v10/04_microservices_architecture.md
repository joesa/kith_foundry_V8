# Microservices Architecture + Implementation Guide (v10)

## Control-plane philosophy
The platform should be described as a collaboration of specialized services and specialized agents.

### Product Intelligence Layer
- C-Suite reasoning
- executive synthesis
- PRD generation
- architecture planning

### Idea Intelligence Layer
- curated daily ideas
- ideation questionnaire
- top-5 curated ideation
- saved idea management
- exclusivity / expiry

### Design Intelligence Layer
- design mode engine
- style logic
- layout composition
- design studio

### Code Intelligence Layer
- code generation
- patch safety
- self-healing

### Runtime Intelligence Layer
- sandbox management
- sandbox policy enforcement
- preview lifecycle

### Deployment Intelligence Layer
- git workflows
- deployment workflows

### Learning Intelligence Layer
- reflection
- feedback capture
- pattern ranking
- optimization

## Platform control plane stack
- React + Vite + Tailwind frontend
- Python + FastAPI API/orchestrator
- Nhost PostgreSQL
- Nhost Auth
- Fly.io MicroVM sandboxes
- Upstash Redis (via Fly integration)
- Inngest
