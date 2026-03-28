# 08_CAPABILITY_GATE_DECISION_MATRIX.md

## Inputs
- wantsDatabase
- wantsAuth
- wantsAI
- externalCloudIntegrations[]
- selectedAIProviders[]

## Output decisions

| DB | Auth | AI | Allowed? | Generated App Backend Guidance | Secrets Needed |
|----|------|----|----------|--------------------------------|----------------|
| F  | F    | F  | Yes      | Frontend-only app             | No             |
| T  | F    | F  | Yes      | Supabase DB optional          | Maybe          |
| F  | T    | F  | Yes      | Supabase Auth optional        | Maybe          |
| T  | T    | F  | Yes      | Supabase DB/Auth/Storage      | Maybe          |
| F  | F    | T  | Yes      | No DB/Auth required           | Yes            |
| T  | F    | T  | Yes      | Supabase DB + AI              | Yes            |
| F  | T    | T  | Yes      | Supabase Auth + AI            | Yes            |
| T  | T    | T  | Yes      | Supabase DB/Auth/Storage + AI | Yes            |

## External cloud integration rule
If user selects external managed services:
- allowed only if not installed inside sandbox
- requires secure credential intake if credentials are needed

## User messaging requirements
Must tell user:
- current built-in managed generated-app support is Supabase DB/Auth/Storage
- external cloud services can be integrated through AI assistance
- secrets are encrypted and securely stored
