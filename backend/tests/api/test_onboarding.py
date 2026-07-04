"""Tests for onboarding API."""

import pytest
from httpx import AsyncClient

from app.core.ai_models import UserCompanyFollow


def _cookie(user_id="local-user"):
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
async def test_onboarding_status_not_onboarded(client: AsyncClient, db_session):
    r = await client.get("/api/v1/onboarding/status", cookies=_cookie())
    assert r.status_code == 200
    data = r.json()
    assert data["onboarded"] is False
    assert data["persona"] is None


@pytest.mark.asyncio(loop_scope="function")
async def test_onboarding_complete_updates_user(client: AsyncClient, db_session):
    r = await client.post(
        "/api/v1/onboarding/complete",
        json={"persona": "Founder", "industry_focus": "AI/ML", "interests_freetext": "LLM agents"},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    data = r.json()
    assert "suggested_companies" in data
    assert "suggested_themes" in data

    # Verify user was updated
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    assert user.persona == "Founder"
    assert user.industry_focus == "AI/ML"
    assert user.interests_freetext == "LLM agents"


@pytest.mark.asyncio(loop_scope="function")
async def test_onboarding_complete_no_auth(client: AsyncClient):
    r = await client.post(
        "/api/v1/onboarding/complete",
        json={"persona": "Founder", "industry_focus": "AI/ML", "interests_freetext": ""},
    )
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_onboarding_confirm_creates_follows(client: AsyncClient, db_session):
    # First complete step
    await client.post(
        "/api/v1/onboarding/complete",
        json={"persona": "Engineer", "industry_focus": "Robotics", "interests_freetext": ""},
        cookies=_cookie(),
    )

    # Confirm with a company id
    r = await client.post(
        "/api/v1/onboarding/confirm",
        json={"company_ids": ["Boston Dynamics"], "theme_ids": []},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Verify follow was created
    from sqlalchemy import select

    follows = (
        (
            await db_session.execute(
                select(UserCompanyFollow).where(UserCompanyFollow.user_id == "local-user")
            )
        )
        .scalars()
        .all()
    )
    assert len(follows) >= 1
    assert follows[0].company_normalized_name == "Boston Dynamics"

    # Verify onboarded_at was set
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    assert user.onboarded_at is not None

    # Verify status now shows onboarded
    r2 = await client.get("/api/v1/onboarding/status", cookies=_cookie())
    assert r2.json()["onboarded"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_onboarding_confirm_creates_subscriptions(client: AsyncClient, db_session):
    # Seed a theme
    from app.core.theme_models import Theme

    theme = Theme(
        name="Test Theme",
        description="A test theme",
        cpc_prefixes=["G06N"],
        is_active=True,
    )
    db_session.add(theme)
    await db_session.commit()
    theme_id = str(theme.id)

    await client.post(
        "/api/v1/onboarding/complete",
        json={"persona": "Researcher", "industry_focus": "AI/ML", "interests_freetext": ""},
        cookies=_cookie(),
    )

    r = await client.post(
        "/api/v1/onboarding/confirm",
        json={"company_ids": [], "theme_ids": [theme_id]},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    from sqlalchemy import select

    from app.core.subscription_models import TopicSubscription

    subs = (
        (
            await db_session.execute(
                select(TopicSubscription).where(TopicSubscription.user_id == "local-user")
            )
        )
        .scalars()
        .all()
    )
    assert len(subs) >= 1
    assert str(subs[0].theme_id) == theme_id
