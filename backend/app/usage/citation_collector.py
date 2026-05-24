"""
Forward citation evidence collector (Sprint 5).

Collects usage signal evidence from PatentPublication.citations_forward.
Returns dicts ready for insertion into usage_evidence — no DB writes.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication

# Age thresholds in years for tier assignment (scope doc §2).
STRONG_CITATION_MAX_YEARS = 5
MEDIUM_CITATION_MAX_YEARS = 10
WEAK_CITATION_MAX_YEARS = 20
STRONG_MIN_CPC_OVERLAP = 2


def _compute_citation_tier(
    filing_date: date | None,
    source_assignees: list[str],
    target_assignees: list[str],
    shared_cpc: int,
) -> tuple[str, float, dict]:
    """Assign evidence_tier and evidence_confidence based on citation metadata."""
    now = date.today()
    age = (now - filing_date).days / 365 if filing_date else float("inf")
    is_self_cite = bool(
        target_assignees
        and source_assignees
        and any(a in source_assignees for a in target_assignees)
    )

    # Exclusion thresholds (scope doc §2).
    if age > WEAK_CITATION_MAX_YEARS:
        return "excluded", 0.0, {}
    if age > MEDIUM_CITATION_MAX_YEARS or is_self_cite:
        return "weak", 0.3, {"reason": "self_citation" if is_self_cite else "age"}
    if age <= STRONG_CITATION_MAX_YEARS and shared_cpc >= STRONG_MIN_CPC_OVERLAP:
        return "strong", 0.9, {}
    if age <= MEDIUM_CITATION_MAX_YEARS:
        return "medium", 0.6, {}

    return "weak", 0.3, {"reason": "age"}


async def collect_citation_evidence(
    session: AsyncSession,
    patent_id: UUID,
) -> list[dict]:
    """Collect forward-citation evidence for a single patent.

    Returns list of dicts with keys matching usage_evidence columns.
    Never writes to DB.
    """
    result = await session.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent or not patent.citations_forward:
        return []

    target_assignees = patent.assignees or []
    target_cpc = set(patent.cpc or [])

    evidence_rows: list[dict] = []
    seen = set()

    for doc_id in patent.citations_forward:
        if doc_id in seen:
            continue
        seen.add(doc_id)

        # Look up the citing patent by doc_id.
        source_result = await session.execute(
            select(PatentPublication).where(
                PatentPublication.doc_id == doc_id
            )
        )
        source = source_result.scalar_one_or_none()
        if not source:
            continue

        source_cpc = set(source.cpc or [])
        shared = list(target_cpc & source_cpc)
        shared_count = len(shared)

        tier, confidence, extra = _compute_citation_tier(
            filing_date=source.filing_date,
            source_assignees=source.assignees or [],
            target_assignees=target_assignees,
            shared_cpc=shared_count,
        )

        if tier == "excluded":
            continue

        evidence_rows.append({
            "patent_publication_id": patent_id,
            "source_type": "forward_citation",
            "source_patent_id": source.id,
            "source_patent_doc_id": source.doc_id,
            "source_patent_title": source.title,
            "source_patent_assignee": (source.assignees or [None])[0],
            "source_patent_filing_date": source.filing_date,
            "source_patent_cpc": source.cpc or [],
            "matched_cpc": shared,
            "cpc_overlap_count": shared_count,
            "similarity_score": None,
            "citation_direction": "forward",
            "evidence_tier": tier,
            "evidence_confidence": confidence,
        })

    return evidence_rows
