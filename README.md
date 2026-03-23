# Design Mode + Style Engine Implementation Spec

This package adds a first-class **Design Mode + Style** system to the AI builder.

## Goal

Turn design mode selection into a real backend capability rather than a prompt-only concept.

The system classifies:

- **Product Mode** (for example: SaaS Dashboard, Portfolio, Marketplace)
- **Style Mode** (for example: Stripe SaaS, Apple Editorial, Swiss Modern)

Then persists those choices to the Project Brain and injects them into downstream agents.

---

## Architecture Update

Updated pipeline:

```text
User Prompt
→ Intent Agent
→ Mode Classifier Agent
→ Style Selector
→ Design Agent
→ Layout Composition Engine
→ Component Agent
→ Code Agent
```

---

## What This Adds

- mode classifier output schema
- Project Brain schema additions
- database migration
- API routes
- backend service to load the design mode pack
- classifier function
- Fastify route example
- persistence helpers
- frontend selector component
- downstream prompt injection contract

---

## Data Contracts

### ModeClassificationResult

```ts
export interface ModeClassificationResult {
  productMode: string
  styleMode: string
  confidence: number
  alternatives: Array<{
    productMode: string
    styleMode: string
    confidence: number
  }>
  reasoning: {
    matchedKeywords: string[]
    matchedFeatures: string[]
    matchedAudienceSignals: string[]
    matchedToneSignals: string[]
  }
}
```

### ProjectBrain Extension

```ts
export interface ProjectBrain {
  project: {
    id: string
    name: string
    description: string
    framework: string
  }
  designMode: {
    productMode: string
    styleMode: string
    confidence: number
    lockedByUser: boolean
  }
  designTokens: Record<string, unknown>
  pages: PageNode[]
  components: ComponentNode[]
  features: FeatureNode[]
  files: FileNode[]
}
```

---

## Database Migration

```sql
ALTER TABLE projects
ADD COLUMN product_mode TEXT,
ADD COLUMN style_mode TEXT,
ADD COLUMN mode_confidence NUMERIC(5,4),
ADD COLUMN design_mode_locked BOOLEAN DEFAULT FALSE;
```

Optional history:

```sql
CREATE TABLE project_design_mode_history (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  product_mode TEXT NOT NULL,
  style_mode TEXT NOT NULL,
  confidence NUMERIC(5,4),
  source TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Routes

```text
POST /api/design/classify-mode
POST /api/design/lock-mode
POST /api/design/unlock-mode
GET  /api/design/mode-options
```

---

## Prompt Injection Contract

Every design/layout/component/code agent should receive:

```text
DESIGN MODE CONTEXT
Product Mode: SaaS Dashboard
Style Mode: Stripe SaaS
Design Type: Analytical, structured, productivity-focused
Layout Model: Sidebar + Topbar + Content Grid
Density: high
Recommended Patterns: Sidebar Navigation, Metric Cards, Analytics Charts, Data Tables
```

---

## Rollout Plan

### Phase 1
- add DB fields
- load JSON pack
- add classify endpoint

### Phase 2
- persist mode/style in Project Brain
- inject mode/style into design and layout agents

### Phase 3
- add frontend selector
- support manual lock override

### Phase 4
- add history and confidence-based reclassification

---

## Files Included

- `src/types/design-mode.ts`
- `src/ai/prompts/mode-classifier.prompt.ts`
- `src/ai/classify-design-mode.ts`
- `src/services/design-mode-service.ts`
- `src/services/project-brain-service.ts`
- `src/routes/design.ts`
- `src/components/DesignModeSelector.tsx`
- `migrations/001_add_design_mode_fields.sql`

These are starter files intended to be adapted to your actual backend framework and DB layer.
