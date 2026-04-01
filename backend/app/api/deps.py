from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
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
AppSettings = Annotated[Settings, Depends(get_settings)]
