"""
Usage signal narrative generator (Sprint 5).

Produces a hedged, evidence-backed narrative for patents with usage signals.
On-demand via AIArtifact cache. Mirrors trend_narrative.py pattern.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.core.exceptions import SummarizationError

logger = logging.getLogger(__name__)

USAGE_NARRATIVE_PROMPT_NAME = "usage_signal_narrative"
USAGE_NARRATIVE_PROMPT_VERSION = 1

REQUIRED_FIELDS = {"summary", "evidence_summary", "market_categories", "related_companies", "limitations"}

# ── Forbidden phrases (scope doc §4) ─────────────────────────────────

FORBIDDEN_PHRASES = [
    "this patent is used",
    "is used by",
    "definitely used",
    "definitively",
    "infringes",
    "free to use",
    "public domain",
    "no licensing required",
    "can freely use",
    "being commercialized",
]

MAX_RETRIES = 2

FALLBACK_NARRATIVE = {
    "summary": "",
    "evidence_summary": "",
    "market_categories": [],
    "related_companies": [],
    "limitations": [
        "Evidence is patent-based only — no product-level verification has been performed.",
        "Narrative generation was unsuccessful after multiple attempts. Evidence data is available for manual review.",
    ],
}


def _contains_forbidden(text: str) -> list[str]:
    """Return list of forbidden phrases found in text (case-insensitive)."""
    lower = text.lower()
    return [phrase for phrase in FORBIDDEN_PHRASES if phrase.lower() in lower]


def build_payload(
    signal_summary: dict[str, Any],
    top_evidence: list[dict[str, Any]],
    patent_title: str = "",
    patent_assignee: str = "",
    expiry_status: str = "",
    expiry_confidence: str = "",
) -> dict[str, Any]:
    """Build the prompt-render payload for usage_signal_narrative_v1."""
    evidence_lines = []
    for i, ev in enumerate(top_evidence[:5], 1):
        title = ev.get("source_patent_title") or "(untitled)"
        assignee = ev.get("source_patent_assignee") or "unknown"
        tier = ev.get("evidence_tier", "unknown")
        sim = ev.get("similarity_score")
        date_str = str(ev.get("source_patent_filing_date", ""))
        line = f"{i}. {title} (assignee: {assignee}, tier: {tier}"
        if sim is not None:
            line += f", similarity: {sim:.2f}"
        if date_str:
            line += f", filed: {date_str}"
        line += ")"
        evidence_lines.append(line)

    return {
        "patent_title": patent_title or "(untitled)",
        "patent_assignee": patent_assignee or "unknown",
        "expiry_status": expiry_status or "unknown",
        "expiry_confidence": expiry_confidence or "unknown",
        "evidence_count": str(signal_summary.get("evidence_count", 0)),
        "strong_count": str(signal_summary.get("by_tier", {}).get("strong", 0)),
        "medium_count": str(signal_summary.get("by_tier", {}).get("medium", 0)),
        "weak_count": str(signal_summary.get("by_tier", {}).get("weak", 0)),
        "signal_score": str(signal_summary.get("score", 0)),
        "signal_confidence": signal_summary.get("confidence", "unknown"),
        "evidence_list": "\n".join(evidence_lines) if evidence_lines else "(none)",
    }


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    """Enforce schema, coerce types, reject forbidden phrases.

    Handles Sonnet envelope keys (key_findings, overall_assessment,
    commercial_indicators) by mapping them to canonical schema keys.

    Returns validated dict. Raises SummarizationError with
    detail=FORBIDDEN if any forbidden phrase is present (caller retries).
    """
    # Sonnet envelope handling (mirrors trend_narrative pattern).
    # Map non-canonical keys to the expected schema.
    if "key_findings" in data and "evidence_summary" not in data:
        findings = data["key_findings"]
        if isinstance(findings, list):
            lines = []
            for f in findings[:5]:
                if isinstance(f, dict):
                    lines.append(f.get("evidence", "") or f.get("theme", ""))
                elif isinstance(f, str):
                    lines.append(f)
            data["evidence_summary"] = ". ".join(l for l in lines if l)
        elif isinstance(findings, str):
            data["evidence_summary"] = findings

    if "overall_assessment" in data and isinstance(data["overall_assessment"], str):
        existing = data.get("summary", "")
        if existing:
            data["summary"] = existing + " " + data["overall_assessment"]
        else:
            data["summary"] = data["overall_assessment"]

    if "commercial_indicators" in data:
        # Heuristic: commercial_indicators is a list of dicts with keys
        # like "type" (maps to market_categories) and "assignee"/"company"
        # (maps to related_companies). Split based on key presence.
        indicators = data["commercial_indicators"]
        if isinstance(indicators, list):
            for item in indicators[:5]:
                if isinstance(item, dict):
                    cat = item.get("type") or item.get("category")
                    if cat:
                        cats = data.setdefault("market_categories", [])
                        if isinstance(cats, list):
                            cats.append(str(cat))
                    comp = item.get("assignee") or item.get("company")
                    if comp:
                        comps = data.setdefault("related_companies", [])
                        if isinstance(comps, list):
                            comps.append(str(comp))
    # Check for forbidden phrases in all string fields.
    for key in ("summary", "evidence_summary"):
        text = str(data.get(key, ""))
        hits = _contains_forbidden(text)
        if hits:
            raise SummarizationError(
                f"Forbidden phrases found in {key}: {hits}. "
                f"Regenerate with stricter hedging."
            )

    # Schema defaults.
    for field in REQUIRED_FIELDS:
        if field not in data:
            if field in ("market_categories", "related_companies"):
                data[field] = []
            elif field == "limitations":
                data[field] = [
                    "Evidence is patent-based only — no product-level verification has been performed."
                ]
            else:
                data[field] = ""

    # summary: string, stripped, enforce minimum length (non-strict).
    if not isinstance(data.get("summary"), str):
        data["summary"] = str(data["summary"])
    data["summary"] = data["summary"].strip()

    # evidence_summary: string, stripped.
    if not isinstance(data.get("evidence_summary"), str):
        data["evidence_summary"] = str(data["evidence_summary"])
    data["evidence_summary"] = data["evidence_summary"].strip()

    # market_categories: list of strings, max 5.
    cats = data.get("market_categories") or []
    data["market_categories"] = [str(c) for c in cats if c][:5]

    # related_companies: list of strings, max 5.
    comps = data.get("related_companies") or []
    data["related_companies"] = [str(c) for c in comps if c][:5]

    # limitations: list of strings, ensure first is standard disclaimer.
    lims = data.get("limitations") or []
    if not lims:
        lims = [
            "Evidence is patent-based only — no product-level verification has been performed."
        ]
    # Ensure the disclaimer is first.
    disclaimer = "Evidence is patent-based only — no product-level verification has been performed."
    if disclaimer not in lims:
        lims.insert(0, disclaimer)
    data["limitations"] = [str(l) for l in lims][:5]

    return data


async def generate_usage_narrative(
    session: AsyncSession,
    signal_summary: dict[str, Any],
    top_evidence: list[dict[str, Any]],
    patent_id: UUID,
    *,
    patent_title: str = "",
    patent_assignee: str = "",
    expiry_status: str = "",
    expiry_confidence: str = "",
) -> tuple[dict[str, Any], UUID]:
    """Generate a usage signal narrative with retry on forbidden phrases.

    Returns (validated_dict, artifact_id). Cached via AIArtifact.
    """
    payload = build_payload(
        signal_summary, top_evidence,
        patent_title=patent_title,
        patent_assignee=patent_assignee,
        expiry_status=expiry_status,
        expiry_confidence=expiry_confidence,
    )

    subject_key = f"usage:{patent_id}"

    # Retry loop for forbidden phrase rejection.
    for attempt in range(MAX_RETRIES + 1):
        strict_prefix = ""
        if attempt > 0:
            strict_prefix = (
                "STRICT INSTRUCTION (attempt {n}): The previous output contained "
                "forbidden phrases. Re-read the SYSTEM section's forbidden phrase "
                "list and regenerate. Use ONLY hedged language. ".format(n=attempt + 1)
            )

        request = LLMRequest(
            artifact_type="usage_signal_narrative",
            prompt_name=USAGE_NARRATIVE_PROMPT_NAME,
            prompt_version=USAGE_NARRATIVE_PROMPT_VERSION,
            input_payload={**payload, "_strict_prefix": strict_prefix},
            subject_key=subject_key,
            tier="summary",  # Sonnet — matches trend_narrative. Haiku produced
                             # unstable JSON envelopes on structured narrative
                             # schemas in Sprint 4 diagnosis.
            max_tokens=2048,
            expected_output_tokens=500,
        )
        client = get_llm_client()
        try:
            response = await client.complete(session, request)
        except anthropic.APIError as e:
            raise SummarizationError(
                f"Claude API error during usage narrative generation: {e}"
            ) from e

        if response.content_json is None:
            raise SummarizationError(
                f"Usage narrative artifact {response.artifact_id} did not parse as JSON."
            )

        try:
            validated = validate_output(response.content_json)
        except SummarizationError as e:
            if "Forbidden phrases" in str(e) and attempt < MAX_RETRIES:
                logger.warning(
                    "Forbidden phrase detected (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES + 1, e,
                )
                continue
            # Last retry exhausted or different error — use fallback.
            logger.error("Narrative generation failed: %s", e)
            validated = dict(FALLBACK_NARRATIVE)

        # Update artifact with validated content.
        from sqlalchemy import update
        from app.core.ai_models import AIArtifact
        await session.execute(
            update(AIArtifact)
            .where(AIArtifact.id == response.artifact_id)
            .values(content_json=validated, content_text=None)
        )
        await session.commit()

        return validated, response.artifact_id

    # Should not reach here; return fallback.
    logger.error("Usage narrative retries exhausted for %s", patent_id)
    return dict(FALLBACK_NARRATIVE), UUID("00000000-0000-0000-0000-000000000000")
