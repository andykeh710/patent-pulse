"""P0 security: users.is_admin must default to false.

Previously every account (including magic-link signups) became an admin.
These tests lock in the safe default and the ADMIN_EMAILS allowlist behavior.
"""
import pytest
from sqlalchemy import select

from app.core.ai_models import User


def _cookie(user_id: str) -> dict:
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings

    return {
        "auth_session": jwt.encode(
            {
                "sub": user_id,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(days=30),
            },
            settings.auth_secret_key,
            algorithm="HS256",
        )
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_orm_user_defaults_to_non_admin(db_session):
    """A user created without an explicit is_admin is NOT an admin."""
    u = User(email="plain@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    assert u.is_admin is False


@pytest.mark.asyncio(loop_scope="function")
async def test_new_magic_link_user_is_not_admin(client, db_session, monkeypatch):
    """Signing up via magic link does not grant admin when allowlist is empty."""
    monkeypatch.setattr("app.api.v1.auth.settings.admin_emails", "")
    r = await client.post(
        "/api/v1/auth/request-link", json={"email": "newbie@example.com"}
    )
    assert r.status_code == 202
    user = (
        await db_session.execute(select(User).where(User.email == "newbie@example.com"))
    ).scalar_one()
    assert user.is_admin is False


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_endpoint_rejects_normal_user(client, db_session, monkeypatch):
    """A normal (non-allowlisted) signed-up user cannot reach admin endpoints."""
    monkeypatch.setattr("app.api.v1.auth.settings.admin_emails", "")
    await client.post("/api/v1/auth/request-link", json={"email": "normal@example.com"})
    user = (
        await db_session.execute(select(User).where(User.email == "normal@example.com"))
    ).scalar_one()

    r = await client.get("/api/v1/admin/email/analytics", cookies=_cookie(user.id))
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_allowlisted_email_is_admin(client, db_session, monkeypatch):
    """An ADMIN_EMAILS address is granted admin on signup and passes the gate."""
    monkeypatch.setattr(
        "app.api.v1.auth.settings.admin_emails", "boss@example.com, other@x.com"
    )
    await client.post("/api/v1/auth/request-link", json={"email": "boss@example.com"})
    user = (
        await db_session.execute(select(User).where(User.email == "boss@example.com"))
    ).scalar_one()
    assert user.is_admin is True

    r = await client.get("/api/v1/admin/email/analytics", cookies=_cookie(user.id))
    assert r.status_code == 200


@pytest.mark.asyncio(loop_scope="function")
async def test_allowlist_promotes_existing_non_admin_on_login(
    client, db_session, monkeypatch
):
    """A pre-existing non-admin is promoted when later added to the allowlist."""
    u = User(email="late@example.com", is_admin=False)
    db_session.add(u)
    await db_session.commit()

    monkeypatch.setattr("app.api.v1.auth.settings.admin_emails", "late@example.com")
    await client.post("/api/v1/auth/request-link", json={"email": "late@example.com"})
    await db_session.refresh(u)
    assert u.is_admin is True
