# 02_API_CONTRACTS.md

All routes are under `/api`.

Authentication: bearer session from Nhost Auth or platform session cookie.

## 1. Prompt and idea entry

### POST `/api/prompts/submit`
Request:
```json
{
  "workspaceId": "uuid",
  "projectId": "uuid|null",
  "prompt": "Build a B2B compliance dashboard for clinics",
  "mode": "as_is|enhance_first"
}
```

Response:
```json
{
  "projectId": "uuid",
  "jobId": "uuid",
  "nextStage": "executive_review"
}
```

### GET `/api/ideas/daily`
Response:
```json
{
  "ideaId": "uuid",
  "title": "AI Vendor Security Copilot",
  "summary": "A B2B platform that automates vendor security reviews for mid-market teams.",
  "marketAnalysis": {},
  "financialAnalysis": {},
  "presentation": {
    "imageUrl": "https://...",
    "urgencyCopy": "High-upside opportunity. Act before others do."
  },
  "isSaved": false,
  "isReserved": false
}
```

### POST `/api/ideas/daily/:ideaId/action`
Request:
```json
{
  "action": "accept|reject|save"
}
```

Response:
```json
{
  "result": "accepted|rejected|saved",
  "projectId": "uuid|null",
  "nextStage": "executive_review|questionnaire|saved_ideas"
}
```

## 2. Guided ideation

### GET `/api/ideation/questionnaire`
Response:
```json
{
  "questionnaireRunId": "uuid",
  "questions": [
    {"id":"industry","type":"single_select","label":"Which industries interest you?","options":["healthcare","finance","ops","legal","creator"]}
  ]
}
```

### POST `/api/ideation/questionnaire/:runId/submit`
Request:
```json
{
  "answers": {
    "industry": "healthcare"
  }
}
```

Response:
```json
{
  "jobId": "uuid",
  "nextStage": "curated_five_generation"
}
```

### GET `/api/ideas/batches/:batchId`
Response:
```json
{
  "batchId": "uuid",
  "batchType": "five_pack",
  "items": [
    {
      "ideaId": "uuid",
      "rank": 1,
      "title": "...",
      "summary": "...",
      "marketAnalysis": {},
      "financialAnalysis": {},
      "presentation": {}
    }
  ]
}
```

## 3. Saved ideas

### GET `/api/saved-ideas`
Response:
```json
{
  "items": [
    {
      "ideaId": "uuid",
      "title": "...",
      "status": "saved_only",
      "savedAt": "2026-03-20T12:00:00Z",
      "savedExpiresAt": "2026-03-27T12:00:00Z",
      "uniquenessDegraded": false
    }
  ]
}
```

### POST `/api/saved-ideas/:ideaId/start`
Response:
```json
{
  "projectId": "uuid",
  "jobId": "uuid",
  "warning": "This idea may have been shown to others."
}
```

## 4. Executive review and planning artifacts

### GET `/api/projects/:projectId/executive`
Response:
```json
{
  "projectId": "uuid",
  "reports": [
    {"agent":"CEO","summary":"..."},
    {"agent":"CPO","summary":"..."},
    {"agent":"CTO","summary":"..."}
  ],
  "synthesis": {
    "summary": "...",
    "recommendedDirection": "..."
  }
}
```

### GET `/api/projects/:projectId/prd`
### GET `/api/projects/:projectId/architecture`

## 5. Design studio

### GET `/api/projects/:projectId/design`
Response:
```json
{
  "projectId": "uuid",
  "mode": "saas_dashboard",
  "style": "industrial_command",
  "pages": [],
  "components": [],
  "tokens": {},
  "htmlPreviews": []
}
```

## 6. Capability gate

### GET `/api/projects/:projectId/capabilities`
### POST `/api/projects/:projectId/capabilities`

## 7. Secrets

### POST `/api/projects/:projectId/secrets/intake-session`
### POST `/api/projects/:projectId/secrets`
### GET `/api/projects/:projectId/secrets`
### POST `/api/secrets/:secretId/revoke`

## 8. Build and sandbox
### POST `/api/projects/:projectId/build`
### GET `/api/projects/:projectId/jobs/:jobId`
### GET `/api/projects/:projectId/sandbox`
### GET `/api/projects/:projectId/sandbox/logs`

## 9. Editor chat and patching
### POST `/api/projects/:projectId/editor/chat`
### GET `/api/projects/:projectId/patches/:patchId`
### POST `/api/projects/:projectId/patches/:patchId/apply`

## 10. Deployment
### POST `/api/projects/:projectId/git/connect`
### POST `/api/projects/:projectId/git/commit`
### POST `/api/projects/:projectId/deploy/vercel`

## Error model
```json
{
  "error": {
    "code": "string_code",
    "message": "Human-readable message",
    "details": {}
  }
}
```
