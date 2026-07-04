"""
Phase 3 PR 6 — Tier-based daily chat quotas.

Free: 5/day, Basic: 50/day, Lifetime/Enterprise: unlimited.
Stored in Redis with a date suffix so counters auto-roll at UTC midnight.
Check-before-increment prevents going over the limit by 1.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────

KEY_PREFIX = "chat:quota"
QUOTA_KEY_TTL_SECONDS = 86_400  # 24h safety net; date in key handles rollover

TIER_LIMITS: dict[str, int | None] = {
    "free": None,  # set at init from settings
    "basic": None,  # set at init from settings
    "lifetime": None,  # unlimited
    "enterprise": None,  # unlimited
}


def _init_tier_limits() -> None:
    """Populate TIER_LIMITS from settings (called at module import)."""
    TIER_LIMITS["free"] = settings.chat_quota_free
    TIER_LIMITS["basic"] = settings.chat_quota_basic


_init_tier_limits()


# ── Exceptions ────────────────────────────────────────────────────────


class QuotaExceeded(Exception):
    """Raised when a user hits their daily chat limit."""

    def __init__(self, *, tier: str, limit: int, used: int):
        self.tier = tier
        self.limit = limit
        self.used = used
        super().__init__(f"{tier} tier quota exceeded: {used}/{limit}")


# ── Service ───────────────────────────────────────────────────────────


class ChatQuotaService:
    """Redis-backed daily chat quota tracker.

    Each user's daily counter is a Redis integer key under
    ``chat:quota:{user_id}:{YYYY-MM-DD}`` with a 24h TTL.
    """

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self._redis = redis_client

    async def _ensure_redis(self) -> aioredis.Redis | None:
        """Lazy-init the Redis client. Returns None if unavailable."""
        if self._redis is not None:
            return self._redis
        try:
            self._redis = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            logger.warning("Redis unavailable; quota enforcement disabled")
            return None
        return self._redis

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _key(self, user_id: str) -> str:
        return f"{KEY_PREFIX}:{user_id}:{self._today_utc()}"

    async def check_and_increment(self, user_id: str, tier: str) -> int:
        """Check quota and increment if not exceeded.

        Returns the new count. Raises ``QuotaExceeded`` if the limit
        is hit. Unlimited tiers (lifetime, enterprise) return 0 sentinel
        and never increment.
        """
        limit = TIER_LIMITS.get(tier)
        if limit is None:
            return 0  # unlimited tier — no counter

        r = await self._ensure_redis()
        if r is None:
            # Redis down — allow the request (fail-open)
            return 0

        key = self._key(user_id)

        # Check before increment — prevents going over by 1
        current = await r.get(key)
        current_int = int(current) if current else 0
        if current_int >= limit:
            raise QuotaExceeded(tier=tier, limit=limit, used=current_int)

        new_count = await r.incr(key)
        await r.expire(key, QUOTA_KEY_TTL_SECONDS)
        return int(new_count)

    async def get_usage(self, user_id: str, tier: str) -> dict:
        """Read-only usage check."""
        limit = TIER_LIMITS.get(tier)
        if limit is None:
            return {
                "tier": tier,
                "used": 0,
                "limit": None,
                "unlimited": True,
                "remaining": None,
            }

        r = await self._ensure_redis()
        if r is None:
            return {
                "tier": tier,
                "used": 0,
                "limit": limit,
                "unlimited": False,
                "remaining": limit,
            }

        key = self._key(user_id)
        current = await r.get(key)
        used = int(current) if current else 0
        return {
            "tier": tier,
            "used": used,
            "limit": limit,
            "unlimited": False,
            "remaining": max(0, limit - used),
        }


# ── Module-level singleton ────────────────────────────────────────────

_quota_service: ChatQuotaService | None = None


def get_quota_service() -> ChatQuotaService:
    """Return the module-level ChatQuotaService singleton."""
    global _quota_service
    if _quota_service is None:
        _quota_service = ChatQuotaService()
    return _quota_service
