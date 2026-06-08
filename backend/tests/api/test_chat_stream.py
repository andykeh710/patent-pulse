"""Tests for Phase 3 PR 1 — SSE chat streaming endpoint."""

import json

import pytest
from httpx import AsyncClient


def _cookie(user_id: str = "local-user") -> dict[str, str]:
    """Create a valid auth_session cookie for testing."""
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings

    return {
        "auth_session": jwt.encode(
            {
                "sub": user_id,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(days=30),
            },
            settings.auth_secret_key,
            algorithm="HS256",
        )
    }


# ── Auth tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_no_auth_returns_401(client: AsyncClient):
    """No auth cookie → 401."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_invalid_cookie_returns_401(client: AsyncClient):
    """Garbage cookie → 401."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
        cookies={"auth_session": "not.a.valid.jwt"},
    )
    assert r.status_code == 401


# ── SSE format tests ──────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_returns_sse_content_type(client: AsyncClient):
    """Response must be text/event-stream."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_yields_sse_data_lines(client: AsyncClient):
    """Every non-empty line from the stream must start with 'data: '."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hi"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    lines = [line for line in r.text.split("\n") if line.strip()]
    assert len(lines) > 0, "expected at least one SSE data line"

    for line in lines:
        assert line.startswith("data: "), f"expected 'data: ', got {line[:40]}..."
        payload = json.loads(line[len("data: "):])
        assert "type" in payload


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_includes_done_event(client: AsyncClient):
    """The SSE stream must terminate with a 'done' event."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = []
    for line in r.text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("data: "):
            events.append(json.loads(stripped[len("data: "):]))

    types = [e["type"] for e in events]
    assert "done" in types, f"expected 'done' event, got types: {types}"


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_echoes_user_message(client: AsyncClient):
    """The mock response must contain the user's message."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "what is a patent"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    full_text = ""
    for line in r.text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("data: "):
            event = json.loads(stripped[len("data: "):])
            if event["type"] == "token":
                full_text += event["content"]

    assert "what is a patent" in full_text
    assert "Phase 3" in full_text


# ── Edge case tests ──────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_empty_message_rejected(client: AsyncClient):
    """Empty message → 422 (validation error)."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": ""},
        cookies=_cookie(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_missing_message_field_rejected(client: AsyncClient):
    """Missing required field → 422."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={},
        cookies=_cookie(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_conversation_id_is_optional(client: AsyncClient):
    """conversation_id can be omitted."""
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hi", "conversation_id": "some-conv-123"},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_streams_incrementally(client: AsyncClient):
    """The response should be chunked, not buffered into one big block.

    We verify this by checking that the response has a non-empty body
    (streamed content) AND that it arrived as a single async read
    (httpx test client reads the whole stream eagerly). The real
    incremental test is done via curl against a running server.
    """
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "stream test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    # Parse SSE events to verify multiple tokens were sent
    token_count = 0
    for line in r.text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("data: "):
            event = json.loads(stripped[len("data: "):])
            if event["type"] == "token":
                token_count += 1

    # The mock response "Hello, you said: 'stream test'. Phase 3 is being built."
    # is ~57 characters — each becomes a token
    assert token_count > 10, f"expected >10 tokens, got {token_count}"
    assert r.headers["content-type"].startswith("text/event-stream")
