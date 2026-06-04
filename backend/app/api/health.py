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


@router.get("/health")
@limiter.exempt
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    db_status = await _check_db(db)
    redis_status = await _check_redis()
    resend_status = await _check_resend()

    probes = {"db": db_status, "redis": redis_status, "resend": resend_status}
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(cfg)
        probes["alembic_head"] = script.get_current_head()
    except Exception:
        probes["alembic_head"] = "unknown"
    all_ok = all(v in ("ok", "skipped") for v in probes.values())
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
    if not settings.resend_api_key:
        return "skipped"
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        )
        await asyncio.wait_for(asyncio.to_thread(urllib.request.urlopen, req, timeout=2), timeout=3)
        return "ok"
    except Exception:
        logger.info("Health: Resend check skipped (API not configured or unreachable)")
        return "unreachable"
