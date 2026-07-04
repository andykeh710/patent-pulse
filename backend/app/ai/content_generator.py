"""
LinkedIn post generator.

Produces a markdown LinkedIn post for a patent as an AIArtifact.
Cache-first via :mod:`app.ai.llm_client`.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

LINKEDIN_PROMPT_NAME = "linkedin_post"
LINKEDIN_PROMPT_VERSION = 1

REQUIRED_FIELDS = {"post_markdown", "hook", "tone", "caveats"}
ALLOWED_TONES = {"analytical", "curiosity", "news"}


def build_payload(patent: PatentPublication) -> dict[str, Any]:
    """Build the prompt-render payload for linkedin_post_v1."""
    summary_what = ""
    if patent.summary and isinstance(patent.summary, dict):
        summary_what = patent.summary.get("what_it_is", "")

    tags = patent.tags or {}
    opp_tags = tags.get("opportunity_tags", [])
    opp_tag_str = ", ".join(opp_tags) if opp_tags else "None"

    return {
        "title": patent.title or "(no title)",
        "assignees": ", ".join(patent.assignees or []) or "(unknown)",
        "filing_date": str(patent.filing_date) if patent.filing_date else "(unknown)",
        "grant_date": str(patent.grant_date) if patent.grant_date else "(not granted)",
        "legal_status": patent.legal_status or "(unknown)",
        "estimated_expiry": str(patent.estimated_expiry_date)
        if patent.estimated_expiry_date
        else "(not estimated)",
        "abstract": patent.abstract or "(no abstract available)",
        "cpc_codes": ", ".join(patent.cpc or []) or "(none)",
        "ai_summary_what_it_is": summary_what or "(not yet summarized)",
        "opportunity_score": str(round(patent.opportunity_score, 1))
        if patent.opportunity_score is not None
        else "not scored",
        "opportunity_tags_section": f"Opportunity tags: {opp_tag_str}",
    }


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    """Enforce required keys, coerce types, constrain enums.

    Provides sensible defaults for missing keys rather than hard-failing,
    since LLMs occasionally omit keys even when instructed.
    """
    missing = REQUIRED_FIELDS - set(data.keys())
    if "post_markdown" in missing:
        data["post_markdown"] = ""
        missing.discard("post_markdown")
    if "hook" in missing:
        data["hook"] = ""
        missing.discard("hook")
    if "tone" in missing:
        data["tone"] = "analytical"
        missing.discard("tone")
    if "caveats" in missing:
        data["caveats"] = []
        missing.discard("caveats")
    if missing:
        raise SummarizationError(f"LinkedIn post output missing required fields: {missing}")

    # post_markdown: string, stripped
    if not isinstance(data.get("post_markdown"), str):
        data["post_markdown"] = str(data["post_markdown"])
    data["post_markdown"] = data["post_markdown"].strip()

    # hook: string, stripped, capped at 200 chars
    if not isinstance(data.get("hook"), str):
        data["hook"] = str(data["hook"])
    data["hook"] = data["hook"].strip()[:200]

    # tone: constrain to allowed set
    tone = (data.get("tone") or "analytical").strip().lower()
    data["tone"] = tone if tone in ALLOWED_TONES else "analytical"

    # caveats: list of strings, capped at 5
    caveats = data.get("caveats") or []
    if not isinstance(caveats, list):
        caveats = [str(caveats)] if caveats else []
    data["caveats"] = [str(c).strip() for c in caveats if str(c).strip()][:5]

    return data


async def generate_linkedin_post(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
) -> tuple[dict[str, Any], UUID]:
    """Compute LinkedIn post for a patent and persist as an AIArtifact.

    Returns ``(result_dict, artifact_id)``. Idempotent via AIArtifact cache.
    """
    payload = build_payload(patent)
    request = LLMRequest(
        artifact_type="linkedin_post",
        prompt_name=LINKEDIN_PROMPT_NAME,
        prompt_version=LINKEDIN_PROMPT_VERSION,
        input_payload=payload,
        patent_publication_id=patent.id,
        run_id=run_id,
        tier="narrative",  # routes to Haiku (~$0.0003/post)
        max_tokens=2048,
        expected_output_tokens=600,
    )
    client = get_llm_client()
    try:
        response = await client.complete(session, request)
    except anthropic.APIError as e:
        raise SummarizationError(f"AI API error during content generation: {e}") from e

    if response.content_json is None:
        raise SummarizationError(
            f"LinkedIn post artifact {response.artifact_id} did not parse as JSON."
        )
    validated = validate_output(response.content_json)
    return validated, response.artifact_id
