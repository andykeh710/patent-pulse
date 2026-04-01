import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.summarizer import PatentSummarizer, REQUIRED_SUMMARY_FIELDS
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication


@pytest.fixture
def mock_patent() -> PatentPublication:
    patent = PatentPublication(
        doc_id="USPTO:TEST001",
        office="USPTO",
        publication_number="TEST001",
        title="Test Patent Title",
        abstract="This is a test abstract describing the invention.",
        claims_text="1. A method comprising: step A; step B; step C.",
        description_text="Detailed description of the invention...",
        cpc=["G06F 21/00", "H04L 9/32"],
    )
    return patent


@pytest.fixture
def valid_summary_response() -> dict:
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
        "source_spans": [
            {"quote": "step A; step B", "field": "claims"}
        ],
    }


class TestPatentSummarizer:
    def test_build_prompt_includes_patent_content(self, mock_patent: PatentPublication) -> None:
        summarizer = PatentSummarizer(api_key="test-key")
        prompt = summarizer._build_prompt(mock_patent)

        assert mock_patent.title in prompt
        assert mock_patent.abstract in prompt
        assert "G06F 21/00" in prompt

    def test_parse_valid_json(self, valid_summary_response: dict) -> None:
        summarizer = PatentSummarizer(api_key="test-key")
        raw = json.dumps(valid_summary_response)
        result = summarizer._parse_and_validate(raw)

        assert result["what_it_is"] == "A test invention"
        assert len(result["who_should_care"]) == 2

    def test_parse_strips_markdown_fences(self, valid_summary_response: dict) -> None:
        summarizer = PatentSummarizer(api_key="test-key")
        raw = f"```json\n{json.dumps(valid_summary_response)}\n```"
        result = summarizer._parse_and_validate(raw)

        assert result["what_it_is"] == "A test invention"

    def test_parse_raises_on_missing_fields(self) -> None:
        summarizer = PatentSummarizer(api_key="test-key")
        incomplete = {"what_it_is": "Test"}

        with pytest.raises(SummarizationError, match="missing required fields"):
            summarizer._parse_and_validate(json.dumps(incomplete))

    def test_parse_enforces_speculative_label(self) -> None:
        summarizer = PatentSummarizer(api_key="test-key")
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
        result = summarizer._parse_and_validate(json.dumps(response))

        assert result["novel_applications"][0]["label"] == "SPECULATIVE"

    @patch("app.ai.summarizer.anthropic.Anthropic")
    def test_summarize_calls_api(
        self,
        mock_anthropic: MagicMock,
        mock_patent: PatentPublication,
        valid_summary_response: dict,
    ) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=json.dumps(valid_summary_response))]
        mock_client.messages.create.return_value = mock_message

        summarizer = PatentSummarizer(api_key="test-key")
        result = summarizer.summarize(mock_patent)

        assert result["what_it_is"] == "A test invention"
        mock_client.messages.create.assert_called_once()


class TestIndependentClaimsExtraction:
    def test_extracts_independent_claims(self) -> None:
        claims = """1. A method comprising step A and step B.
        
2. The method of claim 1, further comprising step C.

3. A system configured to perform step A.

4. The system of claim 3, wherein step A includes substep X."""

        summarizer = PatentSummarizer(api_key="test-key")
        result = summarizer._extract_independent_claims(claims)

        assert "A method comprising" in result
        assert "A system configured" in result
        assert "method of claim 1" not in result
        assert "system of claim 3" not in result

    def test_handles_empty_claims(self) -> None:
        summarizer = PatentSummarizer(api_key="test-key")
        assert summarizer._extract_independent_claims(None) == ""
        assert summarizer._extract_independent_claims("") == ""

    def test_fallback_to_truncated_claims(self) -> None:
        claims = "2. The method of claim 1.\n3. The method of claim 2."
        summarizer = PatentSummarizer(api_key="test-key")
        result = summarizer._extract_independent_claims(claims)
        assert len(result) > 0
