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
    all_ok = all(v in ("ok", "skipped") for v in probes.values())
    probes["overall"] = "ok" if all_ok else "degraded"

    return probes


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
