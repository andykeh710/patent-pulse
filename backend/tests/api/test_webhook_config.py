"""Tests for webhook config + alerts endpoints (Phase 5 PR 2)."""
import pytest
from sqlalchemy import select

SECRET = "test-secret-key-for-tests"


@pytest.fixture(autouse=True, scope="session")
def _patch_settings():
    from app.config import settings as global_settings
    global_settings.auth_secret_key = SECRET


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", SECRET)


def _make_session_cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt
    token = jwt.encode(
        {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        },
        SECRET,
        algorithm="HS256",
    )
    return {"auth_session": token}


@pytest.mark.asyncio(loop_scope="function")
async def test_get_webhook_config_empty(client):
    """No config returns defaults."""
    r = await client.get(
        "/api/v1/account/webhook-config",
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["webhook_url"] is None
    assert data["enabled"] is False


@pytest.mark.asyncio(loop_scope="function")
async def test_set_webhook_config_lifetime(client, db_session):
    """Lifetime users can configure webhooks."""
    from app.core.ai_models import User

    user = (await db_session.execute(
        select(User).where(User.id == "local-user")
    )).scalar_one()
    user.tier = "lifetime"
    await db_session.commit()

    r = await client.post(
        "/api/v1/account/webhook-config",
        json={"webhook_url": "https://example.com/hook", "secret_key": "secret123", "enabled": True},
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["webhook_url"] == "https://example.com/hook"
    assert data["enabled"] is True

    # Verify secret not exposed
    assert "secret_key" not in data


@pytest.mark.asyncio(loop_scope="function")
async def test_set_webhook_config_free_returns_402(client, db_session):
    """Free tier users cannot configure webhooks."""
    from app.core.ai_models import User

    user = (await db_session.execute(
        select(User).where(User.id == "local-user")
    )).scalar_one()
    user.tier = "free"
    await db_session.commit()

    r = await client.post(
        "/api/v1/account/webhook-config",
        json={"webhook_url": "https://example.com/hook", "secret_key": "secret", "enabled": True},
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 402


@pytest.mark.asyncio(loop_scope="function")
async def test_list_alerts_empty(client):
    """No alerts returns empty list."""
    r = await client.get(
        "/api/v1/account/alerts",
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio(loop_scope="function")
async def test_list_alerts_with_data(client, db_session):
    """Alerts list returns expected shape."""
    from datetime import datetime, timezone

    from app.core.alert_models import Alert

    db_session.add(Alert(
        user_id="local-user",
        type="assignee_filed",
        payload={"title": "Test Alert"},
        status="sent",
        delivery_method="webhook",
    ))
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/alerts",
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["type"] == "assignee_filed"
    assert data[0]["status"] == "sent"
    assert data[0]["delivery_method"] == "webhook"


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_config_unauthorized(client):
    """No auth → 401."""
    r = await client.get("/api/v1/account/webhook-config")
    assert r.status_code == 401
