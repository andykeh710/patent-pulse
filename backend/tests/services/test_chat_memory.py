"""Tests for Phase 3 PR 5 — ConversationStore."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_memory import (
    MAX_MESSAGES_PER_CONVERSATION,
    ConversationStore,
)

# ── Helpers ───────────────────────────────────────────────────────────

def _mock_redis():
    """Return an AsyncMock that looks like redis.asyncio.Redis."""
    redis = AsyncMock()
    # pipeline() returns a Pipeline that supports async with
    pipe = MagicMock()
    # Pipeline queueing methods are synchronous in redis-py
    pipe.rpush = MagicMock()
    pipe.ltrim = MagicMock()
    pipe.expire = MagicMock()
    # Only execute() is async
    pipe.execute = AsyncMock()
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=None)
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


# ── new_conversation_id ───────────────────────────────────────────────


class TestNewConversationId:
    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_valid_uuid(self):
        store = ConversationStore(_mock_redis())
        cid = await store.new_conversation_id()
        uuid.UUID(cid)  # raises ValueError if invalid


# ── append + get round-trip ───────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_append_and_get_roundtrip():
    redis = _mock_redis()
    redis.lrange = AsyncMock(return_value=[
        '{"role": "user", "content": "hello"}',
        '{"role": "assistant", "content": "hi there"}',
    ])

    store = ConversationStore(redis)

    await store.append_message("user-1", "conv-1", "user", "hello")
    await store.append_message("user-1", "conv-1", "assistant", "hi there")

    history = await store.get_history("user-1", "conv-1")
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "hello"}
    assert history[1] == {"role": "assistant", "content": "hi there"}


@pytest.mark.asyncio(loop_scope="function")
async def test_append_turn_writes_user_and_assistant_together():
    redis = _mock_redis()
    store = ConversationStore(redis)

    await store.append_turn("user-1", "conv-1", "hello", "hi there")

    pipe = redis.pipeline.return_value
    pipe.rpush.assert_called_once()
    args = pipe.rpush.call_args.args
    assert args[0] == "chat:conv:user-1:conv-1"
    assert len(args) == 3
    assert '"role": "user"' in args[1]
    assert '"content": "hello"' in args[1]
    assert '"role": "assistant"' in args[2]
    assert '"content": "hi there"' in args[2]
    pipe.ltrim.assert_called_once()
    pipe.expire.assert_called_once()
    pipe.execute.assert_awaited_once()


@pytest.mark.asyncio(loop_scope="function")
async def test_get_history_empty_when_key_missing():
    redis = _mock_redis()
    redis.lrange = AsyncMock(return_value=[])

    store = ConversationStore(redis)
    history = await store.get_history("user-1", "conv-nonexistent")
    assert history == []


# ── TTL ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_append_sets_ttl():
    redis = _mock_redis()
    store = ConversationStore(redis)

    await store.append_message("user-1", "conv-1", "user", "hello")

    pipe = redis.pipeline.return_value
    pipe.expire.assert_called_once()
    # expire(key, ttl_seconds) — second positional arg is the TTL
    _, ttl = pipe.expire.call_args[0]
    assert ttl == 30 * 60  # 30 minutes


@pytest.mark.asyncio(loop_scope="function")
async def test_append_trims_to_max_messages():
    redis = _mock_redis()
    store = ConversationStore(redis)

    await store.append_message("user-1", "conv-1", "user", "msg")

    pipe = redis.pipeline.return_value
    pipe.ltrim.assert_called_once()
    # ltrim(key, start, stop) — second and third args
    _, start, stop = pipe.ltrim.call_args[0]
    assert start == -MAX_MESSAGES_PER_CONVERSATION
    assert stop == -1


# ── Key isolation ──────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_different_users_isolated():
    redis = _mock_redis()

    # User 1's history
    redis.lrange = AsyncMock(return_value=[
        '{"role": "user", "content": "user1 msg"}',
    ])

    store = ConversationStore(redis)
    history = await store.get_history("user-1", "conv-shared")
    assert len(history) == 1
    assert history[0]["content"] == "user1 msg"

    # Verify the key includes user_id — by checking the key arg
    call_args = redis.lrange.call_args
    assert "user-1" in call_args[0][0]
    assert "conv-shared" in call_args[0][0]


@pytest.mark.asyncio(loop_scope="function")
async def test_same_conversation_id_different_users_have_separate_keys():
    redis = _mock_redis()
    redis.lrange = AsyncMock(return_value=[])

    store = ConversationStore(redis)

    await store.get_history("alice", "conv-1")
    await store.get_history("bob", "conv-1")

    # Two calls with different keys
    assert redis.lrange.call_count == 2
    key_alice = redis.lrange.call_args_list[0][0][0]
    key_bob = redis.lrange.call_args_list[1][0][0]
    assert "alice" in key_alice
    assert "bob" in key_bob
    assert key_alice != key_bob


# ── Corrupt message handling ──────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_get_history_skips_corrupt_messages():
    redis = _mock_redis()
    redis.lrange = AsyncMock(return_value=[
        '{"role": "user", "content": "good"}',
        'not valid json {{{',
        '{"role": "assistant", "content": "also good"}',
    ])

    store = ConversationStore(redis)
    history = await store.get_history("user-1", "conv-1")
    assert len(history) == 2  # corrupt one skipped
    assert history[0]["content"] == "good"
    assert history[1]["content"] == "also good"


# ── get_history returns valid message format ──────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_get_history_returns_correct_message_format():
    redis = _mock_redis()
    redis.lrange = AsyncMock(return_value=[
        '{"role": "user", "content": "first question"}',
        '{"role": "assistant", "content": "first answer"}',
        '{"role": "user", "content": "second question"}',
    ])

    store = ConversationStore(redis)
    history = await store.get_history("user-1", "conv-1")

    assert len(history) == 3
    for msg in history:
        assert "role" in msg
        assert "content" in msg
        assert msg["role"] in ("user", "assistant")
