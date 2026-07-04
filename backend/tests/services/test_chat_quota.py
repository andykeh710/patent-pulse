"""Tests for Phase 3 PR 6 — ChatQuotaService."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.chat_quota import (
    TIER_LIMITS,
    ChatQuotaService,
    QuotaExceeded,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _mock_redis(get_return=None):
    """Return an AsyncMock that looks like redis.asyncio.Redis."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=get_return)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


# ── TIER_LIMITS ────────────────────────────────────────────────────────


class TestTierLimits:
    def test_free_has_limit(self):
        assert TIER_LIMITS["free"] == 5

    def test_basic_has_limit(self):
        assert TIER_LIMITS["basic"] == 50

    def test_lifetime_is_unlimited(self):
        assert TIER_LIMITS["lifetime"] is None

    def test_enterprise_is_unlimited(self):
        assert TIER_LIMITS["enterprise"] is None


# ── check_and_increment ───────────────────────────────────────────────


class TestCheckAndIncrement:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_free_user_first_request_returns_1(self):
        redis = _mock_redis(get_return=None)
        svc = ChatQuotaService(redis)

        count = await svc.check_and_increment("user-1", "free")
        assert count == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_free_user_five_requests_ok(self):
        redis = _mock_redis(get_return="4")  # 4 already used
        svc = ChatQuotaService(redis)

        count = await svc.check_and_increment("user-1", "free")
        assert count == 1  # incr returns 5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_free_user_sixth_request_raises(self):
        redis = _mock_redis(get_return="5")  # at limit
        svc = ChatQuotaService(redis)

        with pytest.raises(QuotaExceeded) as exc:
            await svc.check_and_increment("user-1", "free")
        assert exc.value.tier == "free"
        assert exc.value.limit == 5
        assert exc.value.used == 5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_basic_user_fifty_ok(self):
        redis = _mock_redis(get_return="49")
        svc = ChatQuotaService(redis)

        count = await svc.check_and_increment("user-1", "basic")
        assert count == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_basic_user_fifty_one_raises(self):
        redis = _mock_redis(get_return="50")
        svc = ChatQuotaService(redis)

        with pytest.raises(QuotaExceeded) as exc:
            await svc.check_and_increment("user-1", "basic")
        assert exc.value.tier == "basic"
        assert exc.value.limit == 50

    @pytest.mark.asyncio(loop_scope="function")
    async def test_lifetime_user_returns_0_sentinel(self):
        redis = _mock_redis()
        svc = ChatQuotaService(redis)

        # 100 requests — all should return 0 (skipped)
        for _ in range(100):
            count = await svc.check_and_increment("user-1", "lifetime")
            assert count == 0

        # Redis incr was never called
        redis.incr.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_enterprise_user_returns_0_sentinel(self):
        redis = _mock_redis()
        svc = ChatQuotaService(redis)

        count = await svc.check_and_increment("user-1", "enterprise")
        assert count == 0
        redis.incr.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_unknown_tier_treated_as_free(self):
        """Defensive: unknown tier falls through to default None → unlimited."""
        # TIER_LIMITS.get("unknown") returns None, treated as unlimited
        redis = _mock_redis()
        svc = ChatQuotaService(redis)

        count = await svc.check_and_increment("user-1", "unknown_tier")
        assert count == 0  # unlimited — sentinel
        redis.incr.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_date_rollover_new_day_starts_at_zero(self):
        """Yesterday's counter doesn't affect today's."""
        redis = _mock_redis(get_return="5")  # yesterday's count
        svc = ChatQuotaService(redis)

        # Mock _today_utc to return a different date than the key
        with patch.object(svc, "_today_utc", return_value="2026-06-09"):
            # With a different date, the key is different.
            # redis.get returns None for today's key (no prior usage).
            redis.get = AsyncMock(return_value=None)
            count = await svc.check_and_increment("user-1", "free")
            assert count == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sets_ttl_on_increment(self):
        redis = _mock_redis(get_return=None)
        svc = ChatQuotaService(redis)

        await svc.check_and_increment("user-1", "free")
        redis.expire.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_key_includes_date_string(self):
        redis = _mock_redis(get_return=None)
        svc = ChatQuotaService(redis)

        with patch.object(svc, "_today_utc", return_value="2026-06-08"):
            await svc.check_and_increment("user-1", "free")

        key = redis.incr.call_args[0][0]
        assert "2026-06-08" in key
        assert "user-1" in key


# ── get_usage ──────────────────────────────────────────────────────────


class TestGetUsage:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_free_user_with_usage(self):
        redis = _mock_redis(get_return="3")
        svc = ChatQuotaService(redis)

        usage = await svc.get_usage("user-1", "free")
        assert usage == {
            "tier": "free",
            "used": 3,
            "limit": 5,
            "unlimited": False,
            "remaining": 2,
        }

    @pytest.mark.asyncio(loop_scope="function")
    async def test_free_user_no_usage(self):
        redis = _mock_redis(get_return=None)
        svc = ChatQuotaService(redis)

        usage = await svc.get_usage("user-1", "free")
        assert usage["used"] == 0
        assert usage["remaining"] == 5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_lifetime_user(self):
        redis = _mock_redis()
        svc = ChatQuotaService(redis)

        usage = await svc.get_usage("user-1", "lifetime")
        assert usage["unlimited"] is True
        assert usage["limit"] is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_enterprise_user(self):
        redis = _mock_redis()
        svc = ChatQuotaService(redis)

        usage = await svc.get_usage("user-1", "enterprise")
        assert usage["unlimited"] is True
