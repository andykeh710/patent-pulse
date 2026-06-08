"""Tests for Phase 3 PR 2 — Anthropic streaming + patent retrieval."""

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


def _parse_events(text: str) -> list[dict]:
    """Parse SSE text into a list of event dicts."""
    events = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("data: "):
            events.append(json.loads(stripped[len("data: "):]))
    return events


# ── Mock data ─────────────────────────────────────────────────────────

MOCK_PATENTS = [
    {
        "doc_id": "US20240123456A1",
        "title": "Thermal Management System for Solid-State Batteries",
        "abstract_excerpt": "A thermal management system comprising a plurality of heat dissipation elements…",
        "assignees": ["Toyota Motor Corp"],
        "publication_date": "2024-03-15",
        "similarity": 0.92,
    },
    {
        "doc_id": "EP4567890B1",
        "title": "Electrolyte Composition for Lithium Batteries",
        "abstract_excerpt": "An electrolyte composition including a lithium salt and a non-aqueous solvent…",
        "assignees": ["Panasonic Corp"],
        "publication_date": "2024-01-20",
        "similarity": 0.87,
    },
]

MOCK_TOKENS = [
    "Based",
    " on",
    " the",
    " retrieved",
    " patents",
    ",",
    " Toyota",
    " has",
    " filed",
    " a",
    " thermal",
    " management",
    " system",
    " [US20240123456A1]",
    ".",
]


# ── Auth tests (unchanged from PR 1) ──────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_no_auth_returns_401(client: AsyncClient):
    r = await client.post("/api/v1/chat/stream", json={"message": "hello"})
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_invalid_cookie_returns_401(client: AsyncClient):
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
        cookies={"auth_session": "not.a.valid.jwt"},
    )
    assert r.status_code == 401


# ── SSE format tests ──────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_returns_sse_content_type(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    # Provide a fake stream
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "solid state batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_yields_sse_data_lines(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "battery tech"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    lines = [line for line in r.text.split("\n") if line.strip()]
    assert len(lines) > 0

    for line in lines:
        assert line.startswith("data: ")
        payload = json.loads(line[len("data: "):])
        assert "type" in payload


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_includes_done_event(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    types = [e["type"] for e in events]
    assert "done" in types


# ── Retrieval + streaming tests ───────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_emits_meta_event(client: AsyncClient, monkeypatch):
    """First SSE event should be 'meta' with model and retrieved_count."""
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    assert len(events) > 0
    meta = events[0]
    assert meta["type"] == "meta"
    assert "model" in meta
    assert meta["retrieved_count"] == len(MOCK_PATENTS)


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_emits_sources_before_done(client: AsyncClient, monkeypatch):
    """A 'sources' event with patent list must appear before 'done'."""
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    sources_idx = next(i for i, e in enumerate(events) if e["type"] == "sources")
    done_idx = next(i for i, e in enumerate(events) if e["type"] == "done")
    assert sources_idx < done_idx, "sources must appear before done"

    sources = events[sources_idx]
    assert "patents" in sources
    assert len(sources["patents"]) == len(MOCK_PATENTS)
    assert sources["patents"][0]["doc_id"] == MOCK_PATENTS[0]["doc_id"]


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_streams_from_anthropic(client: AsyncClient, monkeypatch):
    """Token events should contain the mock Anthropic response text."""
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "solid state batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    full_text = ""
    for event in _parse_events(r.text):
        if event["type"] == "token":
            full_text += event["content"]

    assert "Toyota" in full_text
    assert "US20240123456A1" in full_text


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_empty_retrieval(client: AsyncClient, monkeypatch):
    """When no patents match, stream still works with empty-context prompt."""
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: [],
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "something obscure"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    meta = events[0]
    assert meta["retrieved_count"] == 0
    assert "done" in [e["type"] for e in events]


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_anthropic_error(client: AsyncClient, monkeypatch):
    """Anthropic errors produce an 'error' event + 'done'."""
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )

    async def _fail(**kw):
        raise RuntimeError("Simulated Anthropic failure")

    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fail,
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    types = [e["type"] for e in events]
    assert "error" in types
    assert "done" in types


# ── Edge case tests ──────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_empty_message_rejected(client: AsyncClient):
    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": ""},
        cookies=_cookie(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_missing_message_field_rejected(client: AsyncClient):
    r = await client.post(
        "/api/v1/chat/stream",
        json={},
        cookies=_cookie(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_conversation_id_is_optional(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.chat_retrieval.retrieve_patents",
        lambda *a, **kw: MOCK_PATENTS,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _fake_token_stream(),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hi", "conversation_id": "some-conv-123"},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]


# ── Helpers ───────────────────────────────────────────────────────────


async def _fake_token_stream():
    """Simulate an Anthropic streaming response."""
    for token in MOCK_TOKENS:
        yield token
