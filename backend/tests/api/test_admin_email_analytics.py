"""Tests for GET /api/v1/admin/email/analytics (Phase 5 PR 1)."""

from datetime import datetime, timedelta, timezone

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
    from datetime import datetime as dt
    from datetime import timedelta as td
    from datetime import timezone as tz

    import jwt

    token = jwt.encode(
        {
            "sub": user_id,
            "iat": dt.now(tz.utc),
            "exp": dt.now(tz.utc) + td(days=30),
        },
        SECRET,
        algorithm="HS256",
    )
    return {"auth_session": token}


def _make_admin(db_session):
    """Make local-user an admin."""
    from app.core.ai_models import User

    async def _inner():
        user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
        user.is_admin = True
        await db_session.commit()

    return _inner


@pytest.mark.asyncio(loop_scope="function")
async def test_email_analytics_non_admin_returns_403(client):
    r = await client.get(
        "/api/v1/admin/email/analytics",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_email_analytics_admin_returns_200(client, db_session):
    await _make_admin(db_session)()

    r = await client.get(
        "/api/v1/admin/email/analytics",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()
    assert "last_7_days" in data
    assert "by_variant" in data


@pytest.mark.asyncio(loop_scope="function")
async def test_email_analytics_counts_sent(client, db_session):
    from app.core.subscription_models import EmailDelivery

    await _make_admin(db_session)()

    # Seed deliveries within last 7 days
    now = datetime.now(timezone.utc)
    for i in range(3):
        db_session.add(
            EmailDelivery(
                user_id="local-user",
                email_type="weekly_briefing",
                resend_message_id=f"msg_{i}",
                status="sent",
                sent_at=now - timedelta(hours=i),
                subject_variant="A",
            )
        )
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/email/analytics",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["last_7_days"]["sent"] == 3


@pytest.mark.asyncio(loop_scope="function")
async def test_email_analytics_open_rates(client, db_session):
    from app.core.subscription_models import EmailDelivery

    await _make_admin(db_session)()

    now = datetime.now(timezone.utc)
    # 4 sent, 2 opened
    for i in range(4):
        opened = now - timedelta(hours=i) if i < 2 else None
        db_session.add(
            EmailDelivery(
                user_id="local-user",
                email_type="weekly_briefing",
                resend_message_id=f"open_{i}",
                status="sent",
                sent_at=now - timedelta(hours=i),
                subject_variant="A",
                email_opened_at=opened,
            )
        )
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/email/analytics",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["last_7_days"]["sent"] == 4
    assert data["last_7_days"]["opens"] == 2
    assert data["last_7_days"]["open_rate"] == 0.5


@pytest.mark.asyncio(loop_scope="function")
async def test_email_analytics_by_variant(client, db_session):
    from app.core.subscription_models import EmailDelivery

    await _make_admin(db_session)()

    now = datetime.now(timezone.utc)
    # 2 A (1 open), 2 B (2 open)
    variants = [("A", True), ("A", False), ("B", True), ("B", True)]
    for i, (variant, opened) in enumerate(variants):
        opened_at = now - timedelta(hours=i) if opened else None
        db_session.add(
            EmailDelivery(
                user_id="local-user",
                email_type="weekly_briefing",
                resend_message_id=f"var_{i}",
                status="sent",
                sent_at=now - timedelta(hours=i),
                subject_variant=variant,
                email_opened_at=opened_at,
            )
        )
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/email/analytics",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()

    assert "A" in data["by_variant"]
    assert data["by_variant"]["A"]["sent"] == 2
    assert data["by_variant"]["A"]["opens"] == 1
    assert data["by_variant"]["A"]["open_rate"] == 0.5

    assert "B" in data["by_variant"]
    assert data["by_variant"]["B"]["sent"] == 2
    assert data["by_variant"]["B"]["opens"] == 2
    assert data["by_variant"]["B"]["open_rate"] == 1.0


@pytest.mark.asyncio(loop_scope="function")
async def test_email_analytics_click_rates(client, db_session):
    from app.core.subscription_models import EmailDelivery

    await _make_admin(db_session)()

    now = datetime.now(timezone.utc)
    # 5 sent, 1 click
    for i in range(5):
        clicked_at = now - timedelta(hours=i) if i == 0 else None
        db_session.add(
            EmailDelivery(
                user_id="local-user",
                email_type="weekly_briefing",
                resend_message_id=f"click_{i}",
                status="sent",
                sent_at=now - timedelta(hours=i),
                subject_variant="A",
                email_clicked_at=clicked_at,
            )
        )
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/email/analytics",
        cookies=_make_session_cookie("local-user"),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["last_7_days"]["sent"] == 5
    assert data["last_7_days"]["clicks"] == 1
    assert data["last_7_days"]["click_rate"] == 0.2
