"""
Phase 3 — Chat API (SSE streaming).

PR 1: SSE scaffold with mock LLM.
PR 2: Real Anthropic streaming + patent retrieval layer.
PR 3: Anthropic tool calls (search_patents, open_patent, compare_companies).

Endpoint:
  POST /api/v1/chat/stream
    Request:  {"message": str, "conversation_id": str | None}
    Response: text/event-stream (Server-Sent Events)
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anthropic_client import get_chat_client
from app.api.deps import current_user, get_db
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


# ── Quota stub ────────────────────────────────────────────────────────


async def _check_chat_quota_stub(user_id: str) -> None:
    """Log the quota check; actual enforcement lands in PR 6."""
    logger.info(
        "chat_quota_stub: would enforce quota for user=%s",
        user_id,
    )


# ── Tool result helper ────────────────────────────────────────────────


def _sanitize_tool_result(result: dict) -> dict:
    """Truncate large tool results to keep context window manageable."""
    sanitized = dict(result)
    # search_patents result: truncate abstract_excerpt per patent
    if "results" in sanitized and isinstance(sanitized["results"], list):
        sanitized["results"] = sanitized["results"][:20]
        for r in sanitized["results"]:
            if isinstance(r, dict) and "abstract_excerpt" in r:
                excerpt = r["abstract_excerpt"]
                if isinstance(excerpt, str) and len(excerpt) > 200:
                    r["abstract_excerpt"] = excerpt[:200]
    # open_patent result: truncate abstract and claims
    for key in ("abstract", "claims_preview"):
        val = sanitized.get(key)
        if isinstance(val, str) and len(val) > 800:
            sanitized[key] = val[:797] + "..."
    return sanitized


# ── Anthropic stream adapter ──────────────────────────────────────────


async def _stream_anthropic_response(
    message: str,
    db: AsyncSession,
):
    """Retrieve patents + stream Anthropic response with tool calls.

    Pipeline:
      1. Embed query → retrieve top-K patents via pgvector
      2. Build system prompt with patent context
      3. Stream Anthropic token-by-token, handling tool-use events
      4. On tool_use: execute tool, emit SSE events, resume stream
      5. Emit sources + done events

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

                    # Emit tool_call_start
                    yield _sse_event(
                        "tool_call_start",
                        name=tool_name,
                        input=tool_input,
                    )

                    # Execute tool
                    try:
                        result = await execute_tool(tool_name, tool_input, db)
                    except Exception:
                        logger.exception(
                            "Tool execution failed: %s", tool_name
                        )
                        result = {
                            "error": f"Tool '{tool_name}' encountered an internal error."
                        }

                    sanitized = _sanitize_tool_result(result)

                    # Emit tool_call_result
                    yield _sse_event(
                        "tool_call_result",
                        name=tool_name,
                        result=sanitized,
                    )

                    # Append tool-use + tool-result to conversation
                    messages.append({
                        "role": "assistant",
                        "content": [{
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": tool_input,
                        }],
                    })
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(sanitized),
                        }],
                    })

                    # Break out of inner loop to restart stream with
                    # updated messages (tool result is now in context)
                    break

            else:
                # Inner loop completed without breaking — no more
                # tool calls; the stream is finished.
                break

        except Exception:
            logger.exception("Anthropic streaming failed")
            yield _sse_event(
                "error",
                message=(
                    "The chat service is temporarily unavailable. "
                    "Please try again."
                ),
            )
            yield _sse_event("done")
            return

    # ── Step 4: Sources + done ────────────────────────────────────
    yield _sse_event("sources", patents=patents)
    yield _sse_event("done")


# ── Endpoint ──────────────────────────────────────────────────────────


@router.post("/stream")
async def chat_stream(
    request: Request,
    body: ChatStreamRequest,
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream an LLM response as Server-Sent Events.

    Auth required (session cookie). Retrieves top-K relevant patents
    and streams an Anthropic response with inline citations and
    optional tool calls.
    """
    logger.info(
        "chat_stream: user=%s message_len=%d conversation_id=%s",
        user_id,
        len(body.message),
        body.conversation_id,
    )

    # Quota stub (real enforcement in PR 6)
    await _check_chat_quota_stub(user_id)

    return StreamingResponse(
        _stream_anthropic_response(body.message, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
