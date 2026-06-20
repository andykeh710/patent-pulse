"""V3.5: Source health admin endpoint tests."""

import pytest


def _admin_cookie(user_id: str) -> dict:
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
async def test_source_health_requires_admin(client, db_session, monkeypatch):
    """Source health endpoint rejects non-admin users."""
    from sqlalchemy import select

    from app.core.ai_models import User

    monkeypatch.setattr("app.api.v1.auth.settings.admin_emails", "")
    await client.post(
        "/api/v1/auth/request-link", json={"email": "normal@example.com"}
    )
    user = (
        await db_session.execute(
            select(User).where(User.email == "normal@example.com")
        )
    ).scalar_one()

    r = await client.get(
        "/api/v1/admin/source-health", cookies=_admin_cookie(user.id)
    )
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_source_health_returns_data_for_admin(client, db_session, monkeypatch):
    """Admin users get source health data."""
    from sqlalchemy import select

    from app.core.ai_models import User

    # Create admin user
    monkeypatch.setattr(
        "app.api.v1.auth.settings.admin_emails", "admin@example.com"
    )
    await client.post(
        "/api/v1/auth/request-link", json={"email": "admin@example.com"}
    )
    user = (
        await db_session.execute(
            select(User).where(User.email == "admin@example.com")
        )
    ).scalar_one()

    r = await client.get(
        "/api/v1/admin/source-health", cookies=_admin_cookie(user.id)
    )
    assert r.status_code == 200
    data = r.json()
    assert "total_patents" in data
    assert "providers" in data
    assert "source_lag_days" in data


@pytest.mark.asyncio(loop_scope="function")
async def test_source_fetches_requires_admin(client, db_session, monkeypatch):
    """Source fetches endpoint rejects non-admin users."""
    from sqlalchemy import select

    from app.core.ai_models import User

    monkeypatch.setattr("app.api.v1.auth.settings.admin_emails", "")
    await client.post(
        "/api/v1/auth/request-link", json={"email": "plain@example.com"}
    )
    user = (
        await db_session.execute(
            select(User).where(User.email == "plain@example.com")
        )
    ).scalar_one()

    r = await client.get(
        "/api/v1/admin/source-fetches", cookies=_admin_cookie(user.id)
    )
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_retry_grant_week_requires_admin(client, db_session, monkeypatch):
    """Retry endpoint rejects non-admin users."""
    from sqlalchemy import select

    from app.core.ai_models import User

    monkeypatch.setattr("app.api.v1.auth.settings.admin_emails", "")
    await client.post(
        "/api/v1/auth/request-link", json={"email": "plain@example.com"}
    )
    user = (
        await db_session.execute(
            select(User).where(User.email == "plain@example.com")
        )
    ).scalar_one()

    r = await client.post(
        "/api/v1/admin/ingestion/retry-grant-week",
        json={"issue_date": "2026-06-17"},
        cookies=_admin_cookie(user.id),
    )
    assert r.status_code == 403
