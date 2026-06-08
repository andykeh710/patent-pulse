"""
Phase 3 — Chat API (SSE streaming).

PR 1: SSE scaffold with mock LLM. Proves the streaming pipe works
end-to-end before adding retrieval, tools, or Anthropic integration.

Endpoint:
  POST /api/v1/chat/stream
    Request:  {"message": str, "conversation_id": str | None}
    Response: text/event-stream (Server-Sent Events)
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import current_user

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


    # We don't have the session injected here — the caller logs tier.
    logger.info(
        "chat_quota_stub: would enforce quota for user=%s",
        user_id,
    )


# ── Mock LLM stream ───────────────────────────────────────────────────


MOCK_RESPONSE_TEMPLATE = (
    "Hello, you said: '{message}'. Phase 3 is being built."
)


async def _mock_llm_stream(message: str):
    """Yield SSE events character-by-character with a small delay.

    Replaced by Anthropic streaming in PR 2. For now this proves the
    SSE pipe works from FastAPI through the proxy to the frontend.
    """
    response_text = MOCK_RESPONSE_TEMPLATE.format(message=message)

    for char in response_text:
        yield _sse_event("token", content=char)
        await asyncio.sleep(0.03)  # ~33 chars/sec; simulate thinking

    yield _sse_event("done")
    yield _sse_event("meta", input_tokens=0, output_tokens=len(response_text))


# ── Endpoint ──────────────────────────────────────────────────────────


@router.post("/stream")
async def chat_stream(
    request: Request,
    body: ChatStreamRequest,
    user_id: str = Depends(current_user),
):
    """Stream an LLM response as Server-Sent Events.

    Auth required (session cookie). Quota enforcement is stubbed —
    actual limits land in PR 6.
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
        _mock_llm_stream(body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
