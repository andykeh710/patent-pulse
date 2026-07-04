"""Tests for GET /api/v1/admin/billing/health (Phase 4 PR 1)."""

import pytest
from sqlalchemy import select

SECRET = "test-secret-key-for-tests"


@pytest.fixture(autouse=True, scope="session")
def _patch_settings():
    from app.config import settings as global_settings

    global_settings.auth_secret_key = SECRET
    global_settings.resend_api_key = "re_test"
    global_settings.email_from_address = "test@example.com"
    global_settings.email_dev_recipient = "dev@example.com"


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
async def test_billing_health_non_admin_returns_403(client):
    """Non-admin user cannot access billing health."""
    r = await client.get(
        "/api/v1/admin/billing/health",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_billing_health_admin_returns_200(client, db_session):
    """Admin can access billing health."""
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/billing/health",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200


@pytest.mark.asyncio(loop_scope="function")
async def test_billing_health_returns_expected_shape(client, db_session):
    """Response has expected keys and types."""
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/billing/health",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    # Required top-level fields
    assert "mode" in data
    assert data["mode"] in ("test", "live")
    assert isinstance(data["webhook_secret_set"], bool)
    assert isinstance(data["stripe_api_key_configured"], bool)
    assert "test_key_in_use" in data
    assert "live_key_in_use" in data

    # Subscriptions breakdown
    subs = data["subscriptions"]
    assert isinstance(subs, dict)
    for field in ("active", "free", "basic", "lifetime", "enterprise"):
        assert field in subs, f"Missing subscription field: {field}"
        assert isinstance(subs[field], int)

    # Recent activity
    assert isinstance(data["recent_webhook_activity_24h"], int)


@pytest.mark.asyncio(loop_scope="function")
async def test_billing_health_no_secret_leak(client, db_session):
    """Response must not contain raw API keys or secrets."""
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/billing/health",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    body = str(data)
    assert "sk_test_" not in body, "Body should not contain Stripe secret key"
    assert "sk_live_" not in body, "Body should not contain Stripe secret key"
    assert "whsec_" not in body, "Body should not contain webhook secret"


@pytest.mark.asyncio(loop_scope="function")
async def test_billing_health_subscription_counts_accurate(client, db_session):
    """Subscription counts match DB state."""
    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription

    # Make admin
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True

    # Seed subscriptions
    db_session.add_all(
        [
            BillingSubscription(user_id="local-user", tier="basic", status="active"),
            BillingSubscription(user_id="local-user-2", tier="enterprise", status="active"),
        ]
    )
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/billing/health",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    subs = r.json()["subscriptions"]

    assert subs["active"] == 2
    assert subs["basic"] == 1
    assert subs["enterprise"] == 1
    assert subs["free"] == 0
    assert subs["lifetime"] == 0
