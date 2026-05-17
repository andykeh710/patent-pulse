"""Tests for app.ai.summarizer (module-level helpers + cached path)."""
import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.ai.llm_client import LLMResponse
from app.ai.summarizer import (
    REQUIRED_SUMMARY_FIELDS,
    build_summary_payload,
    extract_independent_claims,
    summarize_patent,
    validate_summary,
)
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication


@pytest.fixture
def mock_patent() -> PatentPublication:
    return PatentPublication(
        id=uuid4(),
        doc_id="USPTO:TEST001",
        office="USPTO",
        publication_number="TEST001",
        title="Test Patent Title",
        abstract="This is a test abstract describing the invention.",
        claims_text="1. A method comprising: step A; step B; step C.",
        description_text="Detailed description of the invention...",
        cpc=["G06F 21/00", "H04L 9/32"],
    )


@pytest.fixture
def valid_summary_response() -> dict[str, Any]:
    return {
        "what_it_is": "A test invention",
        "problem_solved": "Solves test problem",
        "how_it_works": "Works via test mechanism",
        "commercial_significance": "Test significance",
        "who_should_care": ["Engineers", "Product managers"],
        "novel_applications": [
            {"application": "Could be used for X", "label": "SPECULATIVE"}
        ],
        "confidence_note": "High confidence",
        "source_spans": [{"quote": "step A; step B", "field": "claims"}],
    }


class TestSummaryPayload:
    def test_payload_has_all_render_keys(self, mock_patent: PatentPublication) -> None:
        payload = build_summary_payload(mock_patent)
        assert payload["title"] == mock_patent.title
        assert payload["abstract"] == mock_patent.abstract
        assert "G06F 21/00" in payload["cpc_codes"]
        assert "step A" in payload["claims_text"]

    def test_payload_handles_missing_fields(self) -> None:
        bare = PatentPublication(
            id=uuid4(),
            doc_id="USPTO:EMPTY",
            office="USPTO",
            publication_number="EMPTY",
        )
        payload = build_summary_payload(bare)
        assert payload["title"] == "(no title provided)"
        assert payload["abstract"] == "(no abstract provided)"
        assert payload["cpc_codes"] == "(no classifications)"


class TestValidateSummary:
    def test_accepts_valid_response(self, valid_summary_response: dict) -> None:
        result = validate_summary(valid_summary_response)
        assert result["what_it_is"] == "A test invention"

    def test_raises_on_missing_fields(self) -> None:
        with pytest.raises(SummarizationError, match="missing required fields"):
            validate_summary({"what_it_is": "Test"})

    def test_enforces_speculative_label(self) -> None:
        response = {
            "what_it_is": "Test",
            "problem_solved": "Test",
            "how_it_works": "Test",
            "commercial_significance": "Test",
            "who_should_care": ["Test"],
            "novel_applications": [
                {"application": "Test app", "label": "CONFIRMED"}
            ],
            "confidence_note": "Test",
            "source_spans": [],
        }
        result = validate_summary(response)
        assert result["novel_applications"][0]["label"] == "SPECULATIVE"

    def test_required_fields_constant(self) -> None:
        # Sanity: the constant matches what validate_summary actually enforces.
        assert "what_it_is" in REQUIRED_SUMMARY_FIELDS
        assert "novel_applications" in REQUIRED_SUMMARY_FIELDS


class TestCachedSummarizePatent:
    @pytest.mark.asyncio
    async def test_marks_plain_text_artifact_failed(
        self, mock_patent: PatentPublication
    ) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.commits = 0

            async def commit(self) -> None:
                self.commits += 1

        artifact = SimpleNamespace(status="complete", error_message=None)
        response = LLMResponse(
            artifact_id=uuid4(),
            artifact_type="summary",
            content_json=None,
            content_text="not json",
            model="claude-sonnet-4-20250514",
            prompt_name="summarize",
            prompt_version=1,
            prompt_hash="prompt-hash",
            input_hash="input-hash",
            input_tokens=1,
            output_tokens=1,
            actual_cost_usd=0.01,
            cache_hit=False,
            created_at=datetime.utcnow(),
            artifact=artifact,
        )
        client = MagicMock()
        client.complete = AsyncMock(return_value=response)
        session = FakeSession()

        with patch("app.ai.summarizer.get_llm_client", return_value=client):
            with pytest.raises(SummarizationError, match="did not parse as JSON"):
                await summarize_patent(session, mock_patent)

        assert artifact.status == "failed"
        assert artifact.error_message == "Summary artifact did not parse as JSON."
        assert session.commits == 1

    @pytest.mark.asyncio
    async def test_invalid_cached_artifact_decrements_run_cached_count(
        self, mock_patent: PatentPublication
    ) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.commits = 0
                self.run = SimpleNamespace(cached_count=1)

            async def commit(self) -> None:
                self.commits += 1

            async def execute(self, statement):
                self.run.cached_count = max(0, self.run.cached_count - 1)

        run_id = uuid4()
        artifact = SimpleNamespace(status="complete", error_message=None)
        response = LLMResponse(
            artifact_id=uuid4(),
            artifact_type="summary",
            content_json=None,
            content_text="not json",
            model="claude-sonnet-4-20250514",
            prompt_name="summarize",
            prompt_version=1,
            prompt_hash="prompt-hash",
            input_hash="input-hash",
            input_tokens=1,
            output_tokens=1,
            actual_cost_usd=0.01,
            cache_hit=True,
            created_at=datetime.utcnow(),
            artifact=artifact,
        )
        client = MagicMock()
        client.complete = AsyncMock(return_value=response)
        session = FakeSession()

        with patch("app.ai.summarizer.get_llm_client", return_value=client):
            with pytest.raises(SummarizationError, match="did not parse as JSON"):
                await summarize_patent(session, mock_patent, run_id=run_id)

        assert session.run.cached_count == 0
        assert session.commits == 1


class TestIndependentClaimsExtraction:
    def test_extracts_independent_claims(self) -> None:
        claims = """1. A method comprising step A and step B.

2. The method of claim 1, further comprising step C.

3. A system configured to perform step A.

4. The system of claim 3, wherein step A includes substep X."""
        result = extract_independent_claims(claims)
        assert "A method comprising" in result
        assert "A system configured" in result
        assert "method of claim 1" not in result
        assert "system of claim 3" not in result

    def test_handles_empty_claims(self) -> None:
        assert extract_independent_claims(None) == ""
        assert extract_independent_claims("") == ""

    def test_fallback_to_truncated_claims(self) -> None:
        claims = "2. The method of claim 1.\n3. The method of claim 2."
        result = extract_independent_claims(claims)
        assert len(result) > 0
