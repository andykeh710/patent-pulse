"""
Phase 3 — Async Anthropic streaming client for the chatbot.

Separate from the existing ``LLMClient`` (which handles batch AI runs
with caching and content-addressed dedup). The chatbot needs:
  - Real-time streaming (SSE)
  - Tool/function calling support (Anthropic native)
  - No caching (every chat query is unique)

Uses ``anthropic.AsyncAnthropic`` for async streaming via
``messages.stream()``. Model is configurable via ``CHAT_MODEL`` env var.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────

CHAT_MODEL = getattr(settings, "chat_model", None) or "claude-sonnet-4-20250514"
CHAT_MAX_TOKENS = 2048


# ── Client ────────────────────────────────────────────────────────────


class AnthropicChatClient:
    """Async Anthropic wrapper for chatbot streaming.

    Minimal — no caching, no artifact persistence. Just stream tokens.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or CHAT_MODEL
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "anthropic_api_key is not configured; cannot make chat calls"
                )
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def stream(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = CHAT_MAX_TOKENS,
    ) -> AsyncIterator[str]:
        """Stream text tokens from Anthropic.

        Yields one text string per content-block delta (a chunk of the
        assistant's response). Does not handle tool-use events yet
        (that lands in PR 3).

        Args:
            system: System prompt (retrieved context + instructions).
            messages: Conversation history (latest user message last).
            max_tokens: Output token limit.

        Yields:
            Text chunks from the streaming response.
        """
        client = self._get_client()

        try:
            async with client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except anthropic.APIError as e:
            logger.error(
                "Anthropic chat stream error: %s (status=%s)",
                e,
                getattr(e, "status_code", None),
            )
            raise


def get_chat_client() -> AnthropicChatClient:
    """Return a new chat client instance.

    Stateless — safe to create per-request.
    """
    return AnthropicChatClient()
