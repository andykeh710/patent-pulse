"""Tests for Sprint 5 scoring engine."""
from datetime import date, timedelta

from app.usage.scoring import compute_usage_signal_score


def _evidence(tier="medium", assignee="Acme", filing_days_ago=1000, cpc_overlap=1, source_type="forward_citation"):
    return {
        "evidence_tier": tier,
        "source_type": source_type,
        "source_patent_filing_date": date.today() - timedelta(days=filing_days_ago),
        "source_patent_assignee": assignee,
        "cpc_overlap_count": cpc_overlap,
        "matched_cpc": ["G06F", "H04L"] if cpc_overlap >= 2 else ["G06F"],
    }


def test_empty_evidence_returns_zero():
    """Zero evidence → score=0, confidence=insufficient."""
    result = compute_usage_signal_score([])
    assert result["score"] == 0
    assert result["confidence"] == "low"  # score 0 → low
    assert result["evidence_count"] == 0


def test_all_strong_evidence_scores_high():
    """Multiple strong recent evidence → high score and confidence."""
    rows = [
        _evidence("strong", "Acme", 365, 3, "forward_citation"),
        _evidence("strong", "Beta", 500, 3, "similar_newer_patent"),
        _evidence("strong", "Gamma", 200, 2, "forward_citation"),
    ]
    result = compute_usage_signal_score(rows)
    assert result["score"] >= 60
    assert result["confidence"] in ("medium", "high")
    breakdown = result["breakdown"]
    assert breakdown["evidence_strength"] > 0
    assert breakdown["recency"] > 0
    assert breakdown["diversity"] == 15  # 2+ sources
    assert breakdown["assignee_activity"] == 10  # 3 distinct
    assert breakdown["total"] == result["score"]


def test_mixed_tiers_mid_range_score():
    """Mixed tiers produce middle-range score."""
    rows = [
        _evidence("strong", "Acme", 400, 2),
        _evidence("medium", "Beta", 1200, 1),
        _evidence("weak", "Gamma", 3000, 1),
    ]
    result = compute_usage_signal_score(rows)
    assert 30 <= result["score"] <= 70
    assert result["evidence_count"] == 3
    assert result["by_tier"]["strong"] == 1
    assert result["by_tier"]["medium"] == 1
    assert result["by_tier"]["weak"] == 1


def test_self_citation_penalizes_score():
    """Heavy self-citation flag=True, score reduced."""
    rows = [
        _evidence("strong", assignee="SelfCorp", filing_days_ago=300, cpc_overlap=2),
        _evidence("strong", assignee="SelfCorp", filing_days_ago=500, cpc_overlap=1),
    ]
    result = compute_usage_signal_score(rows, patent_assignees=["SelfCorp"])
    assert result["has_self_citation_risk"] is True
    assert result["self_citation_ratio"] == 1.0
    # Self-citation at 1/3 weight: strength should be noticeably reduced.
    assert result["breakdown"]["evidence_strength"] < 20


def test_old_evidence_no_recency_contribution():
    """Evidence >15 years old contributes 0 to recency."""
    rows = [
        _evidence("medium", "OldCorp", filing_days_ago=365 * 16, cpc_overlap=1),
    ]
    result = compute_usage_signal_score(rows)
    assert result["breakdown"]["recency"] == 0
    assert result["score"] < 40  # Only evidence_strength contributes.


def test_breakdown_sums_to_total():
    """Every component in breakdown sums to the score."""
    rows = [
        _evidence("strong", "A", 100, 3),
        _evidence("medium", "B", 800, 2, "similar_newer_patent"),
        _evidence("weak", "C", 2500, 1),
    ]
    result = compute_usage_signal_score(rows)
    b = result["breakdown"]
    total_from_components = (
        b["evidence_strength"]
        + b["recency"]
        + b["diversity"]
        + b["assignee_activity"]
        + b["cpc_overlap"]
    )
    assert total_from_components == result["score"]
