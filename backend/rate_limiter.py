"""Shared rate-limiter instance used by main.py and all API routers.

Keeping this in a separate module avoids circular imports: main.py imports the
routers, and the routers need to reference the same ``limiter`` object that is
attached to ``app.state.limiter``.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_rate_key(request: Request) -> str:
    """Rate-limit key: authenticated user ID (JWT sub) or remote IP as fallback."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
        try:
            from auth_supabase import _decode_jwt_local
            payload = _decode_jwt_local(token)
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


# 300 req/min default; LLM-triggering endpoints override with 30/minute.
limiter = Limiter(key_func=_user_rate_key, default_limits=["300/minute"])
