"""
Evidence collection orchestrator (Sprint 5).

Runs both collectors and deduplicates evidence by source_patent_id.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.usage.citation_collector import collect_citation_evidence
from app.usage.similarity_collector import collect_similar_evidence

TIER_WEIGHTS = {"strong": 3, "medium": 2, "weak": 1, "excluded": 0}


def dedup_evidence(
    citation_rows: list[dict],
    similarity_rows: list[dict],
) -> list[dict]:
    """Merge evidence, deduplicating by source_patent_id.

    When a source patent appears in both lists, keep the row with the
    higher tier. If tiers are equal, keep the citation (more direct).
    """
    merged: dict[str, dict] = {}

    for row in similarity_rows:
        pid = str(row["source_patent_id"])
        merged[pid] = row

    for row in citation_rows:
        pid = str(row["source_patent_id"])
        existing = merged.get(pid)
        if existing is None:
            merged[pid] = row
        else:
            # Keep the higher-tier evidence.
            existing_weight = TIER_WEIGHTS.get(existing["evidence_tier"], 0)
            new_weight = TIER_WEIGHTS.get(row["evidence_tier"], 0)
            if new_weight > existing_weight:
                merged[pid] = row
            elif new_weight == existing_weight:
                # Tie — prefer citation (more direct signal).
                merged[pid] = row

    return list(merged.values())


async def collect_all_evidence(
    session: AsyncSession,
    patent_id: UUID,
    *,
    similarity_top_k: int = 10,
) -> tuple[list[dict], dict]:
    """Collect and merge all usage signal evidence for a patent.

    Returns (merged_evidence_list, stats_dict).
    """
    citations = await collect_citation_evidence(session, patent_id)
    similarity = await collect_similar_evidence(session, patent_id, top_k=similarity_top_k)
    merged = dedup_evidence(citations, similarity)

    by_tier: dict[str, int] = {"strong": 0, "medium": 0, "weak": 0}
    by_source: dict[str, int] = {"forward_citation": 0, "similar_newer_patent": 0}
    for row in merged:
        by_tier[row["evidence_tier"]] = by_tier.get(row["evidence_tier"], 0) + 1
        by_source[row["source_type"]] = by_source.get(row["source_type"], 0) + 1

    stats = {
        "total_evidence": len(merged),
        "citation_count": len(citations),
        "similarity_count": len(similarity),
        "dedup_removed": len(citations) + len(similarity) - len(merged),
        "by_tier": by_tier,
        "by_source": by_source,
    }

    return merged, stats
