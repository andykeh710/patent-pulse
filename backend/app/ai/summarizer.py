import json
import logging
import re
from typing import Any

import anthropic

from app.ai.prompts import SUMMARY_SCHEMA_DESCRIPTION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

REQUIRED_SUMMARY_FIELDS = {
    "what_it_is",
    "problem_solved",
    "how_it_works",
    "commercial_significance",
    "who_should_care",
    "novel_applications",
    "confidence_note",
    "source_spans",
}


class PatentSummarizer:
    """
    Generates AI-powered summaries of patents using Claude.

    Transforms dense patent text into structured, accessible summaries
    for business and strategy professionals.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def summarize(self, patent: PatentPublication) -> dict[str, Any]:
        """
        Generate a structured summary for a patent.

        Args:
            patent: PatentPublication model instance

        Returns:
            Dict matching the summary schema

        Raises:
            SummarizationError: If summarization fails
        """
        prompt = self._build_prompt(patent)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = message.content[0].text
            summary = self._parse_and_validate(raw_text)

            logger.info(f"Successfully summarized patent {patent.doc_id}")
            return summary

        except anthropic.APIError as e:
            logger.error(f"Claude API error for {patent.doc_id}: {e}")
            raise SummarizationError(f"Claude API error: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response for {patent.doc_id}: {e}")
            raise SummarizationError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            logger.error(f"Summarization failed for {patent.doc_id}: {e}")
            raise SummarizationError(str(e)) from e

    def _build_prompt(self, patent: PatentPublication) -> str:
        """Build the user prompt with patent content."""
        independent_claims = self._extract_independent_claims(patent.claims_text)
        description_excerpt = (patent.description_text or "")[:2000]

        return USER_PROMPT_TEMPLATE.format(
            title=patent.title or "(no title provided)",
            abstract=patent.abstract or "(no abstract provided)",
            claims_text=independent_claims or "(no claims available)",
            description_excerpt=description_excerpt or "(no description available)",
            cpc_codes=", ".join(patent.cpc or []) or "(no classifications)",
            schema_description=SUMMARY_SCHEMA_DESCRIPTION,
        )

    def _extract_independent_claims(self, claims_text: str | None) -> str:
        """
        Extract only independent claims from full claims text.

        Independent claims don't reference other claim numbers in their preamble.
        """
        if not claims_text:
            return ""

        lines = claims_text.split("\n")
        independent = []

        current_claim = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            claim_start = re.match(r"^(\d+)\.\s*", line)
            if claim_start:
                if current_claim:
                    claim_text = " ".join(current_claim)
                    if not self._references_other_claim(claim_text):
                        independent.append(claim_text)
                current_claim = [line]
            else:
                current_claim.append(line)

        if current_claim:
            claim_text = " ".join(current_claim)
            if not self._references_other_claim(claim_text):
                independent.append(claim_text)

        result = "\n\n".join(independent[:5])
        return result if result else claims_text[:1500]

    def _references_other_claim(self, claim_text: str) -> bool:
        """Check if a claim references another claim number."""
        first_100_chars = claim_text[:100].lower()
        patterns = [
            r"claim\s+\d+",
            r"claims?\s+\d+\s*(and|or|to)\s*\d+",
            r"according to claim",
            r"as (claimed|defined|set forth) in claim",
        ]
        return any(re.search(p, first_100_chars) for p in patterns)

    def _parse_and_validate(self, raw_text: str) -> dict[str, Any]:
        """
        Parse and validate Claude's JSON response.

        Handles markdown code fences if present.
        """
        text = raw_text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        data = json.loads(text)

        missing = REQUIRED_SUMMARY_FIELDS - set(data.keys())
        if missing:
            raise SummarizationError(f"Summary missing required fields: {missing}")

        for app in data.get("novel_applications", []):
            if isinstance(app, dict) and app.get("label") != "SPECULATIVE":
                app["label"] = "SPECULATIVE"

        return data


class MockSummarizer:
    """Mock summarizer for testing without API calls."""

    def summarize(self, patent: PatentPublication) -> dict[str, Any]:
        return {
            "what_it_is": f"Mock summary for {patent.title or 'untitled patent'}",
            "problem_solved": "Test problem",
            "how_it_works": "Test mechanism",
            "commercial_significance": "Test significance",
            "who_should_care": ["Test role 1", "Test role 2"],
            "novel_applications": [
                {"application": "Test application", "label": "SPECULATIVE"}
            ],
            "confidence_note": "This is a mock summary for testing",
            "source_spans": [],
        }
