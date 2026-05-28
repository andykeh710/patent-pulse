"""
Semantic similarity evidence collector (Sprint 5).

Uses pgvector to find newer patents that are semantically
similar to the target. Returns dicts ready for insertion into
usage_evidence — no DB writes.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication

# Similarity thresholds for tier assignment (scope doc §2).
STRONG_SIMILARITY = 0.85
MEDIUM_SIMILARITY = 0.75
WEAK_SIMILARITY = 0.65


def _compute_similarity_tier(
    similarity: float,
    shared_cpc: int,
    source_assignees: list[str],
    target_assignees: list[str],
) -> tuple[str, float]:
    """Assign evidence_tier and confidence based on similarity + CPC overlap."""
    is_same_assignee = bool(
        target_assignees
        and source_assignees
        and any(a in source_assignees for a in target_assignees)
    )

    if similarity >= STRONG_SIMILARITY and shared_cpc >= 1:
        return "strong", 0.9
    if similarity >= MEDIUM_SIMILARITY:
        conf = 0.5 if is_same_assignee else 0.7
        return "medium", conf
    if similarity >= WEAK_SIMILARITY:
        return "weak", 0.3

    return "excluded", 0.0


async def collect_similar_evidence(
    session: AsyncSession,
    patent_id: UUID,
    *,
    top_k: int = 10,
    min_similarity: float = WEAK_SIMILARITY,
) -> list[dict]:
    """Collect semantic similarity evidence for a patent.

    Finds newer patents (filed after this patent's grant_date, or
    filing_date fallback) that are semantically similar per pgvector.

    Returns list of dicts with keys matching usage_evidence columns.
    """
    # Fetch target patent.
    result = await session.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent or patent.embedding is None:
        return []

    target_assignees = patent.assignees or []
    target_cpc = set(patent.cpc or [])
    embedding = patent.embedding

    # "Newer patent" (decision #7): filing_date > source.grant_date,
    # fallback to source.filing_date when grant_date is null.
    cutoff_date = patent.grant_date or patent.filing_date
    if cutoff_date is None:
        cutoff_date = date(2000, 1, 1)

    # Use pgvector cosine distance via SQLAlchemy.
    # 1 - (embedding <=> target) = cosine similarity.
    # Convert numpy array to list — pgvector expects list input.
    emb_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
    similarity_expr = 1.0 - PatentPublication.embedding.cosine_distance(emb_list)

    stmt = (
        select(
            PatentPublication,
            similarity_expr.label("similarity"),
        )
        .where(
            PatentPublication.embedding.isnot(None),
            PatentPublication.id != patent_id,
            PatentPublication.filing_date > cutoff_date,
            similarity_expr >= min_similarity,
        )
        .order_by(similarity_expr.desc())
        .limit(top_k)
    )

    result = await session.execute(stmt)
    rows = result.fetchall()

    evidence_rows: list[dict] = []
    for source, similarity in rows:
        sim = float(similarity)
        source_cpc = set(source.cpc or [])
        shared_cpc = list(target_cpc & source_cpc)

        tier, confidence = _compute_similarity_tier(
            similarity=sim,
            shared_cpc=len(shared_cpc),
            source_assignees=source.assignees or [],
            target_assignees=target_assignees,
        )

        if tier == "excluded":
            continue

        evidence_rows.append({
            "patent_publication_id": patent_id,
            "source_type": "similar_newer_patent",
            "source_patent_id": source.id,
            "source_patent_doc_id": source.doc_id,
            "source_patent_title": source.title,
            "source_patent_assignee": (source.assignees or [None])[0],
            "source_patent_filing_date": source.filing_date,
            "source_patent_cpc": source.cpc or [],
            "matched_cpc": shared_cpc,
            "cpc_overlap_count": len(shared_cpc),
            "similarity_score": sim,
            "citation_direction": None,
            "evidence_tier": tier,
            "evidence_confidence": confidence,
        })

    return evidence_rows
