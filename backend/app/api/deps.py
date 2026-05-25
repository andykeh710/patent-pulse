from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Cookie, Depends
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
    from fastapi import HTTPException
    import jwt as _jwt
    from sqlalchemy import select
    from app.core.ai_models import User

    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = _jwt.decode(
            auth_session, settings.auth_secret_key, algorithms=["HS256"]
        )
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
AppSettings = Annotated[Settings, Depends(get_settings)]
