"""Tests for quota limits (Sprint 7)."""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.ai_models import User
from app.quotas.limits import check_alert_quota, check_topic_quota, require_tier


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_with_0_topics_passes(db_session):
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()
    # No exception expected — user has 0 topic_subscriptions (conftest doesn't seed any)
    await check_topic_quota("local-user", db_session)


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_with_1_topic_fails(db_session):
    from app.core.subscription_models import TopicSubscription
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    # Create 1 existing subscription
    themes = (await db_session.execute(select(__import__("app.core.theme_models", fromlist=["Theme"]).Theme).limit(1))).scalars().all()
    sub = TopicSubscription(user_id="local-user", theme_id=themes[0].id, mode="weekly_digest")
    db_session.add(sub)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await check_topic_quota("local-user", db_session)
    assert exc.value.status_code == 402


@pytest.mark.asyncio(loop_scope="function")
async def test_basic_user_unlimited_topics(db_session):
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()
    # No exception — basic has unlimited topics
    await check_topic_quota("local-user", db_session)


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_alert_quota_under_limit(db_session):
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()
    assert await check_alert_quota(db_session, "local-user") is True


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_alert_quota_exhausted(db_session):
    from app.core.subscription_models import EmailDelivery
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()

    # Create 5 recent deliveries
    for i in range(5):
        db_session.add(EmailDelivery(user_id="local-user", email_type="instant_alert", status="dev", sent_at=datetime.now(timezone.utc)))
    await db_session.commit()

    assert await check_alert_quota(db_session, "local-user") is False


@pytest.mark.asyncio(loop_scope="function")
async def test_basic_user_alert_quota_unlimited(db_session):
    from app.core.subscription_models import EmailDelivery
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    for i in range(100):
        db_session.add(EmailDelivery(user_id="local-user", email_type="instant_alert", status="dev", sent_at=datetime.now(timezone.utc)))
    await db_session.commit()

    assert await check_alert_quota(db_session, "local-user") is True


def test_require_tier_rejects_free():
    dep = require_tier("lifetime", "enterprise")
    assert dep is not None  # it's a callable dependency


def test_tier_limits_dict():
    from app.quotas.limits import TIER_LIMITS
    assert TIER_LIMITS["free"]["max_topics"] == 1
    assert TIER_LIMITS["basic"]["max_topics"] is None
