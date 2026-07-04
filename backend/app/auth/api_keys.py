"""API key management for Enterprise tier (Sprint 7).

Keys are stored hashed (SHA-256). Raw tokens are shown once at creation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import User
from app.core.billing_models import APIKey


def generate_api_key() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Use secrets.token_urlsafe(32)."""
    raw = "pp_live_" + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw)


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def authenticate_api_key(
    session: AsyncSession,
    raw_token: str,
) -> User | None:
    """Look up and validate an API key. Returns User or None.

    Checks key_hash exists, revoked_at IS NULL, then updates last_used_at.
    """
    key_hash = hash_api_key(raw_token)
    key_row = (
        await session.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not key_row:
        return None

    key_row.last_used_at = datetime.now(timezone.utc)
    await session.commit()

    user = (
        await session.execute(select(User).where(User.id == key_row.user_id))
    ).scalar_one_or_none()

    return user
