"""
Phase 3 PR 5 — Redis-backed conversation memory.

Multi-turn chat history stored in Redis LISTs, keyed per-user so
conversations are isolated. Sliding 30-minute TTL, capped at 10
turns (20 messages). Tool-call sequences within a turn are NOT
persisted — only the final user message + assistant response.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────

CONVERSATION_TTL_SECONDS = 30 * 60  # 30 minutes, sliding
MAX_MESSAGES_PER_CONVERSATION = 20  # 10 turns × 2 (user + assistant)
KEY_PREFIX = "chat:conv"


# ── ConversationStore ──────────────────────────────────────────────────


class ConversationStore:
    """Redis-backed conversation history.

    Each conversation is a Redis LIST under ``chat:conv:{user_id}:{conv_id}``.
    Messages are JSON strings: ``{"role": "user"|"assistant", "content": "..."}``.
    """

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self._redis = redis_client

    async def _ensure_redis(self) -> aioredis.Redis | None:
        """Lazy-init the Redis client. Returns None if Redis is unavailable."""
        if self._redis is not None:
            return self._redis
        try:
            self._redis = aioredis.Redis.from_url(
                settings.redis_url, decode_responses=True
            )
        except Exception:
            logger.warning("Failed to connect to Redis; conversation memory disabled")
            return None
        return self._redis

    def _key(self, user_id: str, conversation_id: str) -> str:
        return f"{KEY_PREFIX}:{user_id}:{conversation_id}"

    def _message_payload(self, role: str, content: str) -> str:
        return json.dumps({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def new_conversation_id(self) -> str:
        """Generate a fresh UUID for a new conversation."""
        return str(uuid.uuid4())

    async def get_history(
        self, user_id: str, conversation_id: str
    ) -> list[dict[str, Any]]:
        """Return messages in chronological order (oldest first).

        Each message is ``{"role": "user"|"assistant", "content": "..."}``.
        Returns ``[]`` if the key doesn't exist or Redis is down.
        """
        r = await self._ensure_redis()
        if r is None:
            return []

        try:
            key = self._key(user_id, conversation_id)
            raw = await r.lrange(key, 0, -1)
        except Exception:
            logger.exception("Failed to read conversation history from Redis")
            return []

        messages: list[dict[str, Any]] = []
        for item in raw:
            try:
                messages.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                logger.warning("Corrupt message in conversation %s", conversation_id)
        return messages

    async def append_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the conversation history.

        Trims to ``MAX_MESSAGES_PER_CONVERSATION`` (oldest first out) and
        resets the sliding TTL.
        """
        r = await self._ensure_redis()
        if r is None:
            return

        try:
            key = self._key(user_id, conversation_id)
            payload = self._message_payload(role, content)
            async with r.pipeline() as pipe:
                pipe.rpush(key, payload)
                pipe.ltrim(key, -MAX_MESSAGES_PER_CONVERSATION, -1)
                pipe.expire(key, CONVERSATION_TTL_SECONDS)
                await pipe.execute()
        except Exception:
            logger.exception("Failed to append message to conversation history")

    async def append_turn(
        self,
        user_id: str,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """Append a completed user/assistant turn without interleaving."""
        r = await self._ensure_redis()
        if r is None:
            return

        try:
            key = self._key(user_id, conversation_id)
            user_payload = self._message_payload("user", user_content)
            assistant_payload = self._message_payload("assistant", assistant_content)
            async with r.pipeline() as pipe:
                pipe.rpush(key, user_payload, assistant_payload)
                pipe.ltrim(key, -MAX_MESSAGES_PER_CONVERSATION, -1)
                pipe.expire(key, CONVERSATION_TTL_SECONDS)
                await pipe.execute()
        except Exception:
            logger.exception("Failed to append turn to conversation history")


# ── Module-level singleton ────────────────────────────────────────────

_conversation_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Return the module-level ConversationStore singleton."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore()
    return _conversation_store
