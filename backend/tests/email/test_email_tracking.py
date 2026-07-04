"""Tests for open/click tracking via Resend webhook (Phase 5 PR 1)."""

from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.xfail(reason="KI-003: asyncpg event-loop conflict in FastAPI TestClient")
from sqlalchemy import select

from app.core.subscription_models import EmailDelivery

SECRET = "test-secret-key-for-tests"


@pytest.fixture(autouse=True, scope="session")
def _patch_settings():
    from app.config import settings as global_settings

    global_settings.auth_secret_key = SECRET


async def _seed_delivery(db_session, resend_id="resend_msg_001"):
    """Create an EmailDelivery row for testing webhook updates."""
    delivery = EmailDelivery(
        user_id="local-user",
        email_type="weekly_briefing",
        resend_message_id=resend_id,
        status="sent",
        subject_variant="A",
    )
    db_session.add(delivery)
    await db_session.commit()
    return delivery


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_open_updates_delivery(client, db_session):
    """email.opened event sets email_opened_at."""
    delivery = await _seed_delivery(db_session)

    body = {
        "type": "email.opened",
        "data": {"email_id": "resend_msg_001"},
    }
    r = await client.post("/api/v1/webhooks/resend", json=body)
    assert r.status_code == 200

    # Re-fetch
    result = await db_session.execute(select(EmailDelivery).where(EmailDelivery.id == delivery.id))
    updated = result.scalar_one()
    assert updated.email_opened_at is not None
    assert updated.webhook_event == "email.opened"


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_click_updates_delivery(client, db_session):
    """email.clicked event sets email_clicked_at and click_url."""
    delivery = await _seed_delivery(db_session, "resend_msg_002")

    body = {
        "type": "email.clicked",
        "data": {
            "email_id": "resend_msg_002",
            "click": {"link": "https://inventionindex8.com/pricing"},
        },
    }
    r = await client.post("/api/v1/webhooks/resend", json=body)
    assert r.status_code == 200

    result = await db_session.execute(select(EmailDelivery).where(EmailDelivery.id == delivery.id))
    updated = result.scalar_one()
    assert updated.email_clicked_at is not None
    assert updated.click_url == "https://inventionindex8.com/pricing"
    assert updated.webhook_event == "email.clicked"


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_open_only_first_time(client, db_session):
    """Multiple open events only record the first one."""
    delivery = await _seed_delivery(db_session, "resend_msg_003")

    first_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    delivery.email_opened_at = first_time
    await db_session.commit()

    body = {
        "type": "email.opened",
        "data": {"email_id": "resend_msg_003"},
    }
    r = await client.post("/api/v1/webhooks/resend", json=body)
    assert r.status_code == 200

    result = await db_session.execute(select(EmailDelivery).where(EmailDelivery.id == delivery.id))
    updated = result.scalar_one()
    # Should still be the first time, not overwritten
    assert updated.email_opened_at == first_time


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_click_truncates_url(client, db_session):
    """Click URL is truncated to 512 chars."""
    delivery = await _seed_delivery(db_session, "resend_msg_004")

    long_url = "https://example.com/" + "x" * 600
    body = {
        "type": "email.clicked",
        "data": {
            "email_id": "resend_msg_004",
            "click": {"link": long_url},
        },
    }
    r = await client.post("/api/v1/webhooks/resend", json=body)
    assert r.status_code == 200

    result = await db_session.execute(select(EmailDelivery).where(EmailDelivery.id == delivery.id))
    updated = result.scalar_one()
    assert len(updated.click_url) <= 512


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_unknown_delivery_no_crash(client):
    """Unknown resend_message_id doesn't crash."""
    body = {
        "type": "email.opened",
        "data": {"email_id": "nonexistent_msg_id"},
    }
    r = await client.post("/api/v1/webhooks/resend", json=body)
    assert r.status_code == 200
