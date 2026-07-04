from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, settings
from app.database import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async for session in get_session():
        yield session


def get_settings() -> Settings:
    """Dependency for settings."""
    return settings


DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── Sprint 6: magic-link auth ───────────────────────────────────────

SESSION_COOKIE_NAME = "auth_session"


async def current_user(
    auth_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> str:
    """FastAPI dependency returning the authenticated user_id.

    Reads the 'auth_session' cookie, verifies the JWT, and returns
    the user_id. Raises 401 if missing, expired, or invalid.
    """
    import jwt as _jwt
    from fastapi import HTTPException
    from sqlalchemy import select

    from app.core.ai_models import User

    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = _jwt.decode(auth_session, settings.auth_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
    except _jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user.id


async def current_user_optional(
    auth_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> str | None:
    """Like current_user but returns None instead of 401 on missing cookie."""
    if not auth_session:
        return None
    try:
        import jwt as _jwt

        payload = _jwt.decode(auth_session, settings.auth_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub", "")
        if not user_id:
            return None
    except Exception:
        return None

    from app.core.ai_models import User

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    return user.id if user else None


async def current_user_or_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(current_user_optional),
) -> str:
    """Authenticate via session cookie OR Bearer API key.

    Returns user_id. Raises 401 if neither is valid.
    """
    if user_id is not None:
        return user_id

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer pp_live_"):
        from app.auth.api_keys import authenticate_api_key

        user = await authenticate_api_key(db, auth_header[len("Bearer ") :])
        if user is not None:
            return user.id

    raise HTTPException(status_code=401, detail="Authentication required")


AppSettings = Annotated[Settings, Depends(get_settings)]
