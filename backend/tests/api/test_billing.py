"""Tests for billing API endpoints (Sprint 7). All Stripe calls mocked."""

import json
from unittest.mock import patch

import pytest

SECRET = "test-secret-key-for-tests"


@pytest.fixture(autouse=True, scope="session")
def _patch_settings():
    """Ensure the global settings object has auth_secret_key for API tests."""
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
async def test_checkout_session_no_auth_returns_401(client):
    r = await client.post("/api/v1/billing/checkout-session", json={"tier": "basic"})
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_get_subscription_returns_free(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()
    r = await client.get("/api/v1/billing/subscription", cookies=_make_session_cookie())
    assert r.status_code == 200
    assert r.json()["tier"] == "free"


@pytest.mark.asyncio(loop_scope="function")
async def test_checkout_session_valid_tier_returns_url(client):
    with patch("app.api.v1.billing.create_checkout_session") as mock_checkout:
        mock_checkout.return_value = {"url": "https://checkout.stripe.com/test", "id": "cs_test"}
        r = await client.post(
            "/api/v1/billing/checkout-session",
            json={"tier": "basic"},
            cookies=_make_session_cookie(),
        )
        assert r.status_code == 200
        assert "checkout.stripe.com" in r.json()["checkout_url"]


@pytest.mark.asyncio(loop_scope="function")
async def test_checkout_session_invalid_tier_returns_422(client):
    r = await client.post(
        "/api/v1/billing/checkout-session",
        json={"tier": "platinum"},
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_bad_signature_returns_400(client):
    r = await client.post(
        "/api/v1/billing/webhook",
        content=json.dumps({"type": "unknown"}).encode(),
        headers={"stripe-signature": "bad"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_checkout_subscription_creates_row(client, db_session):
    """checkout.session.completed (subscription mode) → BillingSubscription + user.tier=basic."""
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "mode": "subscription",
                "customer": "cus_test123",
                "subscription": "sub_test456",
                "metadata": {"user_id": "local-user", "tier": "basic"},
            }
        },
    }

    with patch("app.api.v1.billing.verify_webhook_signature") as mock_verify:
        mock_verify.return_value = event
        r = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event).encode(),
            headers={"stripe-signature": "sig_test"},
        )
        assert r.status_code == 200

    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription

    sub = (
        await db_session.execute(
            select(BillingSubscription).where(BillingSubscription.user_id == "local-user")
        )
    ).scalar_one_or_none()
    assert sub is not None
    assert sub.tier == "basic"
    assert sub.stripe_subscription_id == "sub_test456"

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    assert user.tier == "basic"


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_checkout_payment_creates_lifetime(client, db_session):
    """checkout.session.completed (payment mode) → tier=lifetime, payment_intent set."""
    from sqlalchemy import select

    from app.core.billing_models import BillingSubscription

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "mode": "payment",
                "customer": "cus_life",
                "payment_intent": "pi_life789",
                "metadata": {"user_id": "local-user", "tier": "lifetime"},
            }
        },
    }

    with patch("app.api.v1.billing.verify_webhook_signature") as mock_verify:
        mock_verify.return_value = event
        r = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event).encode(),
            headers={"stripe-signature": "sig"},
        )
        assert r.status_code == 200

    sub = (
        await db_session.execute(
            select(BillingSubscription).where(BillingSubscription.user_id == "local-user")
        )
    ).scalar_one_or_none()
    assert sub.tier == "lifetime"
    assert sub.stripe_payment_intent_id == "pi_life789"


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_subscription_deleted_flips_to_free(client, db_session):
    """customer.subscription.deleted → user.tier='free'."""
    from sqlalchemy import select

    from app.core.billing_models import BillingSubscription

    sub = BillingSubscription(
        user_id="local-user", tier="enterprise", stripe_subscription_id="sub_del", status="active"
    )
    db_session.add(sub)
    await db_session.commit()

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_del"}},
    }

    with patch("app.api.v1.billing.verify_webhook_signature") as mock_verify:
        mock_verify.return_value = event
        r = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event).encode(),
            headers={"stripe-signature": "sig"},
        )
        assert r.status_code == 200

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    assert user.tier == "free"
