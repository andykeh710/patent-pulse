"""
Why Now narrative generator.

Produces a structured "Why is this patent interesting NOW?" narrative
as an AIArtifact. Cache-first via :mod:`app.ai.llm_client`. The latest
version is denormalized to ``PatentPublication.why_now_text`` for fast
reads.

Output schema is enforced by the validator below. The prompt lives in
``backend/app/ai/prompts/why_now_v1.md`` (single source of truth).
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

WHY_NOW_PROMPT_NAME = "why_now"
WHY_NOW_PROMPT_VERSION = 1

# Required keys in the JSON response.
REQUIRED_FIELDS = {"headline", "summary", "signals", "confidence", "limitations"}

ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_SIGNAL_TYPES = {
    "publication_timing",
    "expiry_window",
    "technology_momentum",
    "assignee_activity",
    "market_timing",
    "legal_event",
    "cross_industry",
    "other",
}


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
    """Build the prompt-render payload for why_now_v1."""
    tags = patent.tags or {}
    breakdown = patent.opportunity_breakdown or {}
    return {
        "title": patent.title or "(no title provided)",
        "abstract": patent.abstract or "(no abstract provided)",
        "assignees": ", ".join(patent.assignees or []) or "(no assignees)",
        "cpc_codes": ", ".join(patent.cpc or []) or "(no classifications)",
        "legal_status": patent.legal_status or "(unknown)",
        "legal_status_confidence": patent.legal_status_confidence or "unknown",
        "estimated_expiry": str(patent.estimated_expiry_date) if patent.estimated_expiry_date else "(not estimated)",
        "family_members": ", ".join(patent.family_members or []) or "(none)",
        "opportunity_score": str(patent.opportunity_score) if patent.opportunity_score is not None else "(not scored)",
        "opportunity_score_version": str(patent.opportunity_score_version or 1),
        "opportunity_breakdown": _format_opportunity_breakdown(breakdown),
        "tags": _format_tags(tags),
        "risk_flags": ", ".join(tags.get("risk_flags", [])) or "(none)",
        "time_horizon": tags.get("time_horizon", "unknown"),
        "industries": ", ".join(tags.get("industries", [])) or "(none)",
        "technology_method": ", ".join(tags.get("technology_method", [])) or "(none)",
        "novel_application_categories": ", ".join(tags.get("novel_application_categories", [])) or "(none)",
        "why_now_context": "",  # reserved for future trend signal injection
    }


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    """Enforce required keys, coerce types, constrain enums.

    Maps common LLM alternative keys to canonical schema keys.
    """
    # Map alternative keys before strict validation
    key_map = {
        "why_interesting_now": "headline",
        "key_limitations": "limitations",
        "timing_relevance": "summary",
    }
    for old_key, new_key in key_map.items():
        if old_key in data and new_key not in data:
            data[new_key] = data.pop(old_key)

    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        # Provide sensible defaults for missing fields rather than hard-failing,
        # since LLMs occasionally omit keys even when instructed.
        if "signals" in missing:
            data["signals"] = []
            missing.discard("signals")
        if "confidence" in missing:
            data["confidence"] = "low"
            missing.discard("confidence")
        if "limitations" in missing:
            data["limitations"] = []
            missing.discard("limitations")
        if "headline" in missing:
            data["headline"] = ""
            missing.discard("headline")
        if "summary" in missing:
            data["summary"] = ""
            missing.discard("summary")
        if missing:
            raise SummarizationError(f"Why Now output missing required fields: {missing}")

    # headline
    if not isinstance(data.get("headline"), str):
        data["headline"] = ""
    data["headline"] = data["headline"].strip()[:120]

    # summary
    if not isinstance(data.get("summary"), str):
        data["summary"] = ""

    # signals
    signals = data.get("signals") or []
    if not isinstance(signals, list):
        raise SummarizationError("'signals' must be a list")
    cleaned_signals: list[dict[str, Any]] = []
    for sig in signals:
        if not isinstance(sig, dict):
            continue
        st = (sig.get("type") or "other").strip().lower()
        if st not in ALLOWED_SIGNAL_TYPES:
            st = "other"
        cleaned_signals.append({
            "type": st,
            "explanation": str(sig.get("explanation", "")).strip(),
        })
    data["signals"] = cleaned_signals[:4]  # cap at 4

    # confidence
    conf = (data.get("confidence") or "low").strip().lower()
    if conf not in ALLOWED_CONFIDENCE:
        conf = "low"
    data["confidence"] = conf

    # limitations
    lims = data.get("limitations") or []
    if not isinstance(lims, list):
        lims = [str(lims)] if lims else []
    data["limitations"] = [str(x).strip() for x in lims if str(x).strip()]

    return data


async def generate_why_now(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
) -> tuple[dict[str, Any], UUID]:
    """Compute Why Now narrative for a patent and persist as an AIArtifact.

    Returns ``(result_dict, artifact_id)``. Idempotent: subsequent calls with
    the same input fingerprint hit the cache and return the cached artifact.
    Caller is responsible for denormalizing onto ``PatentPublication`` after
    a successful call.
    """
    payload = build_payload(patent)
    request = LLMRequest(
        artifact_type="why_now",
        prompt_name=WHY_NOW_PROMPT_NAME,
        prompt_version=WHY_NOW_PROMPT_VERSION,
        input_payload=payload,
        patent_publication_id=patent.id,
        run_id=run_id,
        tier="narrative",  # routes to Haiku per llm_client._model_for_tier
        max_tokens=2048,
        expected_output_tokens=600,
    )
    client = get_llm_client()
    try:
        response = await client.complete(session, request)
    except anthropic.APIError as e:  # pragma: no cover - network path
        raise SummarizationError(f"Claude API error during Why Now: {e}") from e

    if response.content_json is None:
        raise SummarizationError(
            f"Why Now artifact {response.artifact_id} did not parse as JSON."
        )
    validated = validate_output(response.content_json)
    return validated, response.artifact_id
