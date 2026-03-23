"""
Auth middleware for FastAPI.
Uses Nhost when USE_NHOST=1, otherwise Supabase.
"""
import os
from dotenv import load_dotenv
load_dotenv()

if os.getenv("USE_NHOST") == "1":
    from auth_nhost import (
        get_current_user,
        get_current_user_ws,
        get_optional_user,
        _resolve_user,
        _ensure_user_in_db,
        security,
    )
else:
    from auth_supabase import (
        get_current_user,
        get_current_user_ws,
        get_optional_user,
        _resolve_user,
        _ensure_user_in_db,
        security,
    )


async def resolve_user_from_token(token, db):
    user_info = await _resolve_user(token)
    return _ensure_user_in_db(db, user_info)


__all__ = [
    "get_current_user",
    "get_current_user_ws",
    "get_optional_user",
    "resolve_user_from_token",
    "security",
]
