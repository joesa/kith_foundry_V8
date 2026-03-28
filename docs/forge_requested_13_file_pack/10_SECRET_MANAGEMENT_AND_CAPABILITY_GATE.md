# 10_SECRET_MANAGEMENT_AND_CAPABILITY_GATE.md

## Capability gate
Before build starts, ask:
- Do you want database in the generated app?
- Do you want auth in the generated app?
- Do you want AI in the generated app?

The user can choose any combination or skip all and continue.

## Supported managed generated-app backend today
- Supabase Database
- Supabase Storage
- Supabase Auth

## External cloud services
Users may integrate:
- Cloudflare
- AWS
- GCP
- other managed DBs / Auth / APIs

Condition:
- must not be installed locally in sandbox
- credentials must be securely collected and stored

## Secret storage strategy
Preferred strategy:
- platform-controlled encrypted secret vault
- AES-256-GCM encryption
- trusted backend-only decryption
- ephemeral runtime injection when needed

## Rules
- never store raw API keys in browser localStorage
- never expose raw secrets in logs
- prefer backend proxy or ephemeral runtime injection
