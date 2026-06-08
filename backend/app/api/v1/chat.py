"""
Phase 3 — Chat API (SSE streaming).

PR 1: SSE scaffold with mock LLM.
PR 2: Real Anthropic streaming + patent retrieval layer.

Endpoint:
  POST /api/v1/chat/stream
    Request:  {"message": str, "conversation_id": str | None}
    Response: text/event-stream (Server-Sent Events)
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anthropic_client import get_chat_client
from app.api.deps import current_user, get_db
from app.services.chat_retrieval import build_system_prompt, retrieve_patents

logger = logging.getLogger(__name__)

router = APIRouter()

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


# ── Anthropic stream adapter ──────────────────────────────────────────


async def _stream_anthropic_response(
    message: str,
    db: AsyncSession,
):
    """Retrieve patents + stream Anthropic response as SSE events.

    Pipeline:
      1. Embed query → retrieve top-K patents via pgvector
      2. Build system prompt with patent context
      3. Stream Anthropic token-by-token via SSE
      4. Emit sources + done events

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

    # ── Step 3: Anthropic streaming ───────────────────────────────
    client = get_chat_client()

    try:
        async for token in client.stream(
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
        ):
            yield _sse_event("token", content=token)

    except Exception:
        logger.exception("Anthropic streaming failed")
        yield _sse_event(
            "error",
            message="The chat service is temporarily unavailable. Please try again.",
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
    and streams an Anthropic response with inline citations.
    """
    from fastapi.responses import StreamingResponse

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
