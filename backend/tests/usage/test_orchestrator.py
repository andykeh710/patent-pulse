"""Tests for Sprint 5 evidence collector orchestrator."""

from uuid import uuid4

from app.usage.collector import dedup_evidence


def test_dedup_keeps_higher_tier():
    """When same source_patent_id appears in both, keep higher tier."""
    pid = uuid4()
    citation = [
        {
            "source_patent_id": pid,
            "evidence_tier": "medium",
            "source_type": "forward_citation",
        }
    ]
    similarity = [
        {
            "source_patent_id": pid,
            "evidence_tier": "strong",
            "source_type": "similar_newer_patent",
        }
    ]
    result = dedup_evidence(citation, similarity)
    assert len(result) == 1
    assert result[0]["evidence_tier"] == "strong"
    assert result[0]["source_type"] == "similar_newer_patent"


def test_dedup_prefers_citation_on_tie():
    """Tie in tier → prefer citation (more direct signal)."""
    pid = uuid4()
    citation = [
        {
            "source_patent_id": pid,
            "evidence_tier": "strong",
            "source_type": "forward_citation",
        }
    ]
    similarity = [
        {
            "source_patent_id": pid,
            "evidence_tier": "strong",
            "source_type": "similar_newer_patent",
        }
    ]
    result = dedup_evidence(citation, similarity)
    assert len(result) == 1
    # Citation wins on tie.
    assert result[0]["source_type"] == "forward_citation"


def test_dedup_preserves_unique_ids():
    """Non-overlapping evidence is preserved."""
    p1 = uuid4()
    p2 = uuid4()
    citation = [
        {"source_patent_id": p1, "evidence_tier": "medium", "source_type": "forward_citation"}
    ]
    similarity = [
        {"source_patent_id": p2, "evidence_tier": "strong", "source_type": "similar_newer_patent"}
    ]
    result = dedup_evidence(citation, similarity)
    assert len(result) == 2
