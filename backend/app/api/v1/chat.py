"""
Phase 3 — Chat API (SSE streaming).

PR 1: SSE scaffold with mock LLM.
PR 2: Real Anthropic streaming + patent retrieval layer.
PR 3: Anthropic tool calls (search_patents, open_patent, compare_companies).
PR 4: Citation extraction + soft warning.
PR 6: Chat quota enforcement (Free 5/day, Basic 50/day, Lifetime/Enterprise unlimited).

Endpoint:
  POST /api/v1/chat/stream  — chat with SSE streaming
  GET  /api/v1/chat/quota    — read current usage
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anthropic_client import get_chat_client
from app.api.deps import current_user, get_db
from app.core.ai_models import User
from app.services.chat_citations import extract_citations, verify_citations
from app.services.chat_quota import QuotaExceeded, get_quota_service
from app.services.chat_retrieval import build_system_prompt, retrieve_patents
from app.services.chat_tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────

MAX_TOOL_CALLS_PER_TURN = 5

# ── Request / Event models ───────────────────────────────────────────


class ChatStreamRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's chat message",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Opaque conversation ID for future memory support",
    )


def _sse_event(event_type: str, **fields) -> str:
    """Format a single SSE event as a data: line."""
    payload = {"type": event_type, **fields}
    return f"data: {json.dumps(payload)}\n\n"


# ── Quota enforcement ─────────────────────────────────────────────────


async def _enforce_chat_quota(user_id: str, db: AsyncSession) -> None:
    """Check and increment the user's daily chat quota.

    Raises HTTPException 429 if the limit is exceeded.
    """
    # Look up the user's tier
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    tier = user.tier if user else "free"

    try:
        await get_quota_service().check_and_increment(user_id, tier)
    except QuotaExceeded as e:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "tier": e.tier,
                "used": e.used,
                "limit": e.limit,
                "upgrade_url": "/account/billing",
            },
        ) from e


# ── Tool result helper ────────────────────────────────────────────────


def _sanitize_tool_result(result: dict) -> dict:
    """Truncate large tool results to keep context window manageable."""
    sanitized = dict(result)
    if "results" in sanitized and isinstance(sanitized["results"], list):
        sanitized["results"] = sanitized["results"][:20]
        for r in sanitized["results"]:
            if isinstance(r, dict) and "abstract_excerpt" in r:
                excerpt = r["abstract_excerpt"]
                if isinstance(excerpt, str) and len(excerpt) > 200:
                    r["abstract_excerpt"] = excerpt[:200]
    for key in ("abstract", "claims_preview"):
        val = sanitized.get(key)
        if isinstance(val, str) and len(val) > 800:
            sanitized[key] = val[:797] + "..."
    return sanitized


# ── Citation helpers ──────────────────────────────────────────────────


def _collect_tool_doc_ids(name: str, result: dict) -> set[str]:
    """Extract patent doc_ids from a tool-call result."""
    ids: set[str] = set()

    if name == "open_patent":
        doc_id = result.get("doc_id")
        if isinstance(doc_id, str) and doc_id:
            ids.add(doc_id)

    elif name == "search_patents":
        for r in result.get("results") or []:
            doc_id = r.get("doc_id") if isinstance(r, dict) else None
            if isinstance(doc_id, str) and doc_id:
                ids.add(doc_id)

    elif name == "compare_companies":
        for c in result.get("companies") or []:
            doc_id = c.get("top_patent_id") if isinstance(c, dict) else None
            if isinstance(doc_id, str) and doc_id:
                ids.add(doc_id)

    return ids


# ── Anthropic stream adapter ──────────────────────────────────────────


async def _stream_anthropic_response(
    message: str,
    db: AsyncSession,
):
    """Retrieve patents + stream Anthropic response with tool calls
    and citation verification.

    Pipeline:
      1. Embed query → retrieve top-K patents via pgvector
      2. Build system prompt with patent context
      3. Stream Anthropic token-by-token, handling tool-use events
      4. On tool_use: execute tool, emit SSE events, resume stream
      5. Extract citations, verify against known doc_ids, emit events
      6. Emit sources + done events

    Yields:
        SSE-formatted strings.
    """
    # ── Step 1: Retrieve ──────────────────────────────────────────
    patents = await retrieve_patents(message, db)

    yield _sse_event(
        "meta",
        model="claude-sonnet-4-20250514",
        retrieved_count=len(patents),
    )

    # ── Step 2: System prompt ─────────────────────────────────────
    system_prompt = build_system_prompt(patents)

    # ── Citation-tracking state ───────────────────────────────────
    full_text_parts: list[str] = []
    known_doc_ids: set[str] = {p["doc_id"] for p in patents}

    # ── Step 3: Anthropic streaming with tool loop ────────────────
    client = get_chat_client()
    messages: list[dict] = [{"role": "user", "content": message}]
    tool_call_count = 0

    while True:
        try:
            async for event in client.stream(
                system=system_prompt,
                messages=messages,
                tools=TOOLS,
            ):
                if event["type"] == "text":
                    full_text_parts.append(event["content"])
                    yield _sse_event("token", content=event["content"])

                elif event["type"] == "tool_use":
                    tool_call_count += 1
                    if tool_call_count > MAX_TOOL_CALLS_PER_TURN:
                        yield _sse_event(
                            "warning",
                            message="Tool call limit reached (5 per turn).",
                        )
                        yield _sse_event("done")
                        return

                    tool_name: str = event.get("name", "")
                    tool_input: dict = event.get("input", {})
                    tool_id: str = event.get("id", "")

                    yield _sse_event(
                        "tool_call_start",
                        name=tool_name,
                        input=tool_input,
                    )

                    try:
                        result = await execute_tool(tool_name, tool_input, db)
                    except Exception:
                        logger.exception("Tool execution failed: %s", tool_name)
                        result = {"error": f"Tool '{tool_name}' encountered an internal error."}

                    known_doc_ids |= _collect_tool_doc_ids(tool_name, result)
                    sanitized = _sanitize_tool_result(result)

                    yield _sse_event(
                        "tool_call_result",
                        name=tool_name,
                        result=sanitized,
                    )

                    messages.append(
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": tool_id,
                                    "name": tool_name,
                                    "input": tool_input,
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": json.dumps(sanitized),
                                }
                            ],
                        }
                    )

                    break

            else:
                break

        except Exception:
            logger.exception("Anthropic streaming failed")
            yield _sse_event(
                "error",
                message=("The chat service is temporarily unavailable. " "Please try again."),
            )
            yield _sse_event("done")
            return

    # ── Step 4: Citation verification ─────────────────────────────
    full_text = "".join(full_text_parts)
    cited = extract_citations(full_text)
    verification = verify_citations(cited, known_doc_ids)

    yield _sse_event(
        "citations",
        verified=verification["verified"],
        unverified=verification["unverified"],
    )

    if verification["unverified"]:
        yield _sse_event(
            "warning",
            code="uncited_or_invalid_doc_ids",
            message=("Some patent references could not be verified " "against retrieved sources."),
        )

    # ── Step 5: Sources + done ────────────────────────────────────
    yield _sse_event("sources", patents=patents)
    yield _sse_event("done")


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/stream")
async def chat_stream(
    request: Request,
    body: ChatStreamRequest,
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream an LLM response as Server-Sent Events.

    Auth + quota required. Retrieves top-K relevant patents and
    streams an Anthropic response with inline citations, optional
    tool calls, and citation verification.
    """
    logger.info(
        "chat_stream: user=%s message_len=%d conversation_id=%s",
        user_id,
        len(body.message),
        body.conversation_id,
    )

    # Enforce daily quota (raises 429 if exceeded)
    await _enforce_chat_quota(user_id, db)

    return StreamingResponse(
        _stream_anthropic_response(body.message, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/quota")
async def chat_quota(
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read current chat quota usage for the authenticated user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    tier = user.tier if user else "free"

    return await get_quota_service().get_usage(user_id, tier)
