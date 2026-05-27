"""Sprint 7 cross-cutting integration test — full Free → Enterprise upgrade flow."""
import json

import pytest


def _cookie(user_id="local-user"):
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    return {"auth_session": jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        settings.auth_secret_key, algorithm="HS256",
    )}


@pytest.fixture(autouse=True)
def _ensure_secret(monkeypatch):
    from app.config import settings as g
    g.auth_secret_key = "test-secret-key-for-tests"


@pytest.mark.asyncio(loop_scope="function")
async def test_full_upgrade_flow(client, db_session):
    from app.core.ai_models import User
    from app.core.subscription_models import TopicSubscription
    from app.core.billing_models import BillingSubscription, APIKey
    from sqlalchemy import select
    from unittest.mock import patch

    # ── 1. Create Free user ──
    user = User(id="upgrade-test", email="upgrade@example.com", display_name="Upgrade", tier="free")
    db_session.add(user)
    await db_session.commit()

    ck = _cookie("upgrade-test")

    # Create a theme
    from app.core.theme_models import Theme
    theme = Theme(name="Integration Theme", is_active=True, cpc_prefixes=["G06F"], keywords=["test"])
    db_session.add(theme)
    await db_session.commit()

    # ── 2. Post 1st subscription → 201 ──
    r = await client.post("/api/v1/subscriptions", json={"theme_id": str(theme.id), "mode": "instant_alert"}, cookies=ck)
    assert r.status_code == 201, f"1st sub: {r.text}"

    # 2nd → 402 (quota: free max 1 topic)
    r = await client.post("/api/v1/subscriptions", json={"theme_id": str(theme.id), "mode": "weekly_digest"}, cookies=ck)
    assert r.status_code == 402, f"2nd sub: {r.status_code}"

    # ── 3. Simulate webhook checkout.session.completed → basic ──
    event = {"type": "checkout.session.completed", "data": {"object": {"mode": "subscription", "customer": "cus_upgrade", "subscription": "sub_upgrade", "metadata": {"user_id": "upgrade-test", "tier": "basic"}}}}
    with patch("app.api.v1.billing.verify_webhook_signature", return_value=event):
        r = await client.post("/api/v1/billing/webhook", content=json.dumps(event).encode(), headers={"stripe-signature": "sig"})
        assert r.status_code == 200

    # ── 4. Verify tier=basic + billing row ──
    await db_session.refresh(user)
    assert user.tier == "basic"
    billing = (await db_session.execute(select(BillingSubscription).where(BillingSubscription.user_id == "upgrade-test"))).scalar_one()
    assert billing.tier == "basic"

    # ── 5. 3rd subscription → 201 (unlimited) ──
    r = await client.post("/api/v1/subscriptions", json={"theme_id": str(theme.id), "mode": "weekly_digest"}, cookies=ck)
    assert r.status_code == 201

    # ── 6. API keys → 402 (basic doesn't get API) ──
    r = await client.post("/api/v1/account/api-keys", json={}, cookies=ck)
    assert r.status_code == 402

    # ── 7. Upgrade to enterprise via webhook ──
    event2 = {"type": "checkout.session.completed", "data": {"object": {"mode": "subscription", "customer": "cus_upgrade", "subscription": "sub_enterprise", "metadata": {"user_id": "upgrade-test", "tier": "enterprise"}}}}
    with patch("app.api.v1.billing.verify_webhook_signature", return_value=event2):
        r = await client.post("/api/v1/billing/webhook", content=json.dumps(event2).encode(), headers={"stripe-signature": "sig"})
        assert r.status_code == 200

    await db_session.refresh(user)
    assert user.tier == "enterprise"

    # ── 8. Create API key → 201 ──
    r = await client.post("/api/v1/account/api-keys", json={"name": "Integration Key"}, cookies=ck)
    assert r.status_code == 200  # default FastAPI response
    raw_token = r.json()["raw_token"]
    assert raw_token.startswith("pp_live_")

    # ── 9. Verify API key authenticates ──
    from app.auth.api_keys import authenticate_api_key
    authed_user = await authenticate_api_key(db_session, raw_token)
    assert authed_user is not None
    assert authed_user.id == "upgrade-test"

    # ── 10. CSV export → 200 ──
    r = await client.get("/api/v1/exports/expiry.csv", cookies=ck)
    assert r.status_code == 200
    assert "doc_id" in r.text
