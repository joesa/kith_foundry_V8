# Secret Management and Backend Capability Architecture (v10)

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

## Secret storage strategy
Preferred strategy:
- platform-controlled encrypted secret vault
- AES-256-GCM encryption
- trusted backend-only decryption
- ephemeral runtime injection when needed

## UX emphasis
When presenting this to users, explain that:
- secret handling is not an afterthought
- specialized security and infrastructure agents govern credential handling
- credentials are collected securely, encrypted, audited, and handled through controlled runtime paths
