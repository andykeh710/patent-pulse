"""Health check endpoint with DB, Redis, and Resend probes."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


# Probe states that should NOT mark the system degraded. "dev_preview" and
# "disabled" are deliberate non-production email configurations, not failures.
_HEALTHY_PROBE_STATES = ("ok", "skipped", "dev_preview", "disabled")


@router.get("/health")
@limiter.exempt
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    db_status = await _check_db(db)
    redis_status = await _check_redis()
    resend_status = await _check_resend()

    # Only service probes determine overall health. alembic_head is
    # informational (a revision string like "0034"), so it must not be folded
    # into the all-ok check — doing so pinned `overall` to "degraded" forever.
    service_probes = {"db": db_status, "redis": redis_status, "resend": resend_status}
    all_ok = all(v in _HEALTHY_PROBE_STATES for v in service_probes.values())

    probes = dict(service_probes)
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(cfg)
        probes["alembic_head"] = script.get_current_head()
    except Exception:
        probes["alembic_head"] = "unknown"
    probes["overall"] = "ok" if all_ok else "degraded"

    return probes


@router.get("/_sentry-test")
@limiter.exempt
async def sentry_smoke_test() -> dict:
    """Deliberately raise an error to verify Sentry is receiving events.

    Only enabled in non-production environments. Returns 404 in production
    so the endpoint can't be abused.
    """
    if settings.environment == "production":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    1 / 0  # deliberate ZeroDivisionError for Sentry smoke test


async def _check_db(db: AsyncSession) -> str:
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2)
        return "ok"
    except asyncio.TimeoutError:
        logger.warning("Health: DB check timed out")
        return "unreachable"
    except Exception:
        logger.warning("Health: DB check failed", exc_info=True)
        return "unreachable"


async def _check_redis() -> str:
    try:
        from app.tasks.celery_app import celery_app
        conn = celery_app.broker_connection()
        conn.ensure_connection(max_retries=1, timeout=2)
        return "ok"
    except Exception:
        logger.warning("Health: Redis check failed", exc_info=True)
        return "unreachable"


async def _check_resend() -> str:
    # In non-production send modes the app does NOT deliver via Resend — magic
    # links are logged/previewed (see app.email.sender). A live probe is
    # therefore irrelevant and must not report the system as degraded. This is
    # the correct state for local/staging dev, and distinguishes a deliberate
    # config from a genuine credential failure.
    if settings.email_send_mode in ("dev", "dry_run"):
        return "dev_preview"
    if not settings.resend_api_key:
        return "disabled"
    try:
        import urllib.request
        import urllib.error
        # Use the /emails endpoint (works with sending_access keys).
        # /domains requires full_access which is unnecessary and would
        # return 403 for a correctly-configured sending-access key.
        req = urllib.request.Request(
            "https://api.resend.com/emails?limit=1",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "User-Agent": "InventionIndex8/1.0",
            },
        )
        await asyncio.wait_for(
            asyncio.to_thread(urllib.request.urlopen, req, timeout=5),
            timeout=8,
        )
        return "ok"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            logger.warning(
                "Health: Resend probe returned %s — check RESEND_API_KEY "
                "is valid at https://resend.com/api-keys", e.code,
            )
            return "unauthorized"
        logger.warning(
            "Health: Resend probe HTTP %s: %s", e.code, e.reason,
        )
        return "unreachable"
    except Exception as e:
        logger.warning(
            "Health: Resend probe failed: %s: %s",
            type(e).__name__,
            e,
        )
        return "unreachable"
