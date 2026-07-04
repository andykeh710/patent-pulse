"""Tests for weekly digest AI module."""

import pytest

from app.ai.weekly_digest import build_payload, validate_output
from app.core.exceptions import SummarizationError


def test_build_payload_structure():
    topics = [{"name": "AI", "match_count": 3, "keywords": ["ml"], "cpc_prefixes": ["G06N"]}]
    matches = [
        {
            "topic_name": "AI",
            "title": "Patent X",
            "doc_id": "USPTO:123",
            "assignee": "Acme",
            "cpc": ["G06N"],
        }
    ]
    payload = build_payload(topics, matches)
    assert "topic_list" in payload
    assert "matches_list" in payload
    assert "AI" in payload["topic_list"]
    assert "Patent X" in payload["matches_list"]


def test_validate_output_rejects_forbidden_phrase():
    with pytest.raises(SummarizationError):
        validate_output(
            {
                "headline": "This patent is definitely used in product X",
                "highlights": [],
                "patterns": "",
                "caveats": [],
            }
        )


def test_validate_output_adds_disclaimer():
    result = validate_output(
        {"headline": "A headline", "highlights": [], "patterns": "", "caveats": []}
    )
    assert (
        result["caveats"][0]
        == "Evidence is patent-based only — verify with official registers before acting."
    )


def test_validate_output_defaults_missing_fields():
    result = validate_output({})
    assert result["headline"] == ""
    assert result["highlights"] == []
    assert result["patterns"] == ""
    assert len(result["caveats"]) >= 1
