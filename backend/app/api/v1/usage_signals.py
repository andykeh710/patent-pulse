"""Sprint 5 — Usage Signals API endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.ai_models import AIArtifact, PatentUsageSignals, UsageEvidence
from app.core.models import PatentPublication
from app.usage.collector import collect_all_evidence
from app.usage.scoring import compute_usage_signal_score

router = APIRouter()


# ── schemas ──────────────────────────────────────────────────────────


class EvidenceItem(BaseModel):
    id: UUID
    source_type: str
    source_patent_title: str | None = None
    source_patent_assignee: str | None = None
    source_patent_filing_date: str | None = None
    evidence_tier: str
    similarity_score: float | None = None
    cpc_overlap_count: int = 0
    matched_cpc: list[str] = []

    @classmethod
    def from_row(cls, row) -> EvidenceItem:
        return cls(
            id=row.id,
            source_type=row.source_type,
            source_patent_title=row.source_patent_title,
            source_patent_assignee=row.source_patent_assignee,
            source_patent_filing_date=(
                row.source_patent_filing_date.isoformat()
                if row.source_patent_filing_date
                else None
            ),
            evidence_tier=row.evidence_tier,
            similarity_score=row.similarity_score,
            cpc_overlap_count=row.cpc_overlap_count or 0,
            matched_cpc=row.matched_cpc or [],
        )


class UsageSignalResponse(BaseModel):
    patent_id: UUID
    score: float = 0
    confidence: str = "low"
    breakdown: dict | None = None
    evidence_count: int = 0
    strong_count: int = 0
    medium_count: int = 0
    weak_count: int = 0
    has_self_citation_risk: bool = False
    top_companies: list[str] = []
    market_categories: list[str] = []
    most_recent_evidence_date: str | None = None
    narrative_summary: str | None = None
    narrative_generated_at: str | None = None
    evidence: list[EvidenceItem] = []

    @classmethod
    def from_signal(cls, signal: PatentUsageSignals, evidence_rows: list) -> UsageSignalResponse:
        return cls(
            patent_id=signal.patent_publication_id,
            score=signal.usage_signal_score or 0,
            confidence=signal.usage_signal_confidence or "low",
            breakdown=signal.score_breakdown,
            evidence_count=signal.evidence_count or 0,
            strong_count=signal.strong_evidence_count or 0,
            medium_count=signal.medium_evidence_count or 0,
            weak_count=signal.weak_evidence_count or 0,
            has_self_citation_risk=signal.has_self_citation_risk or False,
            top_companies=signal.top_companies or [],
            market_categories=signal.market_categories or [],
            most_recent_evidence_date=(
                signal.most_recent_evidence_date.isoformat()
                if signal.most_recent_evidence_date
                else None
            ),
            narrative_summary=signal.narrative_summary,
            narrative_generated_at=(
                signal.narrative_generated_at.isoformat()
                if signal.narrative_generated_at
                else None
            ),
            evidence=[EvidenceItem.from_row(e) for e in evidence_rows],
        )


class GenerateResponse(BaseModel):
    patent_id: UUID
    score: float
    confidence: str
    evidence_count: int
    evidence_added: int


class NarrativeResponse(BaseModel):
    patent_id: UUID
    summary: str
    evidence_summary: str = ""
    market_categories: list[str] = []
    related_companies: list[str] = []
    limitations: list[str] = []
    cached: bool = False
    stale: bool = False


# ── helpers ──────────────────────────────────────────────────────────


async def _get_or_assess_signals(
    db: AsyncSession, patent_id: UUID
) -> tuple[PatentUsageSignals | None, list]:
    """Return existing signal row + evidence, or (None, []) if not assessed."""
    result = await db.execute(
        select(PatentUsageSignals).where(
            PatentUsageSignals.patent_publication_id == patent_id
        )
    )
    signal = result.scalar_one_or_none()

    if signal:
        evidence_result = await db.execute(
            select(UsageEvidence)
            .where(UsageEvidence.patent_publication_id == patent_id)
            .order_by(UsageEvidence.evidence_tier.desc().nulls_last())
            .limit(50)
        )
        evidence_rows = evidence_result.scalars().all()
        return signal, list(evidence_rows)

    return None, []


async def _get_patent_or_404(db: AsyncSession, patent_id: UUID) -> PatentPublication:
    result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    return patent


# ── endpoints ────────────────────────────────────────────────────────


@router.get("/{patent_id}", response_model=UsageSignalResponse)
async def get_usage_signals(
    patent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get usage signal assessment for a patent (with evidence list)."""
    await _get_patent_or_404(db, patent_id)

    signal, evidence = await _get_or_assess_signals(db, patent_id)
    if not signal:
        raise HTTPException(status_code=404, detail="No usage signals assessed for this patent")

    return UsageSignalResponse.from_signal(signal, evidence)


@router.post("/{patent_id}/generate", response_model=GenerateResponse)
async def generate_usage_signals(
    patent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate (or refresh) usage signals for a patent."""
    patent = await _get_patent_or_404(db, patent_id)

    # Run collectors.
    evidence_dicts, collector_stats = await collect_all_evidence(
        db, patent.id, similarity_top_k=10
    )

    # Score.
    signal_result = compute_usage_signal_score(
        evidence_dicts, patent.assignees or []
    )

    # Upsert signal row.
    existing = await db.execute(
        select(PatentUsageSignals).where(
            PatentUsageSignals.patent_publication_id == patent_id
        )
    )
    signal_row = existing.scalar_one_or_none()

    if signal_row:
        _update_from_result(signal_row, signal_result, evidence_dicts)
    else:
        signal_row = PatentUsageSignals(patent_publication_id=patent_id)
        _update_from_result(signal_row, signal_result, evidence_dicts)
        db.add(signal_row)

    # Upsert evidence rows.
    evidence_added = await _upsert_evidence(db, evidence_dicts)
    await db.commit()

    return GenerateResponse(
        patent_id=patent_id,
        score=signal_result["score"],
        confidence=signal_result["confidence"],
        evidence_count=signal_result["evidence_count"],
        evidence_added=evidence_added,
    )


@router.post("/{patent_id}/narrative", response_model=NarrativeResponse)
async def generate_narrative(
    patent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate (or return cached) usage signal narrative."""
    await _get_patent_or_404(db, patent_id)

    signal, evidence = await _get_or_assess_signals(db, patent_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Generate usage signals first")

    if signal.usage_signal_score is not None and signal.usage_signal_score < 20:
        raise HTTPException(
            status_code=400,
            detail="Score too low for narrative generation (minimum 20 required)",
        )

    # Check cache.
    if signal.narrative_artifact_id:
        result = await db.execute(
            select(AIArtifact).where(AIArtifact.id == signal.narrative_artifact_id)
        )
        cached = result.scalar_one_or_none()
        if cached and cached.content_json:
            content = cached.content_json
            stale = (
                signal.computed_at is not None
                and signal.narrative_generated_at is not None
                and signal.computed_at > signal.narrative_generated_at
            )
            return NarrativeResponse(
                patent_id=patent_id,
                summary=content.get("summary", ""),
                evidence_summary=content.get("evidence_summary", ""),
                market_categories=content.get("market_categories", []) or [],
                related_companies=content.get("related_companies", []) or [],
                limitations=content.get("limitations", []) or [],
                cached=True,
                stale=stale,
            )

    # Generate fresh.
    from app.ai.usage_narrative import generate_usage_narrative as _gen

    patent = await _get_patent_or_404(db, patent_id)

    narrative_dict, artifact_id = await _gen(
        db,
        {
            "score": signal.usage_signal_score,
            "confidence": signal.usage_signal_confidence,
            "evidence_count": signal.evidence_count,
            "by_tier": {
                "strong": signal.strong_evidence_count,
                "medium": signal.medium_evidence_count,
                "weak": signal.weak_evidence_count,
            },
        },
        [{
            "source_patent_title": e.source_patent_title,
            "source_patent_assignee": e.source_patent_assignee,
            "evidence_tier": e.evidence_tier,
            "similarity_score": e.similarity_score,
            "cpc_overlap_count": e.cpc_overlap_count,
            "source_patent_filing_date": e.source_patent_filing_date,
            "matched_cpc": e.matched_cpc,
        } for e in evidence[:5]],
        patent_id,
        patent_title=patent.title or "",
        patent_assignee=(patent.assignees or [None])[0] or "",
    )

    # Link narrative to signal row.
    signal.narrative_summary = narrative_dict.get("summary", "")
    signal.narrative_artifact_id = artifact_id
    signal.narrative_generated_at = datetime.utcnow()
    await db.commit()

    return NarrativeResponse(
        patent_id=patent_id,
        summary=narrative_dict.get("summary", ""),
        evidence_summary=narrative_dict.get("evidence_summary", ""),
        market_categories=narrative_dict.get("market_categories", []) or [],
        related_companies=narrative_dict.get("related_companies", []) or [],
        limitations=narrative_dict.get("limitations", []) or [],
        cached=False,
        stale=False,
    )


# ── helpers ──────────────────────────────────────────────────────────

from datetime import datetime


def _update_from_result(
    row: PatentUsageSignals,
    result: dict,
    evidence: list[dict],
) -> None:
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
        try:
            from datetime import date as date_type
            row.most_recent_evidence_date = date_type.fromisoformat(
                result["most_recent_date"]
            )
        except (ValueError, TypeError):
            pass


async def _upsert_evidence(db: AsyncSession, evidence: list[dict]) -> int:
    inserted = 0
    for ev in evidence[:50]:
        source_pid = ev.get("source_patent_id")
        if not source_pid:
            continue
        exists = await db.execute(
            select(UsageEvidence).where(
                UsageEvidence.patent_publication_id == ev.get("patent_publication_id"),
                UsageEvidence.source_patent_id == source_pid,
            )
        )
        if exists.scalar_one_or_none():
            continue
        row = UsageEvidence(**{k: v for k, v in ev.items() if hasattr(UsageEvidence, k)})
        db.add(row)
        inserted += 1
    return inserted
