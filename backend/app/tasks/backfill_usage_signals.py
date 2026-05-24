"""
Usage signals backfill task (Sprint 5).

Processes patents in batches: collects evidence, scores, and
upserts patent_usage_signals rows. Idempotent — safe to run
repeatedly.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.ai_models import PatentUsageSignals, UsageEvidence
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.usage.collector import collect_all_evidence
from app.usage.scoring import compute_usage_signal_score

logger = logging.getLogger(__name__)

# Recompute signals for patents last assessed more than this many days ago.
STALENESS_DAYS = 7


async def backfill_usage_signals_for_session(
    session,
    *,
    limit: int | None = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Session-aware backfill (testable).

    Returns dict: processed, scored, skipped, errors, evidence_total.
    """
    stats: dict[str, int] = {
        "processed": 0,
        "scored": 0,
        "skipped": 0,
        "errors": 0,
        "evidence_total": 0,
    }

    # Fetch patents eligible for processing: have an embedding but
    # either no signal row OR signal is stale.
    stale_cutoff = datetime.utcnow() - timedelta(days=STALENESS_DAYS)

    result = await session.execute(
        select(PatentPublication)
        .where(PatentPublication.embedding.isnot(None))
        .order_by(PatentPublication.opportunity_score.desc().nulls_last())
        .offset(offset)
        .limit(limit)
    )
    patents = result.scalars().all()
    stats["processed"] = len(patents)

    for patent in patents:
        try:
            # Check if signal exists and is fresh.
            existing = await session.execute(
                select(PatentUsageSignals).where(
                    PatentUsageSignals.patent_publication_id == patent.id
                )
            )
            signal_row = existing.scalar_one_or_none()

            if signal_row and signal_row.computed_at and signal_row.computed_at > stale_cutoff:
                stats["skipped"] += 1
                continue

            # Collect evidence.
            evidence, collector_stats = await collect_all_evidence(
                session, patent.id, similarity_top_k=10
            )

            if not evidence:
                # No evidence found — still create a zero-score signal row.
                signal_result = compute_usage_signal_score([], patent.assignees or [])
            else:
                signal_result = compute_usage_signal_score(evidence, patent.assignees or [])

            # Upsert signal row.
            if signal_row:
                _update_signal_row(signal_row, signal_result, evidence)
            else:
                signal_row = PatentUsageSignals(
                    patent_publication_id=patent.id,
                )
                _update_signal_row(signal_row, signal_result, evidence)
                session.add(signal_row)

            # Insert evidence rows (skip if existing to avoid duplicates).
            # Dedup: check if evidence for this patent+source already exists.
            if evidence:
                inserted = await _upsert_evidence_rows(session, evidence)
                stats["evidence_total"] += inserted

            stats["scored"] += 1

        except Exception as e:
            logger.error("Error processing patent %s: %s", patent.doc_id, e)
            stats["errors"] += 1
            continue

    await session.commit()
    logger.info(
        "Usage signals backfill: processed=%d scored=%d skipped=%d errors=%d evidence=%d",
        stats["processed"],
        stats["scored"],
        stats["skipped"],
        stats["errors"],
        stats["evidence_total"],
    )
    return stats


async def backfill_usage_signals(
    *,
    limit: int | None = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Production wrapper — opens its own session."""
    async with async_session_maker() as session:
        return await backfill_usage_signals_for_session(
            session, limit=limit, offset=offset
        )


# ── helpers ────────────────────────────────────────────────────────────


def _update_signal_row(
    row: PatentUsageSignals,
    result: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> None:
    """Update a PatentUsageSignals row in-place from scoring result."""
    row.usage_signal_score = result["score"]
    row.usage_signal_confidence = result["confidence"]
    row.score_breakdown = result["breakdown"]
    row.evidence_count = result["evidence_count"]
    row.strong_evidence_count = result.get("by_tier", {}).get("strong", 0)
    row.medium_evidence_count = result.get("by_tier", {}).get("medium", 0)
    row.weak_evidence_count = result.get("by_tier", {}).get("weak", 0)
    row.top_companies = result.get("top_companies", [])
    row.market_categories = result.get("market_categories", [])
    row.has_self_citation_risk = result.get("has_self_citation_risk", False)
    row.computed_at = datetime.utcnow()

    if result.get("most_recent_date"):
        from datetime import date as date_type
        try:
            row.most_recent_evidence_date = date_type.fromisoformat(
                result["most_recent_date"]
            )
        except (ValueError, TypeError):
            pass


async def _upsert_evidence_rows(
    session,
    evidence: list[dict[str, Any]],
) -> int:
    """Insert evidence rows, skipping duplicates by (patent_id, source_patent_id)."""
    inserted = 0
    for ev in evidence[:50]:  # Cap at 50 per patent (scope doc).
        source_pid = ev.get("source_patent_id")
        target_pid = ev.get("patent_publication_id")
        if not source_pid or not target_pid:
            continue

        # Check for existing.
        result = await session.execute(
            select(UsageEvidence).where(
                UsageEvidence.patent_publication_id == target_pid,
                UsageEvidence.source_patent_id == source_pid,
            )
        )
        if result.scalar_one_or_none():
            continue

        row = UsageEvidence(**ev)
        session.add(row)
        inserted += 1

    return inserted
