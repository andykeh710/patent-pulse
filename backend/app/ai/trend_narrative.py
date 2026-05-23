"""
Trend narrative generator.

Produces a data-backed narrative for a trend (surface + key) as an
AIArtifact. Cache-first via :mod:`app.ai.llm_client`. Mirrors
:mod:`app.ai.why_now`.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.core.ai_models import AIArtifact, TrendSnapshot
from app.core.exceptions import SummarizationError

logger = logging.getLogger(__name__)

TREND_NARRATIVE_PROMPT_NAME = "trend_narrative"
TREND_NARRATIVE_PROMPT_VERSION = 1

REQUIRED_FIELDS = {"summary", "why_now", "key_assignees", "related_trends", "caveats"}


def build_payload(
    trend: TrendSnapshot,
    top_patents: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the prompt-render payload for trend_narrative_v1.

    `top_patents` is an optional list of dicts with keys:
    {title, abstract_snippet, primary_assignee, cpc_codes}.
    Max 5 patents used; abstracts truncated to ~200 chars.
    """
    assignee_pct = round(trend.assignee_diversity * 100, 1) if trend.assignee_diversity else 0
    cpc_pct = round(trend.cpc_diversity * 100, 1) if trend.cpc_diversity else 0

    payload: dict[str, Any] = {
        "surface": trend.surface,
        "key": trend.key,
        "count_4w": str(trend.count_4w),
        "count_12w": str(trend.count_12w),
        "baseline_12mo": str(round(trend.baseline_12mo, 1)),
        "z_score": str(round(trend.z_score, 1)),
        "growth_pct": str(round(trend.growth_pct, 1)),
        "assignee_diversity_pct": str(assignee_pct),
        "cpc_diversity_pct": str(cpc_pct),
        "patent_context": "",
    }

    if top_patents:
        lines = ["Top patents driving this trend:"]
        for i, p in enumerate(top_patents[:5], 1):
            title = p.get("title") or "(untitled)"
            assignee = p.get("primary_assignee") or "unknown"
            cpc = p.get("cpc_codes") or "N/A"
            abstract = p.get("abstract_snippet") or ""
            line = f"{i}. {title} (assignee: {assignee}, CPC: {cpc})"
            if abstract:
                line += f" — {abstract}"
            lines.append(line)
        payload["patent_context"] = "\n".join(lines)

    return payload


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    """Enforce required keys, coerce types, provide defaults.

    Handles both flat responses and nested ``{"trend_analysis": {...}}``
    wrappers that some models (Haiku) produce despite prompt instructions.
    """
    # Some models wrap content in envelope keys. Handle both dict and string envelopes.
    # Also handle flat responses where a `trend_summary` key holds the summary text.
    for key_name in ("trend_summary", "trend_analysis"):
        if key_name in data:
            if isinstance(data[key_name], str) and not data.get("summary"):
                data["summary"] = data[key_name]
            elif isinstance(data[key_name], dict):
                inner = data[key_name]
                if "summary" in inner:
                    data["summary"] = inner["summary"]
                elif "title" in inner:
                    # {title, overview, caveats, ...} format — combine into summary.
                    parts = [inner.get("title", "")]
                    for k in ("overview", "key_findings", "filing_activity", "analysis"):
                        if k in inner:
                            if isinstance(inner[k], dict):
                                interp = inner[k].get("interpretation", "")
                                if interp:
                                    parts.append(interp)
                            elif isinstance(inner[k], str):
                                parts.append(inner[k])
                    data["summary"] = " ".join(p for p in parts if p).strip()
                elif "implications" in inner:
                    data["summary"] = str(inner["implications"])
                if "why_now" in inner:
                    data["why_now"] = inner["why_now"]
                elif "filing_activity" in inner and isinstance(inner["filing_activity"], dict):
                    data["why_now"] = str(inner["filing_activity"].get("interpretation", ""))
                if "key_assignees" in inner:
                    data["key_assignees"] = inner["key_assignees"]
                if "related_trends" in inner:
                    data["related_trends"] = inner["related_trends"]
                if "caveats" in inner:
                    data["caveats"] = inner["caveats"]

    missing = REQUIRED_FIELDS - set(data.keys())
    # Top-level `implications` → `why_now` fallback.
    if "why_now" in missing and "implications" in data:
        data["why_now"] = str(data["implications"])
        missing.discard("why_now")
    if "summary" in missing:
        data["summary"] = ""
        missing.discard("summary")
    if "why_now" in missing:
        data["why_now"] = ""
        missing.discard("why_now")
    if "key_assignees" in missing:
        data["key_assignees"] = []
        missing.discard("key_assignees")
    if "related_trends" in missing:
        data["related_trends"] = []
        missing.discard("related_trends")
    if "caveats" in missing:
        # Default caveat when LLM doesn't produce any.
        data["caveats"] = [
            "Trend analysis is based on patent filing activity and does not constitute market or legal advice."
        ]
        missing.discard("caveats")
    if missing:
        raise SummarizationError(
            f"Trend narrative output missing required fields: {missing}"
        )

    # summary: string, stripped
    if not isinstance(data.get("summary"), str):
        data["summary"] = str(data["summary"])
    data["summary"] = data["summary"].strip()

    # why_now: string, stripped
    if not isinstance(data.get("why_now"), str):
        data["why_now"] = str(data["why_now"])
    data["why_now"] = data["why_now"].strip()

    # key_assignees: list of strings
    assignees = data.get("key_assignees") or []
    if not isinstance(assignees, list):
        assignees = [str(assignees)] if assignees else []
    data["key_assignees"] = [str(a).strip() for a in assignees if str(a).strip()][:10]

    # related_trends: list of strings
    related = data.get("related_trends") or []
    if not isinstance(related, list):
        related = [str(related)] if related else []
    data["related_trends"] = [str(r).strip() for r in related if str(r).strip()][:5]

    # caveats: list of strings, capped at 5
    caveats = data.get("caveats") or []
    if not isinstance(caveats, list):
        caveats = [str(caveats)] if caveats else []
    data["caveats"] = [str(c).strip() for c in caveats if str(c).strip()][:5]

    return data


async def generate_trend_narrative(
    session: AsyncSession,
    trend: TrendSnapshot,
    *,
    run_id: UUID | None = None,
    top_patents: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any], UUID]:
    """Compute a trend narrative and persist as an AIArtifact.

    Returns ``(result_dict, artifact_id)``. Idempotent via AIArtifact cache.
    """
    payload = build_payload(trend, top_patents=top_patents)
    subject_key = f"{trend.surface}:{trend.key}"
    request = LLMRequest(
        artifact_type="trend_narrative",
        prompt_name=TREND_NARRATIVE_PROMPT_NAME,
        prompt_version=TREND_NARRATIVE_PROMPT_VERSION,
        input_payload=payload,
        subject_key=subject_key,
        run_id=run_id,
        tier="summary",  # Sonnet — Haiku produced unstable JSON envelopes on this schema.
        max_tokens=2048,
        expected_output_tokens=500,
    )
    client = get_llm_client()
    try:
        response = await client.complete(session, request)
    except anthropic.APIError as e:
        raise SummarizationError(
            f"Claude API error during trend narrative generation: {e}"
        ) from e

    if response.content_json is None:
        raise SummarizationError(
            f"Trend narrative artifact {response.artifact_id} did not parse as JSON."
        )
    validated = validate_output(response.content_json)

    # Update the artifact with validated data so GET returns clean schema.
    # Use explicit UPDATE since in-place mutation of JSONB doesn't always flush.
    from sqlalchemy import update
    await session.execute(
        update(AIArtifact)
        .where(AIArtifact.id == response.artifact_id)
        .values(content_json=validated, content_text=None)
    )
    await session.commit()

    return validated, response.artifact_id
