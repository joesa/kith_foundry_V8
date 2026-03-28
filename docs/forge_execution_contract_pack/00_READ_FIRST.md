# 00_READ_FIRST.md

This is the strict execution contract pack for Forge.

## Objective
Reduce ambiguity so Cursor, Antigravity, or an engineering team can implement the system with minimal interpretation drift.

## Critical invariants
- Platform core uses Nhost PostgreSQL and Nhost Auth.
- Platform core does not use Supabase.
- Generated apps may optionally use Supabase DB/Auth/Storage if selected.
- External cloud services are allowed only as cloud-managed integrations, never as locally installed sandbox infrastructure.
- All persisted secrets must use AES-256-GCM encryption.
- Raw API keys must never be persisted in browser localStorage.
- Saved-only ideas are soft-held for exactly 7 days.
- Ideas in active product/build states are reserved.
- Agent collaboration must remain visible in the product experience.
