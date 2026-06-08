"""Tests for alert webhook system (Phase 5 PR 2)."""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.core.alert_models import Alert, UserWebhookConfig
from app.core.models import PatentPublication
from app.tasks.alerts import (
    _compute_hmac,
    _deliver_via_webhook,
    _deliver_with_session,
    _scan_with_session,
)

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


# ═══════════════════════════════════════════════════════════════════════
# HMAC
# ═══════════════════════════════════════════════════════════════════════


def test_hmac_deterministic():
    """Same payload + secret = same signature."""
    s1 = _compute_hmac(b"hello", "secret")
    s2 = _compute_hmac(b"hello", "secret")
    assert s1 == s2
    assert len(s1) == 64  # SHA256


def test_hmac_different_secret():
    """Different secrets produce different signatures."""
    s1 = _compute_hmac(b"hello", "secret1")
    s2 = _compute_hmac(b"hello", "secret2")
    assert s1 != s2


def test_hmac_different_payload():
    """Different payloads produce different signatures."""
    s1 = _compute_hmac(b"hello", "secret")
    s2 = _compute_hmac(b"world", "secret")
    assert s1 != s2


# ═══════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_scan_creates_assignee_filed_alert(db_session):
    """A followed company filing a patent in a watched CPC area creates an alert."""
    from app.core.ai_models import User, UserCompanyFollow
    from app.core.subscription_models import TopicSubscription
    from app.core.theme_models import Theme, ThemeMatch

    # Set up user
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "lifetime"

    # Theme with CPC
    theme = Theme(name="AI/ML", is_active=True, cpc_prefixes=["G06N"])
    db_session.add(theme)
    await db_session.flush()

    # Subscription
    db_session.add(TopicSubscription(
        user_id="local-user", theme_id=theme.id, mode="weekly_digest"
    ))

    # Followed company
    db_session.add(UserCompanyFollow(
        user_id="local-user", company_normalized_name="acme", display_name="Acme Corp"
    ))

    # Patent filed today by Acme in AI/ML CPC
    db_session.add(PatentPublication(
        doc_id="USPTO:US20240000001",
        office="USPTO",
        publication_number="20240000001",
        publication_date=datetime.now(timezone.utc).date(),
        assignees=["Acme Corp"],
        cpc=["G06N 3/08"],
        title="Neural Network Training System",
    ))
    await db_session.commit()

    stats = await _scan_with_session(db_session)
    assert stats["assignee_filed"] >= 1

    # Verify alert row
    alerts = (await db_session.execute(
        select(Alert).where(Alert.user_id == "local-user")
    )).scalars().all()
    assert len(alerts) >= 1
    assert alerts[0].type == "assignee_filed"
    assert alerts[0].payload.get("assignee") == "Acme Corp"


@pytest.mark.asyncio(loop_scope="function")
async def test_scan_creates_expiring_alert(db_session):
    """A patent expiring within 90 days in a watched CPC area creates an alert."""
    from app.core.ai_models import User
    from app.core.subscription_models import TopicSubscription
    from app.core.theme_models import Theme

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()

    theme = Theme(name="Semiconductor", is_active=True, cpc_prefixes=["H01L"])
    db_session.add(theme)
    await db_session.flush()

    db_session.add(TopicSubscription(
        user_id="local-user", theme_id=theme.id, mode="weekly_digest"
    ))

    # Patent expiring in 30 days
    expiry = (datetime.now(timezone.utc) + timedelta(days=30)).date()
    db_session.add(PatentPublication(
        doc_id="USPTO:US20240000002",
        office="USPTO",
        publication_number="20240000002",
        publication_date=datetime.now(timezone.utc).date(),
        assignees=["Intel Corp"],
        cpc=["H01L 21/02"],
        title="Semiconductor Process",
        estimated_expiry_date=expiry,
    ))
    await db_session.commit()

    stats = await _scan_with_session(db_session)
    assert stats["patent_expiring"] >= 1


@pytest.mark.asyncio(loop_scope="function")
async def test_scan_creates_high_opportunity_alert(db_session):
    """A new patent with opportunity_score > 80 creates an alert."""
    from app.core.ai_models import User
    from app.core.subscription_models import TopicSubscription
    from app.core.theme_models import Theme

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()

    theme = Theme(name="Biotech", is_active=True, cpc_prefixes=["C12N"])
    db_session.add(theme)
    await db_session.flush()

    db_session.add(TopicSubscription(
        user_id="local-user", theme_id=theme.id, mode="weekly_digest"
    ))

    db_session.add(PatentPublication(
        doc_id="USPTO:US20240000003",
        office="USPTO",
        publication_number="20240000003",
        publication_date=datetime.now(timezone.utc).date(),
        assignees=["Moderna"],
        cpc=["C12N 15/10"],
        title="mRNA Vaccine Platform",
        summary={"opportunity_score": 92},
    ))
    await db_session.commit()

    stats = await _scan_with_session(db_session)
    assert stats["high_opportunity"] >= 1


# ═══════════════════════════════════════════════════════════════════════
# Webhook delivery
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_delivery_success(monkeypatch):
    """Successful webhook delivery marks alert as sent."""
    config = UserWebhookConfig(
        user_id="local-user",
        webhook_url="https://example.com/webhook",
        secret_key="test-secret",
        enabled=True,
    )

    alert = Alert(
        user_id="local-user",
        type="assignee_filed",
        payload={"patent_id": "USPTO:US123", "title": "Test"},
    )

    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    async def mock_post(*args, **kwargs):
        return mock_resp

    with patch("httpx.AsyncClient.post", new=mock_post):
        success = await _deliver_via_webhook(alert, config)

    assert success is True


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_delivery_http_error(monkeypatch):
    """Non-2xx response marks delivery as failed."""
    config = UserWebhookConfig(
        user_id="local-user",
        webhook_url="https://example.com/webhook",
        secret_key="test-secret",
        enabled=True,
    )

    alert = Alert(
        user_id="local-user",
        type="assignee_filed",
        payload={"title": "Test"},
    )

    mock_resp = AsyncMock()
    mock_resp.status_code = 500

    async def mock_post(*args, **kwargs):
        return mock_resp

    with patch("httpx.AsyncClient.post", new=mock_post):
        success = await _deliver_via_webhook(alert, config)

    assert success is False


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_delivery_network_error(monkeypatch):
    """Network error marks delivery as failed."""
    config = UserWebhookConfig(
        user_id="local-user",
        webhook_url="https://down.example.com/webhook",
        secret_key="test-secret",
        enabled=True,
    )

    alert = Alert(
        user_id="local-user",
        type="assignee_filed",
        payload={"title": "Test"},
    )

    async def mock_post(*args, **kwargs):
        raise RuntimeError("Connection refused")

    with patch("httpx.AsyncClient.post", new=mock_post):
        success = await _deliver_via_webhook(alert, config)

    assert success is False


# ═══════════════════════════════════════════════════════════════════════
# Retry logic
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_alert_retry_increments_on_failure(db_session):
    """Failed delivery increments retry_count, max 3 then failed."""
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    user.email = "test@example.com"

    alert = Alert(
        user_id="local-user",
        type="assignee_filed",
        payload={"title": "Test"},
        status="pending",
    )
    db_session.add(alert)
    await db_session.commit()

    # Email will fail (no Resend config), so alert retries
    async def mock_send(*args, **kwargs):
        return {"status": "failed"}

    with patch("app.tasks.alerts._deliver_via_email", new=mock_send):
        await _deliver_with_session(db_session)

    # Re-fetch
    result = await db_session.execute(
        select(Alert).where(Alert.id == alert.id)
    )
    updated = result.scalar_one()
    assert updated.retry_count >= 1
    assert updated.status in ("pending", "failed")


# ═══════════════════════════════════════════════════════════════════════
# Webhook signature headers
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_webhook_sends_correct_headers(monkeypatch):
    """Webhook POST includes X-IIE-Signature and X-IIE-Event headers."""
    config = UserWebhookConfig(
        user_id="local-user",
        webhook_url="https://example.com/webhook",
        secret_key="test-secret",
        enabled=True,
    )

    alert = Alert(
        user_id="local-user",
        type="assignee_filed",
        payload={"title": "Test"},
    )

    captured_headers = {}

    async def capture_post(url, **kwargs):
        captured_headers.update(kwargs.get("headers", {}))
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        return mock_resp

    with patch("httpx.AsyncClient.post", new=capture_post):
        await _deliver_via_webhook(alert, config)

    assert "X-IIE-Signature" in captured_headers
    assert captured_headers["X-IIE-Signature"].startswith("sha256=")
    assert captured_headers["X-IIE-Event"] == "alerts.assignee_filed"


# ═══════════════════════════════════════════════════════════════════════
# Dedup
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_alert_dedup_same_patent(db_session):
    """Alert for same user+type+patent_id within 24h is deduplicated."""
    from app.core.ai_models import User, UserCompanyFollow
    from app.core.subscription_models import TopicSubscription
    from app.core.theme_models import Theme

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()

    theme = Theme(name="AI", is_active=True, cpc_prefixes=["G06N"])
    db_session.add(theme)
    await db_session.flush()

    db_session.add(TopicSubscription(
        user_id="local-user", theme_id=theme.id, mode="weekly_digest"
    ))
    db_session.add(UserCompanyFollow(
        user_id="local-user", company_normalized_name="acme", display_name="Acme"
    ))

    db_session.add(PatentPublication(
        doc_id="USPTO:US20240000004",
        office="USPTO",
        publication_number="20240000004",
        publication_date=datetime.now(timezone.utc).date(),
        assignees=["Acme"],
        cpc=["G06N 3/08"],
        title="AI System",
    ))
    await db_session.commit()

    # First scan
    await _scan_with_session(db_session)
    count1 = (await db_session.execute(
        select(Alert).where(Alert.user_id == "local-user")
    )).scalars().all()

    # Second scan (same data)
    await _scan_with_session(db_session)
    count2 = (await db_session.execute(
        select(Alert).where(Alert.user_id == "local-user")
    )).scalars().all()

    # Should be same count (dedup worked)
    assert len(count1) == len(count2)
    assert len(count1) > 0
