"""
Sentry error tracking (PR8).

Silently noops when ``SENTRY_DSN`` is unset — no runtime errors, no
side effects.  Designed to be called once at app startup.

Usage:
    from app.observability.sentry import init_sentry
    init_sentry()
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is configured.

    When the DSN is empty (default in dev), this function logs an info
    message and returns without touching the SDK.
    """
    from app.config import settings

    dsn = settings.sentry_dsn
    if not dsn:
        logger.info("SENTRY_DSN not set — Sentry disabled")
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        release=settings.release_sha or "unknown",
        traces_sample_rate=0.1,
        profiles_sample_rate=0.0,  # off for V1
        send_default_pii=False,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
    )
    logger.info("Sentry initialized (env=%s)", settings.environment)
