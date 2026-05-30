"""
Source fetch instrumentation helper.

Provides a context manager and async helper for logging every external
data fetch to the source_fetches table. Used by all ingestion providers
for data-health visibility.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.core.models import SourceFetch
from app.database import async_session_maker

logger = logging.getLogger(__name__)


async def record_source_fetch_async(
    *,
    provider: str,
    target_type: str,
    target_id: str | None = None,
    office: str | None = None,
    source_url: str | None = None,
    status: str,
    http_status: int | None = None,
    error_message: str | None = None,
    records_found: int | None = None,
    duration_ms: int | None = None,
    retry_count: int = 0,
) -> SourceFetch:
    """Persist a source fetch log entry asynchronously."""
    now = datetime.now(timezone.utc)
    fetch = SourceFetch(
        provider=provider,
        office=office,
        target_type=target_type,
        target_id=target_id,
        source_url=source_url,
        status=status,
        http_status=http_status,
        error_message=error_message,
        records_found=records_found,
        duration_ms=duration_ms,
        retry_count=retry_count,
        started_at=now,
        completed_at=now,
    )
    try:
        async with async_session_maker() as session:
            session.add(fetch)
            await session.commit()
    except Exception:
        logger.exception("Failed to persist source_fetch log — continuing")
    return fetch


@contextmanager
def record_source_fetch(
    *,
    provider: str,
    target_type: str,
    target_id: str | None = None,
    office: str | None = None,
    source_url: str | None = None,
):
    """Sync context manager that records start/end in source_fetches.

    Usage:
        with record_source_fetch(provider="epo_ops", target_type="publication",
                                  target_id="EP4000000A1") as ctx:
            response = client.fetch(...)
            ctx["http_status"] = response.status_code
            ctx["records_found"] = len(response.data)
            ctx["status"] = "success"
    """
    import asyncio

    start = time.monotonic()
    ctx: dict[str, Any] = {"status": "pending"}
    error_msg: str | None = None
    final_status = "failed"
    http_status: int | None = None
    records: int | None = None

    try:
        yield ctx
        final_status = ctx.get("status", "success")
        http_status = ctx.get("http_status")
        records = ctx.get("records_found")
    except Exception as exc:
        final_status = "failed"
        error_msg = str(exc)[:2000]
        raise
    finally:
        duration = int((time.monotonic() - start) * 1000)
        try:
            asyncio.get_event_loop()
            # We're in an async context — use the async recorder
            asyncio.ensure_future(
                record_source_fetch_async(
                    provider=provider,
                    target_type=target_type,
                    target_id=target_id,
                    office=office,
                    source_url=source_url,
                    status=final_status,
                    http_status=http_status,
                    error_message=error_msg,
                    records_found=records,
                    duration_ms=duration,
                )
            )
        except RuntimeError:
            # No running event loop — record synchronously via async helper
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(
                    record_source_fetch_async(
                        provider=provider,
                        target_type=target_type,
                        target_id=target_id,
                        office=office,
                        source_url=source_url,
                        status=final_status,
                        http_status=http_status,
                        error_message=error_msg,
                        records_found=records,
                        duration_ms=duration,
                    )
                )
            except Exception:
                logger.exception("Failed to persist source_fetch in sync context")
