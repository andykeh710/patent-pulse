"""Tests for magic-link auth flow."""
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.magic_link import (
    _compute_token_hash,
    create_token_for_email,
    generate_token,
    verify_token,
)


def test_generate_token_produces_raw_and_hash():
    raw, h = generate_token()
    assert len(raw) > 30
    assert len(h) == 64  # hexdigest
    assert _compute_token_hash(raw) == h


def test_generate_token_is_unique():
    tokens = {generate_token()[0] for _ in range(10)}
    assert len(tokens) == 10


@pytest.mark.asyncio(loop_scope="function")
async def test_create_and_verify_token(db_session):
    raw, h = await create_token_for_email(db_session, "local-user", "test@example.com")
    assert h

    row = await verify_token(db_session, raw)
    assert row is not None
    assert row.user_id == "local-user"
    assert row.consumed_at is not None


@pytest.mark.asyncio(loop_scope="function")
async def test_verify_consumed_token_fails(db_session):
    raw, _ = await create_token_for_email(db_session, "local-user", "test@example.com")
    row1 = await verify_token(db_session, raw)
    assert row1 is not None

    row2 = await verify_token(db_session, raw)
    assert row2 is None


@pytest.mark.asyncio(loop_scope="function")
async def test_verify_expired_token_fails(db_session):
    raw, h = generate_token()
    from app.core.subscription_models import AuthMagicLinkToken
    token_row = AuthMagicLinkToken(
        token_hash=h,
        user_id="local-user",
        email="test@example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(token_row)
    await db_session.commit()

    row = await verify_token(db_session, raw)
    assert row is None


@pytest.mark.asyncio(loop_scope="function")
async def test_verify_unknown_token_fails(db_session):
    row = await verify_token(db_session, "nonexistent-token")
    assert row is None
