"""
Expiry assessment backfill task.

Computes or recomputes ExpiryAssessment rows for patent records.
Idempotent — safe to run repeatedly.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import ExpiryAssessment
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.expiry.assessment import (
    compute_expiry_assessment,
    compute_expiry_opportunity_score,
)

logger = logging.getLogger(__name__)


async def backfill_expiry_assessments_for_session(
    session: AsyncSession,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    """Compute ExpiryAssessment rows using an existing session (testable core).

    Selects patents that have no existing ExpiryAssessment row, computes
    the assessment, and inserts or updates.

    Args:
        session: An active AsyncSession.
        limit: Max patents to process (None = all).
        offset: Skip this many patents (for paginated backfill).

    Returns:
        Dict with counts: ``{"created": N, "updated": N, "skipped": N,
        "total_processed": N}``.
    """
    stats = {"created": 0, "updated": 0, "skipped": 0, "total_processed": 0}

    # Select patents that have NO existing ExpiryAssessment row.
    existing_sub = select(ExpiryAssessment.patent_publication_id)
    stmt = (
        select(PatentPublication.id)
        .where(PatentPublication.id.notin_(existing_sub))
        .order_by(PatentPublication.created_at.asc())
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    patent_ids = [row[0] for row in result.all()]
    logger.info(
        "Backfill: found %d patent(s) to assess (limit=%s, offset=%s)",
        len(patent_ids), limit, offset,
    )

    for patent_id in patent_ids:
        patent_result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == patent_id)
        )
        patent = patent_result.scalar_one_or_none()
        if patent is None:
            stats["skipped"] += 1
            continue

        payload = compute_expiry_assessment(patent)
        opp_score = compute_expiry_opportunity_score(patent, payload)

        existing_result = await session.execute(
            select(ExpiryAssessment).where(
                ExpiryAssessment.patent_publication_id == patent_id
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            _update_assessment(existing, payload, opp_score)
            stats["updated"] += 1
        else:
            row = ExpiryAssessment(
                patent_publication_id=patent_id,
                expiry_opportunity_score=opp_score["score"],
                expiry_opportunity_breakdown=opp_score["breakdown"],
                **{k: v for k, v in payload.items()},
            )
            session.add(row)
            stats["created"] += 1

        stats["total_processed"] += 1

        if stats["total_processed"] % 100 == 0:
            await session.commit()
            logger.info(
                "Backfill progress: %d processed (%d created, %d updated)",
                stats["total_processed"], stats["created"], stats["updated"],
            )

    await session.commit()

    logger.info(
        "Backfill complete: %d processed (%d created, %d updated, %d skipped)",
        stats["total_processed"], stats["created"], stats["updated"], stats["skipped"],
    )
    return stats


async def backfill_expiry_assessments(
    *,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    """Production wrapper: opens its own session via async_session_maker.

    For testability, prefer ``backfill_expiry_assessments_for_session``
    directly when a session is available.
    """
    async with async_session_maker() as session:
        return await backfill_expiry_assessments_for_session(
            session, limit=limit, offset=offset,
        )


# ── helpers ──────────────────────────────────────────────────────────


def _update_assessment(
    existing: ExpiryAssessment,
    payload: dict,
    opp_score: dict,
) -> None:
    """Update an existing ExpiryAssessment row in-place with new payload."""
    existing.estimated_expiry_date = payload["estimated_expiry_date"]
    existing.expiry_status = payload["expiry_status"]
    existing.expiry_status_confidence = payload["expiry_status_confidence"]
    existing.maintenance_status = payload["maintenance_status"]
    existing.maintenance_status_source = payload["maintenance_status_source"]
    existing.active_family_risk = payload["active_family_risk"]
    existing.active_family_risk_reason = payload["active_family_risk_reason"]
    existing.terminal_disclaimer_flag = payload["terminal_disclaimer_flag"]
    existing.patent_term_adjustment_days = payload["patent_term_adjustment_days"]
    existing.legal_caveats = payload["legal_caveats"]
    existing.assessment_json = payload["assessment_json"]
    existing.expiry_opportunity_score = opp_score["score"]
    existing.expiry_opportunity_breakdown = opp_score["breakdown"]
    existing.source_updated_at = datetime.utcnow()
