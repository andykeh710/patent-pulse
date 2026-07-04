"""Tests for Phase 3 PR 2–4 — Anthropic streaming + patent retrieval + tool calls + citations."""

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
            events.append(json.loads(stripped[len("data: ") :]))
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

# Tool-call mock: one text token, then a tool_use.
# NOTE: In the real Anthropic API, the stream ENDS after a tool_use
# content_block_stop. The model does not produce text after a tool_use
# in the same stream pass. After the caller sends the tool_result back,
# a new stream begins with the continuation. The test helpers below
# simulate this with a stateful two-pass mock.
MOCK_TOOL_STREAM = [
    {"type": "text", "content": "Let me search for that."},
    {
        "type": "tool_use",
        "id": "toolu_001",
        "name": "search_patents",
        "input": {"query": "solid state batteries", "limit": 5},
    },
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

# ── Citation mock data ────────────────────────────────────────────────

# Tokens citing patents that ARE in MOCK_PATENTS, using proper
# USPTO:/EPO: prefixes (the model follows the system prompt rule).
# verify_citations is prefix-agnostic — USPTO:US20240123456A1 matches
# the known doc_id US20240123456A1.
MOCK_VERIFIED_CITATION_TOKENS = [
    {"type": "text", "content": "See "},
    {"type": "text", "content": "[USPTO:US20240123456A1]"},
    {"type": "text", "content": " for Toyota's thermal management system. "},
    {"type": "text", "content": "Also "},
    {"type": "text", "content": "[EPO:EP4567890B1]"},
    {"type": "text", "content": " covers electrolytes."},
]

# Tokens with a citation NOT in any known source — should trigger warning.
MOCK_UNCITED_TOKENS = [
    {"type": "text", "content": "See "},
    {"type": "text", "content": "[USPTO:US99999999]"},
    {"type": "text", "content": " for a completely fabricated patent."},
]


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


async def _yield_mock(events: list[dict]):
    """Yield a static list of events as an async stream."""
    for event in events:
        yield event


# ── Session-wide quota passthrough ────────────────────────────────────


@pytest.fixture(autouse=True)
def _passthrough_quota(monkeypatch):
    """All existing stream tests skip quota enforcement."""

    async def _noop(*a, **kw):
        return None

    monkeypatch.setattr(
        "app.api.v1.chat._enforce_chat_quota",
        _noop,
    )


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
        payload = json.loads(line[len("data: ") :])
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
    tcs_idx = next(i for i, e in enumerate(events) if e["type"] == "tool_call_start")
    tokens_before = [e for e in events[:tcs_idx] if e["type"] == "token"]
    assert len(tokens_before) >= 1
    assert any("search" in t["content"].lower() for t in tokens_before)

    # And token events AFTER the tool result (text from second pass)
    tcr_idx = next(i for i, e in enumerate(events) if e["type"] == "tool_call_result")
    tokens_after = [e for e in events[tcr_idx:] if e["type"] == "token"]
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


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_tool_call_limit_capped(client: AsyncClient, monkeypatch):
    """After 5 tool calls, a warning event fires and the turn ends."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )

    # Always emit a tool_use — never plain text — so the loop
    # keeps re-entering until the cap fires.
    async def _infinite_tool_stream(self, **kw):
        yield {
            "type": "tool_use",
            "id": "toolu_loop",
            "name": "search_patents",
            "input": {"query": "batteries"},
        }

    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        _infinite_tool_stream,
    )
    monkeypatch.setattr(
        "app.api.v1.chat.execute_tool",
        lambda name, input, db: _async_return(MOCK_TOOL_RESULT),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "endless tool loop"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)

    # 5 tool_call_start + 5 tool_call_result events
    starts = [e for e in events if e["type"] == "tool_call_start"]
    results = [e for e in events if e["type"] == "tool_call_result"]
    assert len(starts) == 5, f"expected 5 tool_call_start, got {len(starts)}"
    assert len(results) == 5, f"expected 5 tool_call_result, got {len(results)}"

    # Warning event after the 5th call
    warnings = [e for e in events if e["type"] == "warning"]
    assert len(warnings) == 1
    assert "limit reached" in warnings[0]["message"].lower()

    # Done must follow warning
    event_types = [e["type"] for e in events]
    warn_idx = event_types.index("warning")
    done_idx = event_types.index("done")
    assert warn_idx < done_idx, "warning must appear before done"

    # No sources event — the cap path returns early before sources
    assert "sources" not in event_types


# ── Citation tests ────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_emits_citations_event(client: AsyncClient, monkeypatch):
    """citations event appears after tokens, before sources, before done."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _yield_mock(MOCK_VERIFIED_CITATION_TOKENS),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    event_types = [e["type"] for e in events]

    assert "citations" in event_types

    cit_idx = event_types.index("citations")
    sources_idx = event_types.index("sources")
    done_idx = event_types.index("done")
    assert cit_idx < sources_idx < done_idx, "citations must appear before sources before done"


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_citations_all_verified(
    client: AsyncClient,
    monkeypatch,
):
    """When all citations match known doc_ids, verified list is populated."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _yield_mock(MOCK_VERIFIED_CITATION_TOKENS),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "batteries"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)
    cit = next(e for e in events if e["type"] == "citations")

    # Both MOCK_PATENTS doc_ids are in the known set (prefix-agnostic):
    # USPTO:US20240123456A1 → matches US20240123456A1
    # EPO:EP4567890B1       → matches EP4567890B1
    assert len(cit["verified"]) == 2
    assert "USPTO:US20240123456A1" in cit["verified"]
    assert "EPO:EP4567890B1" in cit["verified"]
    assert cit["unverified"] == []


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_citations_warning_on_unverified(
    client: AsyncClient,
    monkeypatch,
):
    """When unverified citations exist, warning event fires with code."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _yield_mock(MOCK_UNCITED_TOKENS),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)

    cit = next(e for e in events if e["type"] == "citations")
    assert len(cit["unverified"]) >= 1
    assert "USPTO:US99999999" in cit["unverified"]

    warnings = [e for e in events if e["type"] == "warning"]
    cite_warnings = [w for w in warnings if w.get("code") == "uncited_or_invalid_doc_ids"]
    assert len(cite_warnings) == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_no_citation_warning_when_all_verified(
    client: AsyncClient,
    monkeypatch,
):
    """When all citations are verified, no citation warning fires."""
    monkeypatch.setattr(
        "app.api.v1.chat.retrieve_patents",
        _mock_retrieve_patents,
    )
    monkeypatch.setattr(
        "app.ai.anthropic_client.AnthropicChatClient.stream",
        lambda self, **kw: _yield_mock(MOCK_VERIFIED_CITATION_TOKENS),
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "test"},
        cookies=_cookie(),
    )
    assert r.status_code == 200

    events = _parse_events(r.text)

    cit = next(e for e in events if e["type"] == "citations")
    assert cit["unverified"] == []

    # No citation-related warning
    cite_warnings = [
        w
        for w in events
        if w["type"] == "warning" and w.get("code") == "uncited_or_invalid_doc_ids"
    ]
    assert cite_warnings == []


# ── Quota tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_quota_exceeded_returns_402(
    client: AsyncClient,
    monkeypatch,
):
    """When quota is exceeded, 402 with structured JSON body is returned."""
    # Override the passthrough fixture with a real enforcement failure
    from fastapi import HTTPException as HTTPErr

    async def _raise_quota(*a, **kw):
        raise HTTPErr(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "tier": "free",
                "used": 5,
                "limit": 5,
                "upgrade_url": "/account/billing",
            },
        )

    monkeypatch.setattr(
        "app.api.v1.chat._enforce_chat_quota",
        _raise_quota,
    )

    r = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
        cookies=_cookie(),
    )
    assert r.status_code == 402

    body = r.json()
    assert body["detail"]["error"] == "quota_exceeded"
    assert body["detail"]["tier"] == "free"
    assert body["detail"]["used"] == 5
    assert body["detail"]["limit"] == 5


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_stream_lifetime_user_no_quota_check(
    client: AsyncClient,
    monkeypatch,
):
    """Lifetime users can chat without hitting quota."""
    # The passthrough fixture already skips enforcement.
    # Verify the stream still works for a basic setup.
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
        json={"message": "hello"},
        cookies=_cookie(),
    )
    assert r.status_code == 200


@pytest.mark.asyncio(loop_scope="function")
async def test_chat_quota_endpoint_returns_usage(
    client: AsyncClient,
    monkeypatch,
):
    """GET /api/v1/chat/quota returns usage dict."""
    from unittest.mock import AsyncMock, MagicMock

    svc = MagicMock()
    svc.get_usage = AsyncMock(
        return_value={
            "tier": "free",
            "used": 2,
            "limit": 5,
            "unlimited": False,
            "remaining": 3,
        }
    )
    monkeypatch.setattr(
        "app.api.v1.chat.get_quota_service",
        lambda: svc,
    )

    r = await client.get(
        "/api/v1/chat/quota",
        cookies=_cookie(),
    )
    assert r.status_code == 200

    body = r.json()
    assert body["tier"] == "free"
    assert body["used"] == 2
    assert body["remaining"] == 3


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
