"""Tests for Resend email sender with mode guards."""
import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.core.ai_models import User  # ensure FK target is in metadata
from app.core.subscription_models import EmailDelivery
from app.config import Settings


@pytest.fixture
def dev_settings():
    return Settings(
        email_send_mode="dev",
        email_dev_recipient="dev@example.com",
        email_from_address="alerts@example.com",
        resend_api_key="re_test",
        auth_secret_key="test-secret",
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_dev_mode_rewrites_recipient(db_session, monkeypatch):
    monkeypatch.setattr("app.email.sender.settings", Settings(
        email_send_mode="dev",
        email_dev_recipient="dev@example.com",
        email_from_address="alerts@example.com",
        resend_api_key="",
        auth_secret_key="test-secret",
    ))
    from app.email.sender import send_email
    r = await send_email(
        db_session=db_session,
        to="real@example.com",
        subject="Test",
        template_name="magic_link.html",
        template_kwargs={"magic_link_url": "http://x", "magic_link_base_url": "http://x"},
        user_id="local-user",
        email_type="magic_link",
    )
    assert r["status"] == "dev"
    from sqlalchemy import select
    from app.core.subscription_models import EmailDelivery
    delivery = (await db_session.execute(
        select(EmailDelivery).order_by(EmailDelivery.sent_at.desc()).limit(1)
    )).scalar_one()
    assert delivery.status == "dev"
    assert delivery.email_type == "magic_link"


@pytest.mark.asyncio(loop_scope="function")
async def test_dry_run_writes_delivery_row(db_session, monkeypatch):
    monkeypatch.setattr("app.email.sender.settings", Settings(
        email_send_mode="dry_run",
        email_dev_recipient="dev@example.com",
        email_from_address="alerts@example.com",
        resend_api_key="",
        auth_secret_key="test-secret",
    ))
    from app.email.sender import send_email
    r = await send_email(
        db_session=db_session,
        to="real@example.com",
        subject="Test",
        template_name="magic_link.html",
        template_kwargs={"magic_link_url": "http://x", "magic_link_base_url": "http://x"},
        user_id="local-user",
        email_type="magic_link",
    )
    assert r["status"] == "dry_run"
    from sqlalchemy import select
    from app.core.subscription_models import EmailDelivery
    delivery = (await db_session.execute(
        select(EmailDelivery).order_by(EmailDelivery.sent_at.desc()).limit(1)
    )).scalar_one()
    assert delivery.status == "dry_run"


@pytest.mark.asyncio(loop_scope="function")
async def test_production_without_acknowledgement_refused(db_session, monkeypatch):
    monkeypatch.setattr("app.email.sender.settings", Settings(
        email_send_mode="production",
        email_dev_recipient="dev@example.com",
        email_from_address="alerts@example.com",
        resend_api_key="",
        auth_secret_key="test-secret",
    ))
    monkeypatch.setenv("EMAIL_PRODUCTION_ACKNOWLEDGED", "false")
    from app.email.sender import send_email
    r = await send_email(
        db_session=db_session,
        to="real@example.com",
        subject="Test",
        template_name="magic_link.html",
        template_kwargs={"magic_link_url": "http://x", "magic_link_base_url": "http://x"},
        user_id="local-user",
        email_type="magic_link",
    )
    assert r["status"] == "refused"


@pytest.mark.asyncio(loop_scope="function")
async def test_production_with_acknowledgement_sends(db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_PRODUCTION_ACKNOWLEDGED", "true")
    monkeypatch.setattr("app.email.sender.settings", Settings(
        email_send_mode="production",
        email_dev_recipient="dev@example.com",
        email_from_address="alerts@example.com",
        resend_api_key="re_test123",
        auth_secret_key="test-secret",
    ))
    with patch("resend.Emails.send", return_value={"id": "msg_123"}):
        from app.email.sender import send_email
        r = await send_email(
            db_session=db_session,
            to="real@example.com",
            subject="Test",
            template_name="magic_link.html",
            template_kwargs={"magic_link_url": "http://x", "magic_link_base_url": "http://x"},
            user_id="local-user",
            email_type="magic_link",
        )
        assert r["status"] == "sent"
