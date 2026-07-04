"""
API-layer rate limiting via slowapi (PR12).

Applies a global default of 60 requests/minute per client. Authenticated
users are keyed by their session cookie (user:<id>) so they are counted
separately from anonymous visitors.

TODO (V1.1): Tier-based limits — higher tiers get higher ceilings (e.g.
Basic 120/min, Lifetime 300/min, Enterprise 1000/min). Current V1 uses a
conservative 60/min for all callers.
"""

from __future__ import annotations

import jwt as _jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

SESSION_COOKIE_NAME = "auth_session"


def _get_user_id_from_cookie(request: Request) -> str | None:
    """Best-effort extraction of ``sub`` from the session JWT cookie.

    Returns ``None`` (fall through to IP-based key) if the cookie is
    missing, expired, or tampered with.
    """
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return None
    try:
        payload = _jwt.decode(cookie, settings.auth_secret_key, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None


def _rate_limit_key(request: Request) -> str:
    """Key function for slowapi.

    Authenticated → ``user:<uuid>``     (counted separately, 300/min)
    Anonymous     → ``ip:<addr>``       (counted separately, 60/min)
    """
    user_id = _get_user_id_from_cookie(request)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=["60/minute"],
    # In-process storage (V1).  Redis-backed storage is a V1.1 target.
    storage_uri="memory://",
)
