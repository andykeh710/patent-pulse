# Phase 3 — RAG Chatbot MVP: Implementation Audit

**Date:** 2026-06-08  
**Author:** Hermes (investigation, no code)  
**Source:** `.hermes/plans/2026-06-04_v3-roadmap.md` Part I Section 4  
**Status:** INVESTIGATION COMPLETE — ready for Andy review

---

## 1 — Existing Infrastructure to Reuse

### 1.1 Patent Embeddings

| Metric | Value |
|--------|-------|
| Model | OpenAI `text-embedding-3-small` (1536-dim) |
| Column | `patent_publications.embedding` (`Vector(1536)`) |
| Coverage | 17,706 / 64,231 (27.6%) — backfill mid-flight via PR #21 |
| Index | HNSW `idx_patents_embedding_hnsw` (m=16, ef_construction=64), cosine ops |
| Search | `<=>` operator with `ef_search=100` per-session |

**Reuse for chatbot RAG:** Directly usable. The `PatentEmbedder` class in
`backend/app/ai/embedder.py` generates 1536-dim embeddings from title+abstract.
The `POST /semantic/query` endpoint already does vector similarity search with
`min_similarity` and `limit` params. The chatbot retrieval layer can reuse the
same `PatentEmbedder` call and the same HNSW index.

**Gap:** Embedding coverage is only 27.6%. For a chatbot to cite patents, the
retrieved candidates pool is ~17K patents. Backfill should reach >90% before
the chatbot ships. PR #21's fix is deployed but backfill velocity is unknown.

### 1.2 News Items Embeddings

| Metric | Value |
|--------|-------|
| Model | Same OpenAI `text-embedding-3-small` (1536-dim) |
| Column | `news_items.embedding` (`Vector(1536)`) |
| Coverage | **Unknown — no evidence of news embedding backfill** |
| Index | **None** — no pgvector index on `news_items.embedding` |
| Rows | Unknown — `NewsItem` model exists, `news_ingestion.py` task exists |

**Reuse for chatbot RAG:** The column and model exist, but there is **no
evidence that news items have embeddings populated**. The `NewsItem` model
(`backend/app/core/models.py` line 218) has the embedding column. The news
ingestion task (`backend/app/tasks/news_ingestion.py`) fetches RSS feeds and
persists news items but does **not** call the embedder.

**What needs to happen before chatbot RAG can include news:**
1. Add an HNSW index on `news_items.embedding` (matching patent pattern)
2. Add embedding generation to the news ingestion pipeline
3. Backfill existing news items

**Recommendation:** Defer news retrieval to a follow-up PR. The chatbot MVP
can ship with patent-only retrieval (K=8 patents). News is a smaller corpus
and lower-quality for patent questions anyway. Add it in Phase 3.5 or V4.

### 1.3 Semantic Search Endpoints

Three endpoints exist in `backend/app/api/v1/semantic_search.py`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/semantic/query` | POST | Natural language → top-K patents by cosine similarity |
| `/api/v1/semantic/similar/{id}` | GET | Patent → top-K similar patents |
| `/api/v1/semantic/novelty/{id}` | GET | Patent → novelty score vs prior art |

**Reuse for chatbot:** The `/semantic/query` endpoint is nearly a drop-in
retrieval layer. The chatbot's retrieval step can:
1. Call `PatentEmbedder.generate_embedding(query)`
2. Run `SELECT ... ORDER BY embedding <=> :q LIMIT :k`
3. Return top-K patent records with title, abstract, assignees, doc_id

The chatbot should use `min_similarity=0.4` (lower than the search UI's 0.5
default — conversational queries are shorter and less precise).

### 1.4 Conversation / Session Storage

**None.** No existing session-scoped Redis storage pattern in the codebase.
Redis is used for:
- Celery broker + result backend (`redis://redis:6379/0`)
- Thumbnail cache (key: `thumb:{doc_id}`, TTL: 1 hour, in `patents.py`)
- Distributed lock for enrichment (`enrich_abstracts.py`, key: `enrich_lock`,
  TTL: 600s)

All three are primitive key-value usage (no hashes, no lists, no sorted sets).
No existing conversation state management, no chat history tables in the DB,
no session-scoped key namespace pattern.

**Pattern to establish:** Namespace chat keys under `chat:{user_id}:...`
and set TTL on the entire Redis hash with `EXPIRE`. Use `HSET` for each
message and `EXPIRE` after each write to reset the 30-min TTL.

### 1.5 LLM Client

| Aspect | Detail |
|--------|--------|
| Class | `LLMClient` in `backend/app/ai/llm_client.py` (745 lines) |
| Providers | DeepSeek (primary, via `httpx` raw HTTP) and Anthropic (secondary, via SDK) |
| Default model | `deepseek-chat` (set in `settings.llm_provider = "deepseek"`) |
| Anthropic model | `claude-sonnet-4-20250514` |
| Cache | Content-addressed, `AIArtifact` table, hash-based dedup |
| Streaming | **None** — both `_call_deepseek` and Anthropic `messages.create` are blocking |
| Tool calling | **None** — neither provider is called with tool definitions |

**Critical finding:** The existing `LLMClient.complete()` method is
fundamentally a request-response pattern. For the chatbot, we need a
**separate streaming client** that:
1. Supports SSE output (`text/event-stream`)
2. Supports tool/function calling (Anthropic tool use or DeepSeek function
   calling)
3. Does **not** use the `AIArtifact` cache (chat responses are unique,
   ephemeral, and should not pollute the artifact table)

**Recommendation:** Create a new `ChatClient` class separate from `LLMClient`.
The chatbot's needs (streaming, tools, no caching) are different enough that
shoehorning them into `LLMClient` would create a god object. The `ChatClient`
wraps `anthropic.Anthropic.messages.stream()` for Anthropic or a homegrown
streaming wrapper for DeepSeek's OpenAI-compatible endpoint.

---

## 2 — SSE Streaming

### 2.1 Existing SSE Patterns

**Zero.** A grep for `StreamingResponse` finds only one usage:

```
backend/app/api/v1/exports.py:115: return StreamingResponse(
    io.BytesIO(csv_bytes),
    media_type="text/csv",
    headers={"Content-Disposition": f"attachment; filename=expiry-{today}.csv"},
)
```

This is file-download streaming, not SSE. The chatbot needs `text/event-stream`
with `Transfer-Encoding: chunked`. No existing middleware intercepts or
interferes with streaming responses.

### 2.2 Streaming SDK Support

**Anthropic (recommended for chatbot):**
- SDK: `anthropic` v0.40+ (confirmed in `pyproject.toml`)
- Streaming: `client.messages.stream()` returns `Stream[RawMessageStreamEvent]`
- Pattern:
  ```python
  with client.messages.stream(
      model="claude-sonnet-4-20250514",
      max_tokens=4096,
      system=system_prompt,
      messages=messages,
      tools=tool_definitions,
  ) as stream:
      for text in stream.text_stream:
          yield text
  ```
- Tool events: `stream` also yields `content_block_start` / `content_block_delta`
  events for tool calls. The consumer can inspect event types.
- SSE adapter: Wrap the stream iterator in an async generator that yields
  `data: {"type": "text", "content": "..."}\n\n` chunks.

**DeepSeek (cheaper, but weaker for tools):**
- API: OpenAI-compatible `/chat/completions` with `stream: true`
- SDK: Not using SDK — raw `httpx` in `_call_deepseek()`
- Streaming: Add `"stream": true` to the JSON payload. Response becomes
  `text/event-stream` with `data: {"choices":[{"delta":{"content":"..."}}]}\n\n`
- Tool calling: DeepSeek supports OpenAI-compatible function calling but
  multi-turn tool loops are less robust than Anthropic's native tool use.

### 2.3 Frontend EventSource

**Zero existing usage.** No `EventSource`, `fetch` with streaming
(`response.body.getReader()`), or `useChat` / `useStream` patterns in the
frontend.

**Frontend streaming plan:**
```typescript
// Preferred pattern: fetch + ReadableStream (more flexible than EventSource)
const response = await fetch('/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: '...', history: [...] }),
});
const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  // Parse SSE lines, update React state for each chunk
}
```

This pattern supports POST (EventSource is GET-only), custom headers (auth),
and abort via `AbortController`. No library dependency needed — ~40 lines of
custom hook.

---

## 3 — Tool Calls

### 3.1 Provider Support

| Feature | Anthropic | DeepSeek |
|---------|-----------|----------|
| Tool/function calling | Native `tools` param on `messages.create` | OpenAI-compatible `tools` param |
| Streaming + tools | Yes — tool events interleaved with text | Yes — `delta.tool_calls` |
| Multi-turn tool loop | Excellent — content blocks include `tool_use` | Adequate — OpenAI pattern |
| Structured output | Native JSON mode | OpenAI-compatible `response_format` |
| API cost | $3/$15 per M tokens | $0.27/$1.10 per M tokens |

**Recommendation: Use Anthropic for the chatbot**, even though DeepSeek is the
default for batch AI runs. The chatbot needs:
- Reliable tool calling with multi-turn loops
- Structured thinking (system prompt enforcement works better on Anthropic)
- Streaming quality (DeepSeek streaming can truncate mid-token)

Cost difference: ~$0.12/query (Anthropic) vs ~$0.002/query (DeepSeek) for
typical 2K input + 500 output. At 50 queries/day/user, Anthropic would cost
~$180/month for 100 active users. Worth it for quality. DeepSeek can be a
fallback tier option.

### 3.2 Tool Schemas

#### Tool 1: `search_patents`

```json
{
  "name": "search_patents",
  "description": "Search the patent database by natural language query with optional filters. Returns top-K matching patents with titles, abstracts, assignees, and publication numbers.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query, e.g. 'solid-state battery thermal management'"
      },
      "office": {
        "type": "string",
        "enum": ["USPTO", "EPO", "WIPO", null],
        "description": "Filter by patent office"
      },
      "date_from": {
        "type": "string",
        "description": "Publication date lower bound (YYYY-MM-DD)"
      },
      "limit": {
        "type": "integer",
        "default": 5,
        "minimum": 1,
        "maximum": 20
      }
    },
    "required": ["query"]
  }
}
```

**Backend implementation:** Calls `PatentEmbedder.generate_embedding(query)`,
runs pgvector cosine similarity search with `min_similarity=0.4`. Applies
optional office/date filters. Returns `PatentSearchResult[]` with:
```json
{
  "doc_id": "US12345678B2",
  "title": "...",
  "abstract": "first 300 chars...",
  "assignees": ["Acme Corp"],
  "publication_date": "2024-03-15",
  "similarity": 0.87,
  "url": "/patents/US12345678B2"
}
```

#### Tool 2: `open_patent`

```json
{
  "name": "open_patent",
  "description": "Retrieve full details of a specific patent by its document ID. Returns title, abstract, claims summary, assignees, expiry status, and citation links.",
  "input_schema": {
    "type": "object",
    "properties": {
      "doc_id": {
        "type": "string",
        "description": "Patent document ID, e.g. 'US12345678B2'"
      }
    },
    "required": ["doc_id"]
  }
}
```

**Backend implementation:** `SELECT ... FROM patent_publications WHERE doc_id = :id`.
Returns full `PatentDetail` including abstract, first claim, expiry assessment,
usage signals, and external links. This is the same data shape as
`GET /api/v1/patents/{id}`.

#### Tool 3: `compare_companies`

```json
{
  "name": "compare_companies",
  "description": "Compare patent portfolios of multiple companies. Returns filing counts, top CPC areas, recent filing trends, and overlapping technology areas.",
  "input_schema": {
    "type": "object",
    "properties": {
      "names": {
        "type": "array",
        "items": { "type": "string" },
        "minItems": 2,
        "maxItems": 5,
        "description": "Company/assignee names to compare, e.g. ['Tesla', 'Toyota', 'Panasonic']"
      }
    },
    "required": ["names"]
  }
}
```

**Backend implementation:** Queries `assignees_normalized` table for each name,
joins `patent_publications` for filing counts by year and CPC prefix.
Returns per-company summary:
```json
{
  "companies": [
    {
      "name": "Tesla",
      "total_patents": 8421,
      "top_cpc_areas": ["H01M", "B60L", "G06F"],
      "recent_filing_trend": "increasing",
      "shared_cpc_areas_with_others": ["H01M", "B60L"]
    }
  ]
}
```

---

## 4 — Citation Enforcement

### 4.1 Enforcement Strategies (ranked by strength)

**Strategy A: Provider-level forced tool use (strongest)**
Anthropic's `tool_choice` parameter can force the model to call a tool before
responding. Set `tool_choice: {"type": "any"}` to require at least one tool call.
This ensures every response is grounded in retrieved data. However, it's too
aggressive — the chatbot should be able to clarify questions or say "I don't
know" without a tool call.

**Strategy B: System-prompt reinforcement + post-generation regex check (pragmatic)**
1. System prompt includes: "Every factual claim MUST include a citation in the
   format `[Source: doc_id](link)`. If no source supports a claim, do not make
   the claim. If you have no sources, say 'I don't have enough information to
   answer that.'"
2. After generation, scan the response for `\[Source: [A-Z]{2}\d+\]`.
3. If no citations found AND the response contains factual claims (heuristic:
   response length >100 chars, not an apology/decline), either:
   - **Reject and retry** with stronger system prompt
   - **Display with warning** banner "This response may contain unsourced claims"

**Strategy C: Structured output with required citations field (most robust)**
Require the LLM to output JSON with a `claims` array and a `sources` array.
Every claim must reference a source by index. This guarantees structure but
degrades the conversational experience — raw JSON is not readable.

**Recommendation: Strategy B (pragmatic).** Post-generation regex check with
retry (max 2 attempts). On second failure, show response with warning.
The system prompt is the primary enforcement; regex is the safety net.

### 4.2 System Prompt Citation Format

```
CITATION RULES:
1. Every factual claim about a patent, company, technology, or market MUST
   include a citation.
2. Citation format: [Source: DOC_ID](https://inventionindex8.com/patents/DOC_ID)
3. If you are unsure or have no source, say "I don't have enough information to
   confirm that." Never fabricate.
4. Example: "Toyota has increased solid-state battery filings 40% YoY
   [Source: JP2024-12345A](https://inventionindex8.com/patents/JP2024-12345A)"
```

### 4.3 Retrieval Context Injection

Each retrieved patent chunk in the system prompt should include its doc_id
explicitly to make citation easy:

```
RETRIEVED PATENTS:
[1] US20240123456A1 — "Thermal Management System for Solid-State Batteries"
    Assignee: Toyota Motor Corp | Published: 2024-03-15
    Abstract: A thermal management system comprising...
[2] EP4567890B1 — "Electrolyte Composition for Lithium Batteries"
    ...
```

The LLM cites `[1]` or `US20240123456A1` directly.

---

## 5 — Conversation Memory

### 5.1 Redis Schema

```
Key:   chat:history:{user_id}
Type:  LIST
Value: JSON-encoded messages, newest at HEAD (RPUSH)
TTL:   1800 seconds (30 minutes), reset on each append

Message format:
{
  "role": "user" | "assistant" | "tool",
  "content": "..." | null,
  "tool_name": "search_patents" | null,
  "tool_result": [...] | null,
  "timestamp": "2026-06-08T14:30:00Z"
}
```

**Operations:**
- **Read history:** `LRANGE chat:history:{user_id} 0 -1` → parse JSON
- **Append message:** `RPUSH chat:history:{user_id} '{...}'`
- **Enforce 10-turn cap:** After RPUSH, `LTRIM chat:history:{user_id} -20 0`
  (keep last 20 messages = 10 turns)
- **Reset TTL:** `EXPIRE chat:history:{user_id} 1800` on every write
- **Clear on /new:** `DEL chat:history:{user_id}`

### 5.2 Context Window Management

Each turn (user message + assistant response) is 2 messages. 10-turn cap =
20 messages. With tool calls, 1 turn can be 4 messages
(user → assistant → tool_result → assistant). Cap at 40 messages to
accommodate tool-heavy turns while still bounding total context.

**Token budget:**
- System prompt: ~500 tokens
- Retrieved context (8 patents × 300 chars abstract): ~2000 tokens
- History (20 messages × 100 tokens avg): ~2000 tokens
- Current query: ~100 tokens
- **Total input: ~4600 tokens** — well within Anthropic's 200K context window
- Output: 500-1500 tokens (streamed)

### 5.3 Edge Cases

- **TTL expiry mid-conversation:** User sends query after 31 minutes → history
  is gone. Respond to new query with no prior context. Normal behavior.
- **Redis unavailable:** Fall back to stateless mode (single-turn, no memory).
  Log warning. Do not crash.
- **Message size:** Cap at 10KB per message (prevent abuse). Reject with 400.
- **Concurrent sessions:** Per-user key (no device/session isolation needed
  for MVP). Multiple browser tabs share the same history.

---

## 6 — Quota Wiring

### 6.1 Existing Tier Structure

From `backend/app/quotas/limits.py` and V3 roadmap §5:

| Tier | Chat queries/day | Implementation |
|------|-----------------|----------------|
| Free | 5 | Counter in Redis |
| Basic | 50 | Counter in Redis |
| Lifetime | Unlimited | Skip counter |
| Enterprise | Unlimited | Skip counter |

### 6.2 Quota Enforcement Pattern

Existing pattern from `quotas/limits.py` uses:
- `check_topic_quota(user_id, session)` — checks count vs limit, raises 402
- `require_tier(*allowed_tiers)` — FastAPI dependency, raises 402

New pattern for chat quotas:

```python
# Key: chat:quota:{user_id}:{date_iso}
# Use Redis INCR with TTL = seconds until midnight

async def check_chat_quota(user_id: str, tier: str) -> bool:
    """Return True if user has remaining chat quota for today."""
    if tier in ("lifetime", "enterprise"):
        return True
    limits = {"free": 5, "basic": 50}
    max_queries = limits.get(tier, 0)
    if max_queries == 0:
        return False

    key = f"chat:quota:{user_id}:{date.today().isoformat()}"
    count = await redis.incr(key)
    if count == 1:
        # Set TTL to midnight UTC
        seconds_until_midnight = ...
        await redis.expire(key, seconds_until_midnight)

    return count <= max_queries
```

### 6.3 429 / 402 Response Pattern

Existing pattern: 402 for tier-gated features (exports, reports, API keys),
429 for rate limiting (slowapi).

Recommendation for chatbot: Use **402** (payment required) for quota
exhaustion (matches existing `quotas/limits.py` pattern). Response body:

```json
{
  "detail": "Daily chat quota reached (5/5). Upgrade to Basic for 50 queries/day.",
  "quota": {"used": 5, "limit": 5, "tier": "free", "upgrade_url": "/account/billing"},
  "resets_at": "2026-06-09T00:00:00Z"
}
```

---

## 7 — UI

### 7.1 /chat Full-Screen Page

**Route:** `frontend/src/app/(app)/chat/page.tsx`

**Layout:** 
- Takes full viewport height below TopNav (`min-h-[calc(100vh-3.5rem)]`)
- Two-column on desktop: conversation panel (70%) + patent detail drawer (30%)
- Single-column on mobile: conversation only, drawer as overlay

**Components needed:**
- `ChatPanel`: message list + input area + streaming indicator
- `ChatMessage`: avatar, role label, markdown content with citation links
- `ChatInput`: textarea with submit button, 2000-char limit
- `CitationLink`: renders `[Source: DOC_ID](url)` as stylized badge
- `PatentDrawer`: slide-out panel showing patent detail (reuse `PatentPage` data)

### 7.2 Patent Detail Drawer ("Ask about this patent")

**Trigger:** Button on every `frontend/src/app/(app)/patents/[id]/page.tsx`
- "Ask about this patent" button in the header or sidebar
- Opens `/chat?patent=US12345678B2` with the patent pre-loaded as context

**Drawer behavior:**
- Slides in from right on desktop (overlay on mobile)
- Renders the same `PatentPage` content in a compact layout
- The chat context is automatically seeded with:
  ```
  The user is asking about patent US12345678B2: "[TITLE]"
  Assignee: [ASSIGNEE]. Published: [DATE].
  Abstract: [FULL ABSTRACT]
  ```
- This patent is NOT sent as a retrieved result (it's explicit context).

### 7.3 Streaming Text Rendering

**Approach:** Markdown with custom citation link rendering.

- Parse SSE chunks into a growing text buffer
- Render with `react-markdown` (or a lightweight markdown-to-React serializer)
- Citation links `[Source: DOC_ID](url)` are parsed and rendered as styled
  badges/tags rather than plain links
- "Thinking..." indicator shows a pulsing dot while stream is active
- Abort button (×) stops the fetch and preserves current text

**No library dependencies needed** beyond what's already in `package.json`.
Custom `useChatStream` hook (~80 lines) handles fetch + ReadableStream +
state management.

---

## 8 — Proposed Implementation Sequence

### PR 1: SSE Streaming Scaffold (no retrieval, no tools)

**Depends on:** None  
**Effort:** 4-6 hours  
**Risk:** Low — standalone endpoint, no integration points

**Scope:**
- `POST /api/v1/chat/stream` endpoint (FastAPI `StreamingResponse` with
  `text/event-stream`)
- New `ChatClient` class wrapping `anthropic.Anthropic.messages.stream()`
- Echo mode: returns streamed "You asked: {query}. Chatbot coming soon."
- Frontend `useChatStream` hook with basic SSE parsing
- Basic `/chat` page with input + streaming text display

**Out of scope:** Retrieval, tools, memory, quotas, citations

**Key files:**
- `backend/app/ai/chat_client.py` (new — streaming Anthropic wrapper)
- `backend/app/api/v1/chat.py` (new — SSE endpoint)
- `frontend/src/app/(app)/chat/page.tsx` (new)
- `frontend/src/hooks/useChatStream.ts` (new)

---

### PR 2: Retrieval Layer + Cited Context

**Depends on:** PR 1  
**Effort:** 6-8 hours  
**Risk:** Medium — first time joining retrieval + LLM generation

**Scope:**
- `RetrievalService.retrieve(query, k=8)` using `PatentEmbedder` + pgvector
- System prompt template with `{retrieved_context}` placeholder
- Retrieved patents injected as numbered `[1]...[8]` entries
- LLM instructed to cite patents by number/doc_id
- Backend tests: verify retrieved patents appear in system prompt

**Out of scope:** News retrieval, tool calls, conversation memory

**Key files:**
- `backend/app/services/retrieval.py` (new)
- `backend/app/ai/prompts/chat_system_v1.md` (new)
- `backend/app/api/v1/chat.py` (modify — wire retrieval before LLM call)

---

### PR 3: Tool Calls (3 tools)

**Depends on:** PR 2  
**Effort:** 8-10 hours  
**Risk:** Medium-High — Anthropic tool loop is new territory for this codebase

**Scope:**
- Tool definitions (3 tools) registered with `messages.stream()`
- Tool execution loop in endpoint: LLM returns `tool_use` → execute →
  send `tool_result` → LLM continues → final text response
- `search_patents` implementation (reuse `PatentEmbedder` + pgvector)
- `open_patent` implementation (reuse `GET /patents/{id}` DB query)
- `compare_companies` implementation (new aggregate query)
- Tests: mock Anthropic tool use events, verify tool execution

**Out of scope:** Complex nested tool chaining (one level only for MVP)

**Key files:**
- `backend/app/api/v1/chat.py` (modify — tool loop)
- `backend/app/services/chat_tools.py` (new — tool implementations)
- `backend/app/ai/prompts/chat_system_v1.md` (modify — tool instructions)

---

### PR 4: Citation Enforcement

**Depends on:** PR 3  
**Effort:** 4-6 hours  
**Risk:** Low — post-processing layer, doesn't change generation path

**Scope:**
- Post-generation regex check for `[Source: ...](...)` citations
- Retry logic: if no citations found, re-prompt with stronger instructions
  (max 2 attempts)
- Fallback: on second failure, return response with warning metadata
- Warning UI: "⚠ Some claims in this response may not cite sources"
- Tests: responses with/without citations, retry exhaustion

**Out of scope:** Structured JSON output enforcement, pre-generation tool
choice enforcement

**Key files:**
- `backend/app/services/citation_checker.py` (new)
- `backend/app/api/v1/chat.py` (modify — post-generation check)
- `frontend/src/components/chat/CitationWarning.tsx` (new)

---

### PR 5: Conversation Memory (Redis)

**Depends on:** PR 3 (can run parallel to PR 4)  
**Effort:** 4-5 hours  
**Risk:** Low — Redis is already a dependency, pattern is straightforward

**Scope:**
- Redis LIST-based chat history storage
- 30-min TTL with reset on each message
- 10-turn cap enforcement (LTRIM after each append)
- History injection into system prompt (replaces static context)
- `/chat/new` endpoint to clear history
- Graceful degradation when Redis is unavailable

**Out of scope:** Multi-device sync, user-visible history browsing

**Key files:**
- `backend/app/services/chat_memory.py` (new)
- `backend/app/api/v1/chat.py` (modify — read/write history)

---

### PR 6: Quota Enforcement

**Depends on:** PR 5 (or can merge earlier)  
**Effort:** 3-4 hours  
**Risk:** Low — follows existing `quotas/limits.py` pattern

**Scope:**
- `check_chat_quota(user_id, tier)` function
- Redis counter with daily TTL
- 402 response with quota details + upgrade link
- Frontend quota indicator in `/chat` UI ("3 of 5 queries remaining today")
- Quota bypass for Lifetime/Enterprise

**Out of scope:** Usage dashboard, billing page quota display

**Key files:**
- `backend/app/quotas/limits.py` (modify — add `check_chat_quota`)
- `backend/app/api/v1/chat.py` (modify — quota check before LLM call)
- `frontend/src/components/chat/QuotaIndicator.tsx` (new)

---

### PR 7: Frontend /chat Page + Patent Drawer

**Depends on:** PR 4, PR 5, PR 6  
**Effort:** 8-12 hours  
**Risk:** Medium — most UI work, integration testing needed

**Scope:**
- Full `/chat` page with conversation panel + input
- Markdown rendering with citation badges
- Streaming text display with typing indicator
- Patent detail drawer (slide-out, reuse `PatentPage` data)
- "Ask about this patent" button on patent detail pages
- `/chat?patent=DOC_ID` pre-seeded context
- Mobile-responsive layout
- Tour integration: add `/chat` to tour step (or defer)

**Out of scope:** Chat history browser, conversation export, multi-turn
editing, suggested follow-up questions

**Key files:**
- `frontend/src/app/(app)/chat/page.tsx` (finish)
- `frontend/src/components/chat/ChatPanel.tsx` (new)
- `frontend/src/components/chat/ChatMessage.tsx` (new)
- `frontend/src/components/chat/PatentDrawer.tsx` (new)
- `frontend/src/app/(app)/patents/[id]/page.tsx` (modify — add Ask button)

---

### PR Sequencing Summary

```
PR 1 (SSE scaffold)
  └── PR 2 (Retrieval)
        └── PR 3 (Tools)
              ├── PR 4 (Citations)
              └── PR 5 (Memory) ──┐
                                  ├── PR 7 (Frontend)
              PR 6 (Quotas) ──────┘
```

PRs 4, 5, 6 can run partially in parallel (different files, low conflict
risk). Total: 7 PRs, estimated 37-51 hours of implementation work.

---

## 9 — Open Questions for Andy

1. **Default LLM for chatbot?** The audit recommends Anthropic
   (Claude Sonnet 4) for its superior tool calling and streaming quality,
   even though DeepSeek is the current default for batch AI runs.
   Anthropic would cost ~$0.12/query vs DeepSeek ~$0.002/query.
   At Free-tier 5/day × 100 users = 500 queries/day, that's ~$60/day
   Anthropic vs ~$1/day DeepSeek. Is the quality differential worth the
   cost at this stage?

2. **DeepSeek as fallback?** Could offer Free users DeepSeek-chatbot
   (cheaper, weaker tool use) and Basic+ users Anthropic-chatbot (better
   quality). Adds provider-routing complexity but saves money on free
   tier. Worth it?

3. **Citation enforcement strictness?** Strategy B (soft enforcement with
   retry, fallback to warning) vs Strategy A (hard rejection if no
   citations). Soft is better UX but weaker guardrail. How strict?

4. **News items retrieval?** The `news_items.embedding` column exists but
   has no index and no evidence of populated embeddings. Should the
   chatbot MVP include news retrieval (requires: index creation,
   embedding backfill, integration into retrieval layer) or defer to a
   Phase 3.5 PR?

5. **Onboarding integration?** Should `/chat` appear in the onboarding
   tour (Phase 2 PR 2)? It's a major differentiator — arguably more
   important to surface than some current tour steps. Add as tour step 6
   or replace an existing step?

6. **Cost estimate per query?** For cost tracking, should the chatbot
   endpoint write `AIArtifact` rows (like current `LLMClient.complete()`
   does) or use a separate lightweight cost log? The `AIArtifact` table
   is content-addressed and caches duplicate inputs — chat queries are
   almost never duplicates, so it would just bloat the table.

7. **Conversation memory TTL: 30 minutes OK?** Most users won't chat for
   more than 30 minutes in one session. If they step away and come back,
   starting fresh is arguably better UX than stale context. Confirm.

8. **k=8 retrieval limit?** The roadmap specifies K=8. For a 200K context
   window, this is conservative. Could go to K=16 without exceeding token
   budget. The tradeoff: more patents = better recall but slower
   retrieval and more tokens consumed. Keep K=8 or raise?

---

## Appendix A — Files That Will NOT Change

These are the existing files that the chatbot should NOT modify (to avoid
regressions in the stable AI pipeline):

- `backend/app/ai/llm_client.py` — keep for batch AI runs; chatbot uses separate `ChatClient`
- `backend/app/ai/embedder.py` — reuse `PatentEmbedder` as-is
- `backend/app/core/models.py` — no schema changes for MVP
- `backend/app/core/ai_models.py` — no new columns needed
- `backend/app/api/v1/search.py` — untouched
- `backend/app/api/v1/semantic_search.py` — reuse, don't modify
- `frontend/src/app/(marketing)/page.tsx` — untouched
- `frontend/src/styles/tokens.css` — reuse existing design tokens

## Appendix B — New Dependencies

**Backend (zero new packages):**
- `anthropic` v0.40+ already installed (streaming + tools supported)
- `redis` / `redis-py` already installed (Celery, thumbnail cache)
- `httpx` already installed (DeepSeek calls)
- No new packages needed

**Frontend (zero new packages):**
- `react-markdown` already in `package.json` (used for AI content display)
- SSE via native `fetch` + `ReadableStream` — no library needed
- No new packages needed
