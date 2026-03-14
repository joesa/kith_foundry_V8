"""
Nhost JWT authentication middleware for FastAPI.
Validates tokens via Nhost Auth /token/verify or JWKS.
"""
import os
import httpx
from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models import get_db, User
from datetime import datetime

load_dotenv()

NHOST_AUTH_URL = os.getenv("NHOST_AUTH_URL", "").rstrip("/")
NHOST_GRAPHQL_URL = os.getenv("NHOST_GRAPHQL_URL", "").rstrip("/")
NHOST_ADMIN_SECRET = os.getenv("NHOST_ADMIN_SECRET", "")
NHOST_JWT_SECRET = os.getenv("NHOST_JWT_SECRET", "")  # optional HS256 secret

security = HTTPBearer(auto_error=False)

# Cache JWKS keys to avoid fetching on every request
_jwks_cache: list[dict] = []


async def _get_jwks() -> list[dict]:
    """Fetch and cache JWKS keys from Nhost (with retry for transient DNS errors)."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    jwks_url = f"{NHOST_AUTH_URL}/.well-known/jwks.json"
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(http2=False) as client:
                resp = await client.get(jwks_url, timeout=10)
                if resp.status_code == 200:
                    _jwks_cache = resp.json().get("keys", [])
                    print(f"[auth] JWKS loaded: {len(_jwks_cache)} key(s)")
                    return _jwks_cache
                print(f"[auth] JWKS fetch failed: {resp.status_code} {jwks_url}")
        except Exception as e:
            print(f"[auth] JWKS fetch error (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                import asyncio
                await asyncio.sleep(2)
    return []


async def _validate_token_via_nhost_user(token: str) -> dict | None:
    """Validate token via GET /user — the correct Nhost v2 endpoint (with retry)."""
    if not NHOST_AUTH_URL:
        return None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(http2=False) as client:
                resp = await client.get(
                    f"{NHOST_AUTH_URL}/user",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"sub": data.get("id"), "email": data.get("email", "")}
                print(f"[auth] Nhost /user returned {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            print(f"[auth] Nhost /user error (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                import asyncio
                await asyncio.sleep(2)
    return None


def _decode_jwt_hs256(token: str) -> dict | None:
    """Decode Nhost JWT using HS256 symmetric secret (NHOST_JWT_SECRET)."""
    if not NHOST_JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token, NHOST_JWT_SECRET, algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return payload
    except Exception as e:
        print(f"[auth] HS256 decode error: {e}")
    return None


async def _decode_jwt_rs256(token: str) -> dict | None:
    """Decode Nhost JWT using RS256 JWKS (async)."""
    try:
        keys = await _get_jwks()
        if not keys:
            return None
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        key = next((k for k in keys if k.get("kid") == kid), keys[0] if keys else None)
        if not key:
            return None
        public_key = jwk.construct(key)
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"],
            options={"verify_aud": False}
        )
        return payload
    except Exception as e:
        print(f"[auth] RS256 decode error: {e}")
    return None


async def _resolve_user(token: str) -> dict:
    """Validate token and return user info dict with 'sub' and 'email'."""

    def _email_from_payload(p: dict) -> str:
        return (
            p.get("email")
            or p.get("https://hasura.io/jwt/claims", {}).get("x-hasura-user-email", "")
        )

    # 1. Try HS256 (Nhost default) if NHOST_JWT_SECRET is set
    payload = _decode_jwt_hs256(token)
    if payload and payload.get("sub"):
        return {"sub": payload["sub"], "email": _email_from_payload(payload)}

    # 2. Try RS256 via JWKS
    payload = await _decode_jwt_rs256(token)
    if payload and payload.get("sub"):
        return {"sub": payload["sub"], "email": _email_from_payload(payload)}

    # 3. Fall back to Nhost /user endpoint (always works if token is valid)
    user_info = await _validate_token_via_nhost_user(token)
    if user_info and user_info.get("sub"):
        return user_info

    raise HTTPException(status_code=401, detail="Invalid or expired token")


def _ensure_user_in_db(db: Session, user_info: dict) -> User:
    """Create or update user row to match Nhost auth."""
    user = db.query(User).filter(User.id == user_info["sub"]).first()
    if not user:
        user = User(
            id=user_info["sub"],
            email=user_info["email"],
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.last_login = datetime.utcnow()
        if user_info.get("email") and user.email != user_info["email"]:
            user.email = user_info["email"]
        db.commit()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: validate Nhost user from Bearer token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_info = await _resolve_user(credentials.credentials)
    return _ensure_user_in_db(db, user_info)


async def get_current_user_ws(websocket: WebSocket, db: Session) -> User | None:
    """Extract user from WebSocket query param."""
    token = websocket.query_params.get("token")
    if not token:
        print("[auth] WS auth failed: no token in query params")
        return None
    try:
        user_info = await _resolve_user(token)
        return _ensure_user_in_db(db, user_info)
    except HTTPException as e:
        print(f"[auth] WS auth failed: {e.detail}")
        return None


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of 401."""
    if not credentials:
        return None
    try:
        user_info = await _resolve_user(credentials.credentials)
        return _ensure_user_in_db(db, user_info)
    except HTTPException:
        return None
