"""
Magic-link authentication (Sprint 6).

Token flow:
  1. User POSTs email to /auth/request-link → we generate a 32-byte
     URL-safe token, store SHA-256(token) in auth_magic_link_tokens,
     email the raw token link.
  2. User clicks link → /auth/verify?token=... → we hash and look up.

Security:
  - Token hashed with SHA-256 + HMAC-style keyed hash (auth_secret_key).
  - 15-min expiry, single-use.
  - Always return 202 on request-link (no user-enumeration disclosure).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.core.subscription_models import AuthMagicLinkToken

logger = logging.getLogger(__name__)

TOKEN_BYTES = 32


def _compute_token_hash(raw_token: str) -> str:
    """HMAC-SHA256 the token with auth_secret_key as the key."""
    return hmac.new(
        settings.auth_secret_key.encode(),
        raw_token.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_token() -> tuple[str, str]:
    """Generate a magic-link token.

    Returns (raw_token, token_hash). Store token_hash; email raw_token.
    """
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    return raw, _compute_token_hash(raw)


async def create_token_for_email(
    session,
    user_id: str,
    email: str,
) -> tuple[str, str]:
    """Create an AuthMagicLinkToken row for a user.

    Returns (raw_token, token_hash).
    """
    raw, token_hash = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.magic_link_ttl_minutes
    )

    token_row = AuthMagicLinkToken(
        token_hash=token_hash,
        user_id=user_id,
        email=email,
        expires_at=expires_at,
    )
    session.add(token_row)
    await session.commit()

    return raw, token_hash


async def verify_token(session, raw_token: str) -> AuthMagicLinkToken | None:
    """Verify a magic-link token. Returns the row if valid, or None.

    On success: sets consumed_at and commits.
    """
    token_hash = _compute_token_hash(raw_token)

    from sqlalchemy import select
    result = await session.execute(
        select(AuthMagicLinkToken).where(
            AuthMagicLinkToken.token_hash == token_hash
        )
    )
    row = result.scalar_one_or_none()

    if not row:
        return None

    now = datetime.now(timezone.utc)

    if row.consumed_at is not None:
        return None  # already used

    if now > row.expires_at:
        return None  # expired

    # Consume.
    row.consumed_at = now
    await session.commit()

    return row
