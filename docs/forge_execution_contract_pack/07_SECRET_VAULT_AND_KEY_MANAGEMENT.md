# 07_SECRET_VAULT_AND_KEY_MANAGEMENT.md

## Encryption standard
- AES-256-GCM
- per-secret random IV
- auth tag persisted
- additional authenticated data may include scope metadata
- plaintext exists only during secure intake and secure runtime decryption

## Approved storage locations
### Approved
- platform secret vault in Nhost-backed control plane storage
- ephemeral runtime injection into Fly sandbox
- backend proxy use where browser should never handle provider key

### Disallowed
- browser localStorage
- sessionStorage for raw long-lived secrets
- plaintext files committed to repo
- plaintext build logs

## Runtime injection modes
- `ephemeral_env`: injected into sandbox runtime only for active build/run need
- `backend_proxy`: provider requests routed through backend service that uses secret server-side

## Access control
- only authorized backend services may decrypt
- every runtime use generates audit event
- revoke immediately blocks future runtime injection

## Rotation flow
1. collect new secret securely
2. encrypt new secret
3. persist new row or rotated version
4. mark prior secret rotated/revoked
5. record audit event
