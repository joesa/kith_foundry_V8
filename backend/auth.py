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
        security,
    )
else:
    from auth_supabase import (
        get_current_user,
        get_current_user_ws,
        get_optional_user,
        security,
    )

__all__ = ["get_current_user", "get_current_user_ws", "get_optional_user", "security"]
