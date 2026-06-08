"""Tests for Phase 3 PR 2–3 — Anthropic streaming + patent retrieval + tool calls."""

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
    {"type": "text", "content": "Based"},
    {"type": "text", "content": " on"},
    {"type": "text", "content": " the"},
    {"type": "text", "content": " retrieved"},
    {"type": "text", "content": " patents"},
    {"type": "text", "content": ","},
    {"type": "text", "content": " Toyota"},
    {"type": "text", "content": " has"},
    {"type": "text", "content": " filed"},
    {"type": "text", "content": " a"},
    {"type": "text", "content": " thermal"},
    {"type": "text", "content": " management"},
    {"type": "text", "content": " system"},
    {"type": "text", "content": " [US20240123456A1]"},
    {"type": "text", "content": "."},
]

# Tool-call mock: one text token, then a tool_use, then more text
MOCK_TOOL_STREAM = [
    {"type": "text", "content": "Let me search for that."},
    {
        "type": "tool_use",
        "id": "toolu_001",
        "name": "search_patents",
        "input": {"query": "solid state batteries", "limit": 5},
    },
    {"type": "text", "content": "I found 3 patents related to solid-state batteries."},
]

# Tool result returned by the handler
MOCK_TOOL_RESULT = {
    "results": [
        {
            "doc_id": "USPTO:US99999",
            "title": "Solid-State Battery Electrolyte",
            "abstract_excerpt": "A solid-state electrolyte comprising...",
            "similarity": 0.95,
            "assignees": ["QuantumScape Corp"],
            "publication_date": "2025-01-10",
        },
    ],
    "count": 1,
}


# ── Helpers ───────────────────────────────────────────────────────────

async def _mock_retrieve_patents(*a, **kw):
    """Async mock returning MOCK_PATENTS."""
    return MOCK_PATENTS


async def _mock_retrieve_empty(*a, **kw):
    """Async mock returning empty list."""
    return []


async def _async_return(value):
    """Return a value from an async function — for mocking async callables."""
    return value


async def _fake_token_stream(self, **kw):
    """Simulate an Anthropic streaming response — just text tokens."""
    for token in MOCK_TOKENS:
        yield token


async def _fake_tool_stream(self, **kw):
    """Simulate an Anthropic streaming response with a tool call."""
    for event in MOCK_TOOL_STREAM:
        yield event


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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_empty,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )

    def _fail(self, **kw):
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


# ── Tool call tests ───────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_tool_call_start_event(client: AsyncClient, monkeypatch):
    """When Anthropic emits a tool_use, tool_call_start event is emitted."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )

    # Stateful mock: tool call on first pass, plain text on subsequent
    calls = []

    async def _stream_with_one_tool(self, **kw):
        calls.append(1)
        if len(calls) == 1:
            for event in MOCK_TOOL_STREAM:
                yield event
        else:
            yield {"type": "text", "content": "Done."}

    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _stream_with_one_tool,
    )
    monkeypatch.setattr(
        "app.api.v1.chat.execute_tool",
        lambda name, input, db: _async_return(MOCK_TOOL_RESULT),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "search solid state batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    event_types = [e["type"] for e in events]

    assert "tool_call_start" in event_types
    assert "tool_call_result" in event_types

    tcs = [e for e in events if e["type"] == "tool_call_start"]
    assert len(tcs) >= 1
    assert tcs[0]["name"] == "search_patents"
    assert "input" in tcs[0]


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_tool_call_result_event(client: AsyncClient, monkeypatch):
    """tool_call_result event contains the tool output."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )

    calls = []

    async def _stream_with_one_tool(self, **kw):
        calls.append(1)
        if len(calls) == 1:
            for event in MOCK_TOOL_STREAM:
                yield event
        else:
            yield {"type": "text", "content": "Done."}

    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _stream_with_one_tool,
    )
    monkeypatch.setattr(
        "app.api.v1.chat.execute_tool",
        lambda name, input, db: _async_return(MOCK_TOOL_RESULT),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "search solid state batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    tcr = [e for e in events if e["type"] == "tool_call_result"]
    assert len(tcr) >= 1
    assert tcr[0]["name"] == "search_patents"
    assert "result" in tcr[0]
    assert tcr[0]["result"]["count"] == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_continues_after_tool_result(client: AsyncClient, monkeypatch):
    """After a tool_result, the stream resumes with more tokens."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )

    calls = []

    async def _stream_with_one_tool(self, **kw):
        calls.append(1)
        if len(calls) == 1:
            for event in MOCK_TOOL_STREAM:
                yield event
        else:
            yield {"type": "text", "content": "I found 3 patents related to solid-state batteries."}

    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _stream_with_one_tool,
    )
    monkeypatch.setattr(
        "app.api.v1.chat.execute_tool",
        lambda name, input, db: _async_return(MOCK_TOOL_RESULT),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "search solid state batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)

    # There should be token events BEFORE the tool call
    tcs_idx = next(
        i for i, e in enumerate(events) if e["type"] == "tool_call_start"
    )
    tokens_before = [
        e for e in events[:tcs_idx] if e["type"] == "token"
    ]
    assert len(tokens_before) >= 1
    assert any("search" in t["content"].lower() for t in tokens_before)

    # And token events AFTER the tool result (text from second pass)
    tcr_idx = next(
        i for i, e in enumerate(events) if e["type"] == "tool_call_result"
    )
    tokens_after = [
        e for e in events[tcr_idx:] if e["type"] == "token"
    ]
    assert len(tokens_after) >= 1
    assert any("found" in t["content"].lower() for t in tokens_after)


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_sources_after_tool_calls(client: AsyncClient, monkeypatch):
    """sources event still appears (and after tool calls, before done)."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )

    calls = []

    async def _stream_with_one_tool(self, **kw):
        calls.append(1)
        if len(calls) == 1:
            for event in MOCK_TOOL_STREAM:
                yield event
        else:
            yield {"type": "text", "content": "Done."}

    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _stream_with_one_tool,
    )
    monkeypatch.setattr(
        "app.api.v1.chat.execute_tool",
        lambda name, input, db: _async_return(MOCK_TOOL_RESULT),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    event_types = [e["type"] for e in events]
    assert "sources" in event_types
    assert "done" in event_types


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
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _fake_token_stream,
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hi", "conversation_id": "some-conv-123"},
        cookies=_cookie(),
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
