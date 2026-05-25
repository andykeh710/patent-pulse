"""
Weekly digest generator (Sprint 6).

Produces a Sonnet-written weekly briefing from a user's topic matches.
Cached per (user_id, week_start) as AIArtifact.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMRequest, get_llm_client
from app.core.exceptions import SummarizationError

logger = logging.getLogger(__name__)

WEEKLY_DIGEST_PROMPT_NAME = "weekly_digest"
WEEKLY_DIGEST_PROMPT_VERSION = 1

REQUIRED_FIELDS = {"headline", "highlights", "patterns", "caveats"}
FORBIDDEN_PHRASES = [
    "free to use", "public domain", "is used by", "definitely used",
    "infringes", "no licensing required", "can freely use",
    "being commercialized",
]


def build_payload(
    topics: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the prompt payload for weekly_digest_v1."""
    topic_lines = []
    for t in topics:
        topic_lines.append(
            f"- {t.get('name', 'Unnamed')}: "
            f"{t.get('match_count', 0)} new matches ("
            f"keywords={t.get('keywords', [])}, "
            f"cpc={t.get('cpc_prefixes', [])})"
        )

    match_lines = []
    for m in matches[:15]:  # cap at 15 for prompt token budget
        match_lines.append(
            f"  [{m.get('topic_name', '?')}] {m.get('title', 'Untitled')}"
            f" ({m.get('doc_id', '?')})"
            f" — assignee: {m.get('assignee', 'unknown')}"
            f" — CPC: {', '.join(m.get('cpc', [])[:3])}"
        )

    return {
        "topic_list": "\n".join(topic_lines) if topic_lines else "(no topics)",
        "matches_list": "\n".join(match_lines) if match_lines else "(no matches)",
    }


def validate_output(data: dict[str, Any]) -> dict[str, Any]:
    """Enforce schema, reject forbidden phrases, provide defaults."""
    # ── forbidden phrase check ──
    for key in ("headline", "patterns"):
        text = str(data.get(key, ""))
        lower = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lower:
                raise SummarizationError(
                    f"Forbidden phrase '{phrase}' found in {key}. Regenerate."
                )

    # ── schema defaults ──
    for field in REQUIRED_FIELDS:
        if field not in data:
            if field == "highlights":
                data[field] = []
            elif field == "caveats":
                data[field] = [
                    "Evidence is patent-based only — verify with official registers before acting."
                ]
            else:
                data[field] = ""
                logger.warning("Missing field '%s' in weekly digest output", field)

    # Ensure disclaimer is first in caveats.
    disclaimer = "Evidence is patent-based only — verify with official registers before acting."
    caveats: list = data.get("caveats", [])
    if disclaimer not in caveats:
        caveats.insert(0, disclaimer)
    data["caveats"] = [str(c) for c in caveats][:5]

    # Normalize string fields.
    data["headline"] = str(data.get("headline", "")).strip()
    data["patterns"] = str(data.get("patterns", "")).strip()

    # Normalize highlights.
    highlights = data.get("highlights") or []
    data["highlights"] = [
        {
            "patent_doc_id": str(h.get("patent_doc_id", "")),
            "title": str(h.get("title", "")),
            "why_it_matters": str(h.get("why_it_matters", "")),
        }
        for h in highlights[:10]
        if isinstance(h, dict)
    ]

    return data


async def generate_weekly_digest(
    session: AsyncSession,
    user_id: str,
    week_start: date,
    week_end: date,
    topics: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> tuple[dict[str, Any], UUID]:
    """Generate (or return cached) a weekly digest for a user-week.

    Returns (validated_dict, artifact_id).
    """
    payload = build_payload(topics, matches)
    subject_key = f"weekly_digest:{user_id}:{week_start.isoformat()}"

    request = LLMRequest(
        artifact_type="weekly_digest",
        prompt_name=WEEKLY_DIGEST_PROMPT_NAME,
        prompt_version=WEEKLY_DIGEST_PROMPT_VERSION,
        input_payload=payload,
        subject_key=subject_key,
        tier="summary",  # Sonnet — per A3 lesson, Haiku unreliable on structured JSON.
        max_tokens=2048,
        expected_output_tokens=600,
    )
    client = get_llm_client()
    response = await client.complete(session, request)

    if response.content_json is None:
        raise SummarizationError("Weekly digest artifact did not parse as JSON")

    validated = validate_output(response.content_json)

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
