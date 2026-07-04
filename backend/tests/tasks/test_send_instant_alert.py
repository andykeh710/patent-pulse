"""Tests for instant alert task."""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.models import PatentPublication
from app.core.subscription_models import EmailDelivery, TopicSubscription
from app.core.theme_models import Theme


@pytest.mark.asyncio(loop_scope="function")
async def test_instant_alert_skips_below_min_score(db_session):
    from datetime import date

    patent = PatentPublication(
        doc_id="USPTO:skip-alert",
        title="Skip Alert Patent",
        office="USPTO",
        publication_number="USA001",
        assignees=["SkipCo"],
        cpc=["G06N"],
        filing_date=date(2024, 1, 1),
        publication_date=date(2025, 1, 1),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    theme = themes[0]

    sub = TopicSubscription(
        user_id="alert-skip-user", theme_id=theme.id, mode="instant_alert", min_score=70
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    from app.tasks.send_instant_alert import _send_instant_alert_async

    r = await _send_instant_alert_async(
        str(sub.id), str(patent.id), str(uuid.uuid4()), session=db_session
    )
    assert r["status"] == "skipped"


@pytest.mark.asyncio(loop_scope="function")
async def test_instant_alert_idempotent_within_hour(db_session):
    from datetime import date, datetime, timezone

    patent = PatentPublication(
        doc_id="USPTO:idem-alert",
        title="Idem Alert Patent",
        office="USPTO",
        publication_number="USA002",
        assignees=["IdemCo"],
        cpc=["G06N"],
        filing_date=date(2024, 1, 1),
        publication_date=date(2025, 1, 1),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    theme = themes[0]

    sub = TopicSubscription(
        user_id="alert-idem-user", theme_id=theme.id, mode="instant_alert", min_score=None
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    delivery = EmailDelivery(
        user_id="alert-idem-user",
        subscription_id=sub.id,
        email_type="instant_alert",
        status="dev",
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add(delivery)
    await db_session.commit()

    from app.tasks.send_instant_alert import _send_instant_alert_async

    with patch("app.email.sender.send_email", return_value={"status": "dev", "detail": "Logged"}):
        r = await _send_instant_alert_async(
            str(sub.id), str(patent.id), str(uuid.uuid4()), session=db_session
        )
        assert r["status"] == "skipped"


@pytest.mark.asyncio(loop_scope="function")
async def test_instant_alert_sends_email(db_session):
    from datetime import date

    patent = PatentPublication(
        doc_id="USPTO:happy-alert",
        title="Happy Alert Patent",
        office="USPTO",
        publication_number="USA003",
        assignees=["HappyCo"],
        cpc=["G06N"],
        filing_date=date(2024, 1, 1),
        publication_date=date(2025, 1, 1),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    theme = themes[0]

    sub = TopicSubscription(
        user_id="alert-happy-user", theme_id=theme.id, mode="instant_alert", min_score=None
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    from app.tasks.send_instant_alert import _send_instant_alert_async

    with patch("app.email.sender.send_email", return_value={"status": "dev", "detail": "Logged"}):
        r = await _send_instant_alert_async(
            str(sub.id), str(patent.id), str(uuid.uuid4()), session=db_session
        )
        assert r["status"] == "dev"
        await db_session.refresh(sub)
        assert sub.last_delivered_at is not None


@pytest.mark.asyncio(loop_scope="function")
async def test_hook_enqueues_per_subscription(db_session):
    from datetime import date

    patent = PatentPublication(
        doc_id="USPTO:hook-alert",
        title="Hook Alert Patent",
        office="USPTO",
        publication_number="USA004",
        assignees=["HookCo"],
        cpc=["G06N"],
        filing_date=date(2024, 1, 1),
        publication_date=date(2025, 1, 1),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    theme = themes[0]

    s1 = TopicSubscription(user_id="alert-hook-user-1", theme_id=theme.id, mode="instant_alert")
    s2 = TopicSubscription(user_id="alert-hook-user-2", theme_id=theme.id, mode="instant_alert")
    db_session.add_all([s1, s2])
    await db_session.commit()

    from app.tasks.theme_matcher import _enqueue_match_alerts

    with patch("app.tasks.send_instant_alert.send_instant_alert.delay") as mock_delay:
        count = await _enqueue_match_alerts(db_session, theme.id, patent.id, 0)
        assert count == 2
        assert mock_delay.call_count == 2
