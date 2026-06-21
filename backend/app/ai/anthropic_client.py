"""
Phase 3 — Async chat streaming client routed through DeepSeek.

Uses ``anthropic.AsyncAnthropic`` SDK pointed at DeepSeek's Anthropic-compatible
endpoint (ANTHROPIC_BASE_URL). Model is ``deepseek-v4-pro``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────

CHAT_MODEL = "deepseek-v4-pro"
CHAT_MAX_TOKENS = 2048


# ── Client ────────────────────────────────────────────────────────────


class AnthropicChatClient:
    """Async chat streaming via Anthropic SDK → DeepSeek compat endpoint.

    Routes through ``ANTHROPIC_BASE_URL`` (default: https://api.deepseek.com/anthropic)
    using the DeepSeek API key. Model is ``deepseek-v4-pro``.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or CHAT_MODEL
        self._base_url = settings.anthropic_base_url
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "API key is not configured; cannot make chat calls"
                )
            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def stream(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = CHAT_MAX_TOKENS,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream events from Anthropic.

        Each yielded dict has a ``type`` key:

          ``{"type": "text", "content": "Hello"}``
              A text token delta. Accumulate these to build the
              assistant's response.

          ``{"type": "tool_use", "id": "toolu_...", "name": "search_patents",
             "input": {"query": "..."}}``
              A completed tool-use block. The caller should execute the
              tool, then resume the conversation with a ``tool_result``
              message.

        Args:
            system: System prompt (retrieved context + instructions).
            messages: Conversation history (latest user message last).
            tools: Optional Anthropic tool definitions.
            max_tokens: Output token limit.

        Yields:
            Dicts with ``type`` field: ``"text"`` or ``"tool_use"``.
        """
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            async with client.messages.stream(**kwargs) as stream:
                current_tool_id: str | None = None
                current_tool_name: str | None = None
                current_tool_input: str = ""

                async for event in stream:
                    if event.type == "content_block_start":
                        content_block = event.content_block
                        if content_block.type == "tool_use":
                            current_tool_id = content_block.id
                            current_tool_name = content_block.name
                            current_tool_input = ""

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            yield {"type": "text", "content": delta.text}
                        elif delta.type == "input_json_delta":
                            current_tool_input += delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_id is not None:
                            try:
                                tool_input = json.loads(current_tool_input)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "Failed to parse tool input JSON: %s",
                                    current_tool_input[:200],
                                )
                                tool_input = {}
                            yield {
                                "type": "tool_use",
                                "id": current_tool_id,
                                "name": current_tool_name,
                                "input": tool_input,
                            }
                            current_tool_id = None
                            current_tool_name = None
                            current_tool_input = ""

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
