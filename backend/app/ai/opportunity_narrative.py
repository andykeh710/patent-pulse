"""
Opportunity Narrative generator.

Produces a structured "What could someone build with this?" narrative
as an AIArtifact. Cache-first via :mod:`app.ai.llm_client`.

Output schema is enforced by the validator below. The prompt lives in
``backend/app/ai/prompts/opportunity_narrative_v1.md`` (single source of truth).
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

OPPORTUNITY_NARRATIVE_PROMPT_NAME = "opportunity_narrative"
OPPORTUNITY_NARRATIVE_PROMPT_VERSION = 1

# Required keys in the JSON response.
REQUIRED_FIELDS = {
    "opportunity_type",
    "plain_english_opportunity",
    "possible_products",
    "target_customers",
    "implementation_difficulty",
    "commercial_timing",
    "risks",
}

ALLOWED_OPPORTUNITY_TYPES = {
    "startup_idea",
    "enterprise_tooling",
    "licensing",
    "research_signal",
    "defensive_monitoring",
    "revival_candidate",
    "cross_industry_transfer",
}
ALLOWED_DIFFICULTY = {"low", "medium", "high", "unknown"}
ALLOWED_TIMING = {"now", "near_term", "long_term", "uncertain"}


def _format_opportunity_breakdown(breakdown: dict | None) -> str:
    if not breakdown:
        return "(no breakdown available)"
    lines = []
    for k, v in breakdown.items():
        if isinstance(v, (int, float)):
            lines.append(f"  {k}: {v}")
        elif isinstance(v, str):
            lines.append(f"  {k}: {v}")
        else:
            lines.append(f"  {k}: {json.dumps(v)}")
    return "\n".join(lines) or "(empty breakdown)"


def _format_tags(tags: dict | None) -> str:
    if not tags:
        return "(no tags available)"
    out = []
    for key, val in tags.items():
        if isinstance(val, list):
            out.append(f"  {key}: {', '.join(val) or '(empty)'}")
        elif isinstance(val, str):
            out.append(f"  {key}: {val}")
        else:
            out.append(f"  {key}: {json.dumps(val)}")
    return "\n".join(out) or "(empty tags)"


def build_payload(patent: PatentPublication) -> dict[str, Any]:
    """Build the prompt-render payload for opportunity_narrative_v1."""
    tags = patent.tags or {}
    breakdown = patent.opportunity_breakdown or {}
    return {
        "title": patent.title or "(no title provided)",
        "abstract": patent.abstract or "(no abstract provided)",
        "assignees": ", ".join(patent.assignees or []) or "(no assignees)",
        "cpc_codes": ", ".join(patent.cpc or []) or "(no classifications)",
        "legal_status": patent.legal_status or "(unknown)",
        "legal_status_confidence": patent.legal_status_confidence or "unknown",
        "estimated_expiry": str(patent.estimated_expiry_date)
        if patent.estimated_expiry_date
        else "(not estimated)",
        "opportunity_score": str(patent.opportunity_score)
        if patent.opportunity_score is not None
        else "(not scored)",
        "opportunity_breakdown": _format_opportunity_breakdown(breakdown),
        "tags": _format_tags(tags),
        "risk_flags": ", ".join(tags.get("risk_flags", [])) or "(none)",
        "time_horizon": tags.get("time_horizon", "unknown"),
        "industries": ", ".join(tags.get("industries", [])) or "(none)",
        "technology_method": ", ".join(tags.get("technology_method", [])) or "(none)",
        "novel_application_categories": ", ".join(tags.get("novel_application_categories", []))
        or "(none)",
        "opportunity_narrative_context": "",  # reserved for future why_now/trend context
    }


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    """Enforce required keys, coerce types, constrain enums.

    Maps common LLM alternative keys to canonical schema keys.
    """
    # Map alternative keys before strict validation
    key_map = {
        "commercialization_analysis": "plain_english_opportunity",
        "opportunity": "plain_english_opportunity",
    }
    for old_key, new_key in key_map.items():
        if old_key in data and new_key not in data:
            data[new_key] = data.pop(old_key)

    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        # Provide sensible defaults for missing fields rather than hard-failing,
        # since LLMs occasionally omit keys even when instructed.
        if "opportunity_type" in missing:
            data["opportunity_type"] = "research_signal"
            missing.discard("opportunity_type")
        if "plain_english_opportunity" in missing:
            data["plain_english_opportunity"] = ""
            missing.discard("plain_english_opportunity")
        if "possible_products" in missing:
            data["possible_products"] = []
            missing.discard("possible_products")
        if "target_customers" in missing:
            data["target_customers"] = []
            missing.discard("target_customers")
        if "implementation_difficulty" in missing:
            data["implementation_difficulty"] = "unknown"
            missing.discard("implementation_difficulty")
        if "commercial_timing" in missing:
            data["commercial_timing"] = "uncertain"
            missing.discard("commercial_timing")
        if "risks" in missing:
            data["risks"] = []
            missing.discard("risks")
        if missing:
            raise SummarizationError(
                f"Opportunity Narrative output missing required fields: {missing}"
            )

    # opportunity_type
    ot = (data.get("opportunity_type") or "research_signal").strip().lower()
    if ot not in ALLOWED_OPPORTUNITY_TYPES:
        ot = "research_signal"
    data["opportunity_type"] = ot

    # plain_english_opportunity
    if not isinstance(data.get("plain_english_opportunity"), str):
        data["plain_english_opportunity"] = ""

    # possible_products
    pp = data.get("possible_products") or []
    if not isinstance(pp, list):
        pp = [str(pp)] if pp else []
    data["possible_products"] = [str(x).strip() for x in pp if str(x).strip()][:4]

    # target_customers
    tc = data.get("target_customers") or []
    if not isinstance(tc, list):
        tc = [str(tc)] if tc else []
    data["target_customers"] = [str(x).strip() for x in tc if str(x).strip()][:3]

    # implementation_difficulty
    diff = (data.get("implementation_difficulty") or "unknown").strip().lower()
    if diff not in ALLOWED_DIFFICULTY:
        diff = "unknown"
    data["implementation_difficulty"] = diff

    # commercial_timing
    timing = (data.get("commercial_timing") or "uncertain").strip().lower()
    if timing not in ALLOWED_TIMING:
        timing = "uncertain"
    data["commercial_timing"] = timing

    # risks
    risks = data.get("risks") or []
    if not isinstance(risks, list):
        risks = [str(risks)] if risks else []
    data["risks"] = [str(x).strip() for x in risks if str(x).strip()][:4]

    return data


async def generate_opportunity_narrative(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
) -> tuple[dict[str, Any], UUID]:
    """Compute Opportunity Narrative for a patent and persist as an AIArtifact.

    Returns ``(result_dict, artifact_id)``. Idempotent: subsequent calls with
    the same input fingerprint hit the cache and return the cached artifact.
    """
    payload = build_payload(patent)
    request = LLMRequest(
        artifact_type="opportunity_narrative",
        prompt_name=OPPORTUNITY_NARRATIVE_PROMPT_NAME,
        prompt_version=OPPORTUNITY_NARRATIVE_PROMPT_VERSION,
        input_payload=payload,
        patent_publication_id=patent.id,
        run_id=run_id,
        # Post-Sprint-5 audit (A3): Haiku consistently returned a non-canonical
        # schema (commercialization_analysis, inferred_opportunities, etc.)
        # where the existing key_map only mapped 1 of 7 required fields — the
        # rest defaulted to empty. Switching to summary tier (Sonnet) per the
        # Sprint 4 trend_narrative precedent.
        tier="summary",
        max_tokens=2048,
        expected_output_tokens=600,
    )
    client = get_llm_client()
    try:
        response = await client.complete(session, request)
    except anthropic.APIError as e:  # pragma: no cover - network path
        raise SummarizationError(f"AI API error during Opportunity Narrative: {e}") from e

    if response.content_json is None:
        raise SummarizationError(
            f"Opportunity Narrative artifact {response.artifact_id} did not parse as JSON."
        )
    validated = validate_output(response.content_json)
    return validated, response.artifact_id
