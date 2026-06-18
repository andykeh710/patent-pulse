"""
Tests for L3 GDPR account deletion endpoint.
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select


def _cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings
    return {"auth_session": jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc),
         "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        settings.auth_secret_key, algorithm="HS256",
    )}


def _delete(client: AsyncClient, email: str, **kwargs):
    """Helper: httpx 0.27 AsyncClient.delete() doesn't accept json=."""
    return client.request(
        "DELETE",
        "/api/v1/account/me",
        content=json.dumps({"confirm_email": email}),
        headers={"Content-Type": "application/json"},
        **kwargs,
    )


# ── Auth guards ──────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_without_auth_returns_401(client: AsyncClient):
    r = await _delete(client, "x@x.com")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_wrong_email_returns_400(client: AsyncClient, db_session):
    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.email = "real@example.com"
    await db_session.commit()

    r = await _delete(client, "wrong@example.com", cookies=_cookie())
    assert r.status_code == 400


# ── Successful deletion ──────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_with_matching_email_returns_204(client: AsyncClient, db_session):
    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.email = "good@example.com"
    await db_session.commit()

    r = await _delete(client, "  Good@Example.com  ", cookies=_cookie())
    assert r.status_code == 204


# ── Post-deletion verification ───────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_user_row_gone_after_delete(client: AsyncClient, db_session):
    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.email = "vanish@example.com"
    await db_session.commit()

    r = await _delete(client, "vanish@example.com", cookies=_cookie())
    assert r.status_code == 204

    gone = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one_or_none()
    assert gone is None


@pytest.mark.asyncio(loop_scope="function")
async def test_email_deliveries_anonymized_not_deleted(client: AsyncClient, db_session):
    from uuid import uuid4

    from app.core.ai_models import User
    from app.core.subscription_models import EmailDelivery

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.email = "ed@example.com"
    await db_session.commit()

    delivery = EmailDelivery(
        id=uuid4(),
        user_id=user.id,
        email_type="instant_alert",
        status="delivered",
    )
    db_session.add(delivery)
    await db_session.commit()

    r = await _delete(client, "ed@example.com", cookies=_cookie())
    assert r.status_code == 204

    kept = (await db_session.execute(
        select(EmailDelivery).where(EmailDelivery.id == delivery.id)
    )).scalar_one_or_none()
    assert kept is not None, "email_deliveries row should be kept"
    assert kept.user_id is None, "user_id should be NULL after anonymization"


@pytest.mark.asyncio(loop_scope="function")
async def test_ai_runs_anonymized_not_deleted(client: AsyncClient, db_session):
    from uuid import uuid4

    from app.core.ai_models import AIRun, User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.email = "air@example.com"
    await db_session.commit()

    run = AIRun(
        id=uuid4(),
        task_type="test",
        run_mode="live",
        model="haiku",
        created_by=user.id,
    )
    db_session.add(run)
    await db_session.commit()

    r = await _delete(client, "air@example.com", cookies=_cookie())
    assert r.status_code == 204

    kept = (await db_session.execute(
        select(AIRun).where(AIRun.id == run.id)
    )).scalar_one_or_none()
    assert kept is not None, "ai_runs row should be kept"
    assert kept.created_by is None, "created_by should be NULL after anonymization"


@pytest.mark.asyncio(loop_scope="function")
async def test_subscriptions_cascaded_after_delete(client: AsyncClient, db_session):

    from app.core.ai_models import User
    from app.core.subscription_models import TopicSubscription
    from app.core.theme_models import Theme

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.email = "subs@example.com"
    await db_session.commit()

    theme = Theme(
        name="test-theme-cascade",
        is_active=True,
        cpc_prefixes=["G06F"],
        keywords=["test"],
        assignee_keywords=[],
    )
    db_session.add(theme)
    await db_session.flush()

    sub = TopicSubscription(
        user_id=user.id,
        theme_id=theme.id,
        mode="weekly_digest",
    )
    db_session.add(sub)
    await db_session.commit()

    sub_id = sub.id

    r = await _delete(client, "subs@example.com", cookies=_cookie())
    assert r.status_code == 204

    gone = (await db_session.execute(
        select(TopicSubscription).where(TopicSubscription.id == sub_id)
    )).scalar_one_or_none()
    assert gone is None, "subscriptions should cascade-delete"


@pytest.mark.asyncio(loop_scope="function")
async def test_email_preferences_are_loaded_for_authenticated_user(
    client: AsyncClient,
    db_session,
):
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.preferences = {
        "weekly_briefing_enabled": False,
        "instant_alerts_enabled": True,
    }
    await db_session.commit()

    response = await client.get(
        "/api/v1/account/email-preferences",
        cookies=_cookie(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "weekly_briefing_enabled": False,
        "instant_alerts_enabled": True,
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_email_preferences_update_persists_for_authenticated_user(
    client: AsyncClient,
    db_session,
):
    from app.core.ai_models import User

    response = await client.put(
        "/api/v1/account/email-preferences",
        json={"weekly_briefing_enabled": False},
        cookies=_cookie(),
    )

    assert response.status_code == 200
    assert response.json()["weekly_briefing_enabled"] is False

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    assert user.preferences["weekly_briefing_enabled"] is False


@pytest.mark.asyncio(loop_scope="function")
async def test_company_follow_uses_authenticated_user_id(
    client: AsyncClient,
    db_session,
):
    from app.core.ai_models import UserCompanyFollow

    response = await client.post(
        "/api/v1/account/companies",
        json={"company_name": "Acme Corp"},
        cookies=_cookie(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["company_normalized_name"] == "acme"

    follow = (
        await db_session.execute(
            select(UserCompanyFollow).where(
                UserCompanyFollow.user_id == "local-user",
                UserCompanyFollow.company_normalized_name == "acme",
            )
        )
    ).scalar_one_or_none()
    assert follow is not None
