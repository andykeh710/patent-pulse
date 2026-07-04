"""Tests for Sprint 5 usage signal narrative module."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.ai.usage_narrative import (
    _contains_forbidden,
    build_payload,
    generate_usage_narrative,
    validate_output,
)
from app.core.exceptions import SummarizationError

# ── test data ────────────────────────────────────────────────────────


def _signal(**overrides):
    defaults = {
        "score": 55,
        "confidence": "medium",
        "evidence_count": 3,
        "by_tier": {"strong": 1, "medium": 1, "weak": 1},
        "by_source": {"forward_citation": 2, "similar_newer_patent": 1},
        "top_companies": ["Acme", "Beta"],
    }
    defaults.update(overrides)
    return defaults


def _evidence(**overrides):
    defaults = {
        "source_patent_title": "Test patent title",
        "source_patent_assignee": "TestCorp",
        "evidence_tier": "medium",
        "similarity_score": 0.82,
        "source_patent_filing_date": "2024-01-15",
    }
    defaults.update(overrides)
    return defaults


# ── unit tests ───────────────────────────────────────────────────────


def test_contains_forbidden():
    """Detect forbidden phrases in text."""
    assert _contains_forbidden("this technology is free to use") == ["free to use"]
    assert _contains_forbidden("this patent is used by many companies") == [
        "this patent is used",
        "is used by",
    ]
    assert _contains_forbidden("this appears related to newer patents") == []


def test_build_payload_structure():
    """Payload has all expected keys with non-empty values."""
    payload = build_payload(
        _signal(),
        [_evidence()],
        patent_title="Example",
        patent_assignee="Acme",
        expiry_status="expired_estimated",
        expiry_confidence="medium",
    )
    assert payload["patent_title"] == "Example"
    assert payload["evidence_count"] == "3"
    assert payload["signal_score"] == "55"
    assert "Test patent title" in payload["evidence_list"]


def test_validate_output_normalizes():
    """Valid LLM response passes validation and gets defaults."""
    raw = {
        "summary": "Evidence suggests continued relevance in computing.",
        "evidence_summary": "3 evidence pieces found.",
    }
    result = validate_output(raw)
    assert "computing" in result["summary"]
    assert len(result["limitations"]) >= 1
    assert "patent-based only" in result["limitations"][0]
    assert result["market_categories"] == []
    assert result["related_companies"] == []


def test_validate_output_rejects_forbidden():
    """Forbidden phrase raises SummarizationError."""
    raw = {
        "summary": "This patent is used in many modern smartphones.",
        "evidence_summary": "Evidence confirms usage.",
    }
    with pytest.raises(SummarizationError, match="Forbidden phrases"):
        validate_output(raw)


def test_validate_output_adds_disclaimer():
    """Disclaimer is always first in limitations."""
    raw = {"summary": "OK.", "evidence_summary": "OK.", "limitations": ["Custom caveat"]}
    result = validate_output(raw)
    assert (
        result["limitations"][0]
        == "Evidence is patent-based only — no product-level verification has been performed."
    )
    assert "Custom caveat" in result["limitations"]


# ── integration tests (mocked LLM) ───────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_generate_writes_artifact(db_session):
    """generate_usage_narrative writes AIArtifact with validated content."""
    from sqlalchemy import select

    from app.core.ai_models import AIArtifact

    patent_id = uuid4()
    signal = _signal()
    evidence = [_evidence()]

    # Mock the LLM client to return a valid response.
    mock_response = MagicMock()
    mock_response.content_json = {
        "summary": "Evidence suggests this patent has continued relevance in data processing.",
        "evidence_summary": "3 evidence pieces including forward citations and similar patents.",
        "market_categories": ["G06F", "H04L"],
        "related_companies": ["Acme Corp"],
        "limitations": [
            "Evidence is patent-based only — no product-level verification has been performed.",
            "Semantic similarity does not confirm commercial use.",
        ],
    }
    mock_response.artifact_id = uuid4()

    async def mock_complete(session, request):
        artifact = AIArtifact(
            id=mock_response.artifact_id,
            artifact_type="usage_signal_narrative",
            model="claude-sonnet-4-20250514",
            prompt_name="usage_signal_narrative",
            prompt_version=1,
            prompt_hash="mock_hash_abc123",
            input_hash="mock_input_def456",
            status="complete",
            content_json=mock_response.content_json,
        )
        session.add(artifact)
        await session.commit()
        return mock_response

    with patch(
        "app.ai.usage_narrative.get_llm_client",
        return_value=MagicMock(complete=mock_complete),
    ):
        result, aid = await generate_usage_narrative(
            db_session,
            signal,
            evidence,
            patent_id,
            patent_title="Test Patent",
            patent_assignee="TestCorp",
        )

    assert "data processing" in result["summary"]
    assert result["market_categories"] == ["G06F", "H04L"]
    assert len(result["limitations"]) >= 2

    # Verify artifact was written.
    stmt = select(AIArtifact).where(AIArtifact.id == aid)
    res = await db_session.execute(stmt)
    artifact = res.scalar_one_or_none()
    assert artifact is not None
    assert artifact.content_json is not None


@pytest.mark.asyncio(loop_scope="function")
async def test_generate_falls_back_on_retry_exhaustion(db_session):
    """Forbidden phrases + retries exhausted → fallback narrative."""
    patent_id = uuid4()

    # Mock that always returns forbidden content.
    mock_response = MagicMock()
    mock_response.content_json = {
        "summary": "This patent is used widely.",
        "evidence_summary": "OK.",
    }
    mock_response.artifact_id = uuid4()

    async def mock_complete(session, request):
        return mock_response

    with patch(
        "app.ai.usage_narrative.get_llm_client",
        return_value=MagicMock(complete=mock_complete),
    ):
        result, aid = await generate_usage_narrative(
            db_session,
            _signal(),
            [_evidence()],
            patent_id,
        )

    # Should return fallback narrative after retries.
    assert result["summary"] == ""
    assert len(result["limitations"]) >= 2
