# 06_AGENT_IO_SCHEMAS.md

## Common input schema
```json
{
  "projectId": "uuid|null",
  "workspaceId": "uuid",
  "userId": "uuid",
  "sourceIdeaId": "uuid|null",
  "prompt": "string|null",
  "artifacts": {
    "executive": null,
    "prd": null,
    "architecture": null,
    "design": null
  },
  "constraints": {
    "platformCoreUsesNhost": true,
    "generatedAppSupabaseOptional": true,
    "sandboxHeavyBackendsBlocked": true
  }
}
```

## CEO output
```json
{
  "agent": "CEO",
  "summary": "string",
  "marketOpportunity": "string",
  "strategicDirection": "string",
  "risks": ["string"]
}
```

## CTO output
```json
{
  "agent": "CTO",
  "summary": "string",
  "architectureDirection": "string",
  "stackNotes": ["string"],
  "runtimeConcerns": ["string"]
}
```

## CDO output
```json
{
  "agent": "CDO",
  "summary": "string",
  "designDirection": "string",
  "modeRecommendation": "string",
  "styleRecommendation": "string"
}
```

## Executive Synthesizer output
```json
{
  "summary": "string",
  "recommendedDirection": "string",
  "decisionLog": [
    {"topic":"pricing","outcome":"..."}
  ]
}
```

## Design compiler output
```json
{
  "mode": "saas_dashboard",
  "style": "industrial_command",
  "pages": [],
  "components": [],
  "tokens": {},
  "htmlPreviews": []
}
```

## Patch validator output
```json
{
  "patchId": "uuid",
  "syntaxOk": true,
  "dependencyOk": true,
  "runtimeOk": true,
  "policyOk": true,
  "riskLevel": "low|medium|high",
  "notes": []
}
```
