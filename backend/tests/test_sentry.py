"""
Tests for PR8 Sentry error tracking.

Covers init_sentry (DSN gating), the debug/sentry admin endpoint,
and auth guard on the debug endpoint.
"""

from __future__ import annotations

import logging
from io import StringIO
from unittest.mock import patch

import pytest
from httpx import AsyncClient


# ── helpers ──────────────────────────────────────────────────────────


def _cookie(user_id="local-user"):
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    return {"auth_session": jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc),
         "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        settings.auth_secret_key, algorithm="HS256",
    )}


# ── init_sentry tests ────────────────────────────────────────────────


def test_init_sentry_noops_when_dsn_unset(monkeypatch):
    """When SENTRY_DSN is empty, init_sentry logs and skips SDK init."""
    from app.observability.sentry import init_sentry

    # Patch the settings object directly — init_sentry imports it
    # via ``from app.config import settings``.
    monkeypatch.setattr("app.config.settings.sentry_dsn", "")
    try:
        monkeypatch.delattr("sentry_sdk.init")
    except AttributeError:
        pass  # sentry_sdk may not be imported when DSN is unset

    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    log = logging.getLogger("app.observability.sentry")
    log.addHandler(handler)

    init_sentry()

    handler.flush()
    log.removeHandler(handler)
    output = buf.getvalue()
    assert "SENTRY_DSN not set" in output


def test_init_sentry_calls_sdk_when_dsn_set(monkeypatch):
    """When SENTRY_DSN is set, sentry_sdk.init is called with expected args."""
    from app.observability.sentry import init_sentry

    monkeypatch.setattr(
        "app.config.settings.sentry_dsn",
        "https://key@o123.ingest.sentry.io/456",
    )
    monkeypatch.setattr("app.config.settings.environment", "test")
    monkeypatch.setattr("app.config.settings.release_sha", "abc123")

    with patch("sentry_sdk.init") as mock_init:
        init_sentry()

    mock_init.assert_called_once()
    kwargs = mock_init.call_args[1]
    assert kwargs["dsn"] == "https://key@o123.ingest.sentry.io/456"
    assert kwargs["environment"] == "test"
    assert kwargs["release"] == "abc123"
    assert kwargs["traces_sample_rate"] == 0.1
    assert kwargs["send_default_pii"] is False


# ── Admin debug endpoint tests ───────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_debug_sentry_unauthorized(client: AsyncClient):
    """No auth cookie → 401 on debug/sentry."""
    r = await client.post("/api/v1/admin/debug/sentry")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_debug_sentry_non_admin_gets_403(client: AsyncClient, db_session):
    """Non-admin user → 403 on debug/sentry."""
    from app.core.ai_models import User
    from sqlalchemy import select
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = False
    await db_session.commit()
    r = await client.post("/api/v1/admin/debug/sentry", cookies=_cookie())
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_debug_sentry_admin_raises_runtime_error(client: AsyncClient, db_session):
    """Admin user → the endpoint intentionally raises RuntimeError.

    The ASGI test transport propagates unhandled exceptions, so we
    catch it here instead of checking for a 500 status code.
    """
    from app.core.ai_models import User
    from sqlalchemy import select
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    with pytest.raises(RuntimeError, match="PR8 Sentry debug"):
        await client.post("/api/v1/admin/debug/sentry", cookies=_cookie())
