"""Tests for GET /api/v1/account/usage (Phase 4 PR 3)."""

import pytest

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
async def test_usage_no_auth_returns_401(client):
    r = await client.get("/api/v1/account/usage")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_usage_returns_expected_shape_free(client, db_session):
    """Free tier user gets expected shape with limits."""
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/usage",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["tier"] == "free"
    assert "features" in data

    # Check required features
    for feat_name in ("views", "search", "themes", "companies", "chat"):
        feat = data["features"].get(feat_name)
        assert feat is not None, f"Missing feature: {feat_name}"
        assert "used" in feat
        assert isinstance(feat["used"], int)
        assert "limit" in feat
        assert "remaining" in feat
        assert "unlimited" in feat

    # Free tier: chat limit is 5
    assert data["features"]["chat"]["limit"] == 5
    assert data["features"]["chat"]["unlimited"] is False
    # Views/search should be unlimited
    assert data["features"]["views"]["unlimited"] is True
    assert data["features"]["search"]["unlimited"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_usage_basic_tier_has_higher_limits(client, db_session):
    """Basic tier gets 50 chat, unlimited themes/companies."""
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/usage",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["tier"] == "basic"
    assert data["features"]["chat"]["limit"] == 50
    assert data["features"]["chat"]["unlimited"] is False
    assert data["features"]["themes"]["unlimited"] is True
    assert data["features"]["companies"]["unlimited"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_usage_lifetime_unlimited_chat(client, db_session):
    """Lifetime tier gets unlimited chat."""
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "lifetime"
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/usage",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["tier"] == "lifetime"
    assert data["features"]["chat"]["unlimited"] is True
    assert data["features"]["chat"]["limit"] is None


@pytest.mark.asyncio(loop_scope="function")
async def test_usage_counts_themes(client, db_session):
    """Theme count reflects actual TopicSubscription rows."""
    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.subscription_models import TopicSubscription
    from app.core.theme_models import Theme

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()

    # Seed themes + subscriptions
    theme = Theme(name="AI/ML Test", is_active=True, cpc_prefixes=["G06N"])
    db_session.add(theme)
    await db_session.flush()

    sub = TopicSubscription(
        user_id="local-user",
        theme_id=theme.id,
        mode="weekly_digest",
    )
    db_session.add(sub)
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/usage",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["features"]["themes"]["used"] == 1
    assert data["features"]["themes"]["limit"] == 1
    assert data["features"]["themes"]["remaining"] == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_usage_counts_companies(client, db_session):
    """Company count reflects actual UserCompanyFollow rows."""
    from sqlalchemy import select

    from app.core.ai_models import User, UserCompanyFollow

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()

    follow = UserCompanyFollow(
        user_id="local-user",
        company_normalized_name="acme",
        display_name="Acme Corp",
    )
    db_session.add(follow)
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/usage",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["features"]["companies"]["used"] == 1
    assert data["features"]["companies"]["limit"] == 3
    assert data["features"]["companies"]["remaining"] == 2


@pytest.mark.asyncio(loop_scope="function")
async def test_usage_includes_renews_at(client, db_session):
    """renews_at is present when billing subscription has current_period_end."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    future = datetime.now(timezone.utc) + timedelta(days=30)
    billing = BillingSubscription(
        user_id="local-user",
        tier="basic",
        status="active",
        current_period_end=future,
    )
    db_session.add(billing)
    await db_session.commit()

    r = await client.get(
        "/api/v1/account/usage",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["renews_at"] is not None
    # Should be ISO 8601 format
    assert "T" in data["renews_at"]
