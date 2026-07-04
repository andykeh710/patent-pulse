"""Tests for A/B subject line variants (Phase 5 PR 1)."""

from app.email.weekly_briefing import SUBJECT_VARIANTS, build_subject, pick_variant


def test_pick_variant_is_deterministic():
    """Same user_id always gets the same variant."""
    uid = "550e8400-e29b-41d4-a716-446655440000"
    v1 = pick_variant(uid)
    v2 = pick_variant(uid)
    assert v1 == v2
    assert v1 in SUBJECT_VARIANTS


def test_pick_variant_distributes():
    """Different user_ids should get different variants (over a sample)."""
    variants_seen = set()
    for i in range(20):
        v = pick_variant(f"user-{i}")
        variants_seen.add(v)
    # Should see at least 2 different variants across 20 users
    assert len(variants_seen) >= 2


def test_pick_variant_all_valid():
    """Every variant returned is a known key."""
    for i in range(50):
        v = pick_variant(f"user-{i}")
        assert v in SUBJECT_VARIANTS, f"Unknown variant: {v}"


def test_build_subject_variant_a():
    """Variant A uses signal count."""
    items = [
        {"title": "Patent X", "type": "notable", "source": "Acme"},
        {"title": "Patent Y", "type": "trend", "source": "Beta"},
        {"title": "Patent Z", "type": "expiring", "source": "Gamma"},
    ]
    subj = build_subject("A", items, topic_count=0, company_count=0)
    assert "3" in subj  # signal count
    assert "signals" in subj


def test_build_subject_variant_b():
    """Variant B uses company name."""
    items = [
        {"title": "Patent X", "type": "company", "source": "Acme Corp"},
        {"title": "Patent Y", "type": "notable", "source": "Beta"},
    ]
    subj = build_subject("B", items)
    assert "Acme Corp" in subj
    assert "filing again" in subj.lower()


def test_build_subject_variant_c():
    """Variant C uses topic name."""
    items = [
        {"title": "Patent X", "type": "notable", "source": "Acme", "topic_name": "AI/ML"},
    ]
    subj = build_subject("C", items)
    assert "AI/ML" in subj
    assert "momentum" in subj.lower()


def test_build_subject_variant_d():
    """Variant D uses top patent title."""
    items = [
        {
            "title": "System and Method for Secure Authentication",
            "type": "notable",
            "source": "Acme",
        },
    ]
    subj = build_subject("D", items)
    assert "System and Method for Secure Authentication" in subj
    assert "interesting patent" in subj.lower()


def test_build_subject_fallback():
    """When items are empty, still returns a valid subject."""
    subj = build_subject("A", [])
    assert len(subj) > 0
    assert "signals" in subj


def test_build_subject_unknown_variant_falls_back_to_a():
    """Unknown variant key defaults to A."""
    subj = build_subject("Z", [{"title": "X", "type": "notable", "source": "Y"}])
    assert "signal" in subj.lower()
