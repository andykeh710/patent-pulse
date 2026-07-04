"""
Patent summarizer.

Phase 0 refactor: delegates the actual LLM call to
:mod:`app.ai.llm_client` so every summary becomes a cached
``AIArtifact(summary)`` row, keyed by ``(prompt_hash, input_hash)``.

Two entry points are exposed:

* :class:`PatentSummarizer` (sync, legacy) — kept for back-compat with
  non-async call sites (currently the mock path in tests). The live
  ``summarize()`` method now raises to discourage new use; callers should
  migrate to :func:`summarize_patent` (async) which uses the cache.
* :func:`summarize_patent` (async) — preferred entry point. Returns the
  parsed summary dict AND the produced ``AIArtifact`` id.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

SUMMARY_PROMPT_NAME = "summarize"
SUMMARY_PROMPT_VERSION = 1

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


# ---------------------------------------------------------------------------
# Claims extraction helpers (pure functions; reused by the async path)
# ---------------------------------------------------------------------------


def extract_independent_claims(claims_text: str | None) -> str:
    """Return only the independent claims from a full claims block."""
    if not claims_text:
        return ""

    lines = claims_text.split("\n")
    independent: list[str] = []
    current_claim: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        claim_start = re.match(r"^(\d+)\.\s*", stripped)
        if claim_start:
            if current_claim:
                claim_text = " ".join(current_claim)
                if not _references_other_claim(claim_text):
                    independent.append(claim_text)
            current_claim = [stripped]
        else:
            current_claim.append(stripped)

    if current_claim:
        claim_text = " ".join(current_claim)
        if not _references_other_claim(claim_text):
            independent.append(claim_text)

    result = "\n\n".join(independent[:5])
    return result if result else claims_text[:1500]


def _references_other_claim(claim_text: str) -> bool:
    first_100 = claim_text[:100].lower()
    patterns = [
        r"claim\s+\d+",
        r"claims?\s+\d+\s*(and|or|to)\s*\d+",
        r"according to claim",
        r"as (claimed|defined|set forth) in claim",
    ]
    return any(re.search(p, first_100) for p in patterns)


def build_summary_payload(patent: PatentPublication) -> dict[str, Any]:
    """Build the render payload fed to the summarize_v1 prompt."""
    return {
        "title": patent.title or "(no title provided)",
        "abstract": patent.abstract or "(no abstract provided)",
        "claims_text": extract_independent_claims(patent.claims_text) or "(no claims available)",
        "description_excerpt": (patent.description_text or "")[:2000]
        or "(no description available)",
        "cpc_codes": ", ".join(patent.cpc or []) or "(no classifications)",
    }


def validate_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Enforce required fields + label invariants."""
    missing = REQUIRED_SUMMARY_FIELDS - set(summary.keys())
    if missing:
        raise SummarizationError(f"Summary missing required fields: {missing}")

    for app in summary.get("novel_applications", []) or []:
        if isinstance(app, dict) and app.get("label") != "SPECULATIVE":
            app["label"] = "SPECULATIVE"

    return summary


# ---------------------------------------------------------------------------
# Async (cached) summarization entry point
# ---------------------------------------------------------------------------


async def summarize_patent(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
) -> tuple[dict[str, Any], UUID]:
    """
    Summarize a patent via the cached LLM client.

    Returns ``(summary_dict, artifact_id)``. Safe to call repeatedly:
    subsequent calls with identical inputs will hit the cache and return
    in milliseconds at $0.
    """
    payload = build_summary_payload(patent)
    request = LLMRequest(
        artifact_type="summary",
        prompt_name=SUMMARY_PROMPT_NAME,
        prompt_version=SUMMARY_PROMPT_VERSION,
        input_payload=payload,
        patent_publication_id=patent.id,
        run_id=run_id,
        tier="summary",
        max_tokens=2048,
        expected_output_tokens=900,
    )
    client = get_llm_client()
    try:
        response = await client.complete(session, request)
    except anthropic.APIError as e:  # pragma: no cover - network path
        raise SummarizationError(f"AI API error: {e}") from e

    content = response.content_json
    if content is None:
        # The model returned plain text; surface it as a parse error so
        # the caller can choose to retry with a stricter prompt version.
        raise SummarizationError(
            "Summary artifact did not parse as JSON; see artifact "
            f"{response.artifact_id} for raw text."
        )
    validated = validate_summary(content)
    return validated, response.artifact_id


# ---------------------------------------------------------------------------
# Legacy sync class (kept only so existing tests that import
# ``PatentSummarizer``/``MockSummarizer`` still work; new code should use
# ``summarize_patent`` above).
# ---------------------------------------------------------------------------


class PatentSummarizer:
    """Deprecated: use :func:`summarize_patent` instead."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key
        self.model = model

    def summarize(self, patent: PatentPublication) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError(
            "PatentSummarizer.summarize() is deprecated. Use "
            "app.ai.summarizer.summarize_patent(session, patent) which "
            "routes through the cached llm_client."
        )


class MockSummarizer:
    """Mock summarizer for testing without API calls."""

    def summarize(self, patent: PatentPublication) -> dict[str, Any]:
        return {
            "what_it_is": f"Mock summary for {patent.title or 'untitled patent'}",
            "problem_solved": "Test problem",
            "how_it_works": "Test mechanism",
            "commercial_significance": "Test significance",
            "who_should_care": ["Test role 1", "Test role 2"],
            "novel_applications": [{"application": "Test application", "label": "SPECULATIVE"}],
            "confidence_note": "This is a mock summary for testing",
            "source_spans": [],
        }
