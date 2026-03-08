"""
Supabase JWT authentication middleware for FastAPI.
Validates tokens issued by Supabase Auth and extracts user info.
"""
import os
import httpx
from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models import get_db, User
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

security = HTTPBearer(auto_error=False)


async def _validate_token_via_supabase(token: str) -> dict | None:
    """Validate a Supabase access token by calling the /auth/v1/user endpoint."""
    try:
        try:
            import certifi
            ssl_verify = certifi.where()
        except Exception:
            ssl_verify = False

        async with httpx.AsyncClient(verify=ssl_verify, http2=False) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_ANON_KEY,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "sub": data["id"],
                    "email": data.get("email", ""),
                }
            else:
                print(f"[auth] Supabase validation failed: status={resp.status_code}")
    except Exception as e:
        print(f"[auth] Supabase token validation error: {e}")
    return None


def _decode_jwt_local(token: str) -> dict | None:
    """Decode a Supabase JWT using the JWT secret (faster, no network call)."""
    if not SUPABASE_JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError:
        return None


async def _resolve_user(token: str) -> dict:
    """Validate the token and return user info dict with 'sub' and 'email'."""
    payload = _decode_jwt_local(token)
    if payload and payload.get("sub"):
        return {"sub": payload["sub"], "email": payload.get("email", "")}

    user_info = await _validate_token_via_supabase(token)
    if user_info:
        return user_info

    raise HTTPException(status_code=401, detail="Invalid or expired token")


def _ensure_user_in_db(db: Session, user_info: dict) -> User:
    """Create or update the user row in our DB to match Supabase auth."""
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
    """FastAPI dependency that extracts and validates the Supabase user from Bearer token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_info = await _resolve_user(credentials.credentials)
    return _ensure_user_in_db(db, user_info)


async def get_current_user_ws(websocket: WebSocket, db: Session) -> User | None:
    """Extract user from WebSocket query param or first message. Returns None if no auth."""
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
    """Like get_current_user but returns None instead of raising 401."""
    if not credentials:
        return None
    try:
        user_info = await _resolve_user(credentials.credentials)
        return _ensure_user_in_db(db, user_info)
    except HTTPException:
        return None
