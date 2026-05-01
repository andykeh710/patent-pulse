"""
Patent tagger.

Phase 1 module that produces structured tags for a patent using Claude
Haiku via :mod:`app.ai.llm_client`. Every tag output is durable as
``AIArtifact(tags)`` and the latest version is denormalized to
``PatentPublication.tags`` + ``latest_tags_artifact_id`` for fast reads.

The full controlled vocabulary lives in
``backend/app/ai/prompts/tag_patent_v1.md`` (one source of truth — the
prompt). This module owns the validator that enforces the structure on
the response and the day-one tag-vocabulary constants used by the
opportunity scorer + frontend filters.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.ai.summarizer import extract_independent_claims
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

TAG_PROMPT_NAME = "tag_patent"
TAG_PROMPT_VERSION = 1

# Required keys in the JSON response.
REQUIRED_TAG_FIELDS = {
    "industries",
    "problem_solved",
    "technology_method",
    "materials",
    "novel_application_categories",
    "time_horizon",
    "risk_flags",
    "opportunity_tags",
    "trend_tags",
}

ALLOWED_TIME_HORIZONS = {"now", "near_term", "long_term", "unknown"}

# Day-one tag values surfaced as filters in the UI. Keep in sync with the
# prompt (single source of truth in tag_patent_v1.md). The frontend's
# filter builder reads from ``OPPORTUNITY_TAG_VALUES`` + ``RISK_FLAG_VALUES``.
OPPORTUNITY_TAG_VALUES = (
    "expired_opportunity",
    "ai_revival_candidate",
    "startup_opportunity",
    "enterprise_automation",
    "manufacturing_reuse",
    "sustainability_angle",
    "low_competition",
    "public_domain_candidate",
    "cross_industry_transfer",
)

RISK_FLAG_VALUES = (
    "needs_legal_review",
    "active_family_risk",
    "unknown_legal_status",
    "crowded_space",
    "platform_technology",
    "regulatory_dependency",
    "experimental_only",
)


# ---------------------------------------------------------------------------
# Payload + validation
# ---------------------------------------------------------------------------


def build_tag_payload(patent: PatentPublication) -> dict[str, Any]:
    """Build the prompt-render payload for tag_patent_v1."""
    return {
        "title": patent.title or "(no title provided)",
        "abstract": patent.abstract or "(no abstract provided)",
        "claims_text": extract_independent_claims(patent.claims_text)
        or "(no claims available)",
        "cpc_codes": ", ".join(patent.cpc or []) or "(no classifications)",
        "assignees": ", ".join(patent.assignees or []) or "(no assignees)",
    }


def validate_tags(tags: dict[str, Any]) -> dict[str, Any]:
    """Enforce required keys + coerce list-typed fields + constrain enums."""
    missing = REQUIRED_TAG_FIELDS - set(tags.keys())
    if missing:
        raise SummarizationError(f"Tag output missing required fields: {missing}")

    list_fields = (
        "industries",
        "technology_method",
        "materials",
        "novel_application_categories",
        "risk_flags",
        "opportunity_tags",
        "trend_tags",
    )
    for f in list_fields:
        v = tags.get(f) or []
        if not isinstance(v, list):
            raise SummarizationError(f"Tag field '{f}' must be a list, got {type(v).__name__}")
        # Lowercase + dedupe + drop empties.
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in v:
            if not isinstance(item, str):
                continue
            x = item.strip().lower()
            if not x or x in seen:
                continue
            seen.add(x)
            cleaned.append(x)
        tags[f] = cleaned

    horizon = (tags.get("time_horizon") or "unknown").strip().lower()
    if horizon not in ALLOWED_TIME_HORIZONS:
        horizon = "unknown"
    tags["time_horizon"] = horizon

    if not isinstance(tags.get("problem_solved"), str):
        tags["problem_solved"] = ""
    return tags


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def tag_patent(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
) -> tuple[dict[str, Any], UUID]:
    """Compute tags for a patent and persist as an AIArtifact.

    Returns ``(tags_dict, artifact_id)``. Idempotent: subsequent calls with
    the same input fingerprint hit the cache and return $0 / cached artifact.
    Caller is responsible for denormalizing onto ``PatentPublication`` after
    a successful call (see ``app.tasks.tag.tag_patent_task``).
    """
    payload = build_tag_payload(patent)
    request = LLMRequest(
        artifact_type="tags",
        prompt_name=TAG_PROMPT_NAME,
        prompt_version=TAG_PROMPT_VERSION,
        input_payload=payload,
        patent_publication_id=patent.id,
        run_id=run_id,
        tier="tag",  # routes to Haiku per llm_client._model_for_tier
        max_tokens=1024,
        expected_output_tokens=400,
    )
    client = get_llm_client()
    try:
        response = await client.complete(session, request)
    except anthropic.APIError as e:  # pragma: no cover - network path
        raise SummarizationError(f"Claude API error during tagging: {e}") from e

    if response.content_json is None:
        raise SummarizationError(
            f"Tag artifact {response.artifact_id} did not parse as JSON."
        )
    validated = validate_tags(response.content_json)
    return validated, response.artifact_id
