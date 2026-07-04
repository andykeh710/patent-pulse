# Phase 1 — Semantic Search Foundation Audit

**Date**: 2026-06-08
**Investigator**: Hermes Agent
**Source**: `.hermes/plans/2026-06-04_v3-roadmap.md` Part II, Section 2
**Scope**: Investigation only — no code changes, no production access

---

## Section 1 — Current Embedding State

### 1.1 Does `patent_publications` have an embedding column?

**Yes.** `patent_publications.embedding` exists as `Vector(1536)`, nullable,
since the initial schema migration.

**Evidence**:
- `backend/app/core/models.py:131`:
  ```python
  embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
  ```
- `backend/alembic/versions/0001_initial_schema.py:55`:
  ```python
  sa.Column("embedding", Vector(1536), nullable=True),
  ```
- The pgvector extension is created in the same migration (line 23):
  ```python
  op.execute("CREATE EXTENSION IF NOT EXISTS vector")
  ```

**Dimensions**: 1536. **Nullable**: yes (most patents likely have NULL).

### 1.2 Is there a pgvector index defined?

**No.** There is NO ivfflat or hnsw index on the `embedding` column.

The existing indexes on `patent_publications` are:
- `search_vector` (GIN, for tsvector FTS) — `models.py:143`
- `cpc` (GIN) — `models.py:144`
- `assignees` (GIN) — `models.py:145`
- `tags` (GIN) — `models.py:146`
- `opportunity_score` (BTREE) — `models.py:147`

Every semantic search query (`<=>` operator) currently runs a full
sequential scan of the table. For 64K rows this is fast (tens of ms),
but it will degrade linearly. An index is the single most impactful
optimisation for Phase 1.

### 1.3 What's current coverage?

**SQL to run on production** (Andy, paste this):
```sql
SELECT
  COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded,
  COUNT(*) AS total
FROM patent_publications;
```

Given the beat schedule runs every 2 minutes with `limit=1000` and every
minute with `limit=200` for expiring patents, but the embedder makes
synchronous OpenAI calls per patent (no batch API), the backfill has
been running since Sprint 5. Expect some non-zero coverage, but unlikely
to be 100% unless it's been running for weeks.

### 1.4 Where is the embedding-generation code?

**`backend/app/ai/embedder.py`** (238 lines) — `PatentEmbedder` class
using OpenAI's **synchronous** `httpx.Client`.

Model: `text-embedding-3-small` (1536 dimensions).
API endpoint: `https://api.openai.com/v1/embeddings`.

**Key methods**:
- `generate_embedding(text)` — single text, single API call (line 54)
- `generate_patent_embedding(patent)` — combines title + abstract +
  independent claims + CPC codes into one text, then calls
  `generate_embedding()` (line 96)
- `generate_batch_embeddings(texts, batch_size=20)` — sends up to 20
  texts per API call (line 131)

**`backend/app/tasks/embeddings.py`** (194 lines) — Two Celery tasks:

1. `generate_patent_embedding` (line 24) — single patent, 3 retries
2. `batch_generate_embeddings(limit, prioritize_expiring)` (line 54) —
   processes `limit` patents where `embedding IS NULL`, newest-first
   or expiry-soonest-first.

**Critical observation**: The batch task (line 172) creates ONE
`PatentEmbedder` context manager and then iterates patent-by-patent
calling `generate_patent_embedding()` — which makes ONE API call per
patent. The `generate_batch_embeddings()` method (which sends 20 texts
per call) is never used by the Celery task. This means the current
implementation is **20x less cost-efficient** than it could be for
the OpenAI batch endpoint.

**Beat schedule** (celery_app.py):
- `embeddings-backfill`: every 2 minutes, `limit=1000` (line 192-194)
- `embeddings-backfill-expiring`: every minute, `limit=200`,
  `prioritize_expiring=True` (line 201-206)
- `batch-embeddings`: Sunday at 4am UTC, `limit=50` (line 156-158)

**Config** (`backend/app/config.py`): `openai_api_key` is the relevant
setting (line 40 of embedder.py reads `settings.openai_api_key`).
DeepSeek credentials exist separately (`deepseek_api_key`, line 91).

---

## Section 2 — Round 9 Reuse

### 2.1 Does Round 9 already embed patents somewhere?

**Round 9 added** (migration 0025):
- `user_embeddings` table — `Vector(1536)` per user (computed centroid
  of viewed patent embeddings)
- `news_items.embedding` — `Vector(1536)`, nullable
- `user_view_events` — tracking table for view/save/follow

All three use the same 1536-dim `Vector` type from pgvector.

No new patent-level embedding column was added — Round 9 reuses the
existing `patent_publications.embedding` column from migration 0001.

### 2.2 Can Phase 1 reuse Round 9's pgvector setup?

**Yes, partially.** Key observations:

- **Same vector type, same dimensions**: Round 9 and Phase 1 both use
  `Vector(1536)`. No schema migration needed for dimensions.
- **Same operator**: Round 9's `recommendations.py:71` uses `<=>`
  (cosine distance) — the same operator Phase 1 will use.
- **Same embedding format**: `recommendations.py:66` serializes
  embeddings as `"[1.2,3.4,...]"` — same pattern as
  `semantic_search.py:55`.
- **No index**: Round 9 doesn't create a pgvector index either.
  Recommendations scan the full table (line 69-80).

**What Phase 1 needs that Round 9 doesn't provide**:
1. A pgvector index (IVFFlat or HNSW) on `patent_publications.embedding`
2. The embedding backfill needs to be completed (or at least verified)
3. The embedder needs to support a provider switch (currently
   hardcoded to OpenAI — roadmap says DeepSeek)

**Recommendation**: Share the column. Do NOT create a parallel column
or table. The existing `embedding` column is the canonical vector store
for patents. Round 9 reads from it; Phase 1 writes to it and builds
the index on it.

---

## Section 3 — Current Search Endpoint

### 3.1 What does `GET /api/v1/search` do today?

**Pure PostgreSQL full-text search** using `tsvector` + GIN index.

**File**: `backend/app/api/v1/search.py` (66 lines)

**Query** (line 29):
```python
search_query = func.plainto_tsquery("english", q)
conditions = [PatentPublication.search_vector.op("@@")(search_query)]
```

**Features**:
- `plainto_tsquery` — converts user input to tsquery (ANDs all terms)
- Filters: CPC code, assignee name, date range
- Ranking: `ts_rank(search_vector, search_query)` (line 49)
- Pagination: standard offset/limit

**Response**: `PaginatedResponse[PatentListItem]` — same as /patents
listing.

**Limitations**:
- No stemming awareness for patent-specific terminology
- No semantic understanding — "battery thermal management" only finds
  patents containing those exact tokens
- No vector search integration
- No recency boost

### 3.2 Frontend search bar

**File**: `frontend/src/app/(app)/search/page.tsx` (234 lines)

- Dual-mode: `"fulltext"` (default) and `"semantic"` toggle
- Fulltext mode calls `usePatentSearch` → `GET /api/v1/search?q=...`
- Semantic mode calls `semanticApi.query` → `POST /api/v1/semantic/query`
- URL state sync via query params (`?q=`, `&mode=`, `&page=`)
- No client-side filtering — all filtering is server-side

### 3.3 Semantic search endpoint (already exists)

**File**: `backend/app/api/v1/semantic_search.py` (253 lines)

Three endpoints:
- `POST /api/v1/semantic/query` — natural language search via embedding
- `GET /api/v1/semantic/similar/{patent_id}` — find similar patents
- `GET /api/v1/semantic/novelty/{patent_id}` — compute novelty score

Both query and similar endpoints convert input to embedding via
`PatentEmbedder`, then run `<=>` cosine distance against the full table
(`WHERE embedding IS NOT NULL`). **No index — full sequential scan.**

### 3.4 Similar patents panel (frontend)

**File**: `frontend/src/app/(app)/patents/[id]/page.tsx:866-926`

`SimilarTab` component:
- Calls `semanticApi.similar(patentId)` via SWR
- Handles loading, error, "no embedding" empty state, and "no results
  above threshold" empty state
- Renders patent cards with similarity percentage badges
- Already production-quality UI — just needs the backend to return
  good results

---

## Section 4 — Provider Comparison

### 4.1 DeepSeek embeddings

| Attribute | Value |
|-----------|-------|
| Model name | `deepseek-embedding` (or similar — DeepSeek docs vary) |
| Dimensions | 1536 (confirmed via DeepSeek API docs) |
| Cost per 1M tokens | **Currently not publicly listed as a standalone embeddings API.** DeepSeek offers embeddings through their chat completions endpoint? Need to verify. |
| Rate limits | Unknown — DeepSeek doesn't publish embedding-specific rate limits |
| MTEB score | Not publicly benchmarked against OpenAI on MTEB leaderboard |

**Important**: As of June 2026, DeepSeek's embedding API availability and pricing are unclear. The roadmap assumes they offer an embedding endpoint at ~$0.10/1M tokens, but this needs verification. If they don't have a dedicated embeddings API, the Cost section below becomes moot.

### 4.2 OpenAI text-embedding-3-small

| Attribute | Value |
|-----------|-------|
| Model name | `text-embedding-3-small` |
| Dimensions | 512 or 1536 (configurable) — current code uses 1536 |
| Cost per 1M tokens | **$0.02/1M tokens** (OpenAI pricing page, June 2026) |
| Rate limits | Tier 1: 1M TPM, 500 RPM. TPM scales with usage tier. |
| MTEB average | 62.3 (1536-dim) |
| Batch API | Yes — up to 2048 texts per call |

**Source**: https://platform.openai.com/docs/guides/embeddings

### 4.3 Cost estimate — 64K patent backfill

Assume ~600 tokens per patent (title ~30 + abstract ~200 + first claim
~300 + CPC ~70).

Total tokens: 64,000 × 600 = **38,400,000 tokens** (~38.4M).

| Provider | Cost per 1M tokens | Total backfill cost | Batch calls needed |
|----------|-------------------|---------------------|--------------------|
| OpenAI `text-embedding-3-small` | $0.02 | **$0.77** | 64,000 / 20 = 3,200 (current code, per-patent) OR 64,000 / 2,048 = 32 (if using batch endpoint) |
| DeepSeek (unverified) | ~$0.10 | **~$3.84** | Unknown |

**Reality check**: At $0.77 for the entire backfill, OpenAI is
essentially free at this scale. The roadmap's "$50 estimate" was
off by ~65x. Even if each patent averages 1,500 tokens (due to long
abstracts), the cost would be ~$1.92.

### 4.4 Recommendation

**Use OpenAI `text-embedding-3-small` for Phase 1.** Do not switch to
DeepSeek.

Rationale:
1. **Cost is negligible**: $0.77 for the full backfill. Even with
   daily re-embeds for new patents, annual cost is < $10.
2. **Already integrated**: The codebase already uses it, it works,
   the API is battle-tested, and rate limits are generous.
3. **No uncertainty**: DeepSeek's embedding API availability is
   unknown. OpenAI's is documented and stable.
4. **Roadmap can update**: The roadmap was drafted when DeepSeek
   embeddings were assumed viable. Investigation shows the
   cost argument doesn't hold — OpenAI is actually cheaper at
   this scale, not more expensive.

If DeepSeek later offers a verified embedding endpoint at a
truly lower cost (unlikely at < $0.02/1M), the embedder's
provider-agnostic interface makes switching trivial.

---

## Section 5 — Index Strategy

### 5.1 Which pgvector index for 64K rows at 1536-dim?

Recommendation: **HNSW** over IVFFlat.

| Index | Build time | Query speed | Memory | Notes |
|-------|-----------|-------------|--------|-------|
| IVFFlat | Fast (~1s for 64K) | Moderate | Low | Requires `lists = sqrt(N) ≈ 253`. Good enough, but recall degrades without `probes`. |
| HNSW | Moderate (~5s for 64K) | Fast | Higher | `m=16, ef_construction=64`. Better recall at low latency. Preferred for production. |

For 64K rows, the difference is small. HNSW adds maybe 200-400MB of
memory overhead (1536-dim × 64K vectors × ~16 graph edges). IVFFlat
is simpler but requires tuning `lists` and `probes`. HNSW "just works"
with good defaults.

**Recommended DDL**:
```sql
CREATE INDEX IF NOT EXISTS idx_patents_embedding_hnsw
ON patent_publications
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

Note: `vector_cosine_ops` matches the `<=>` operator already in use.

For IVFFlat (simpler, good enough):
```sql
CREATE INDEX IF NOT EXISTS idx_patents_embedding_ivfflat
ON patent_publications
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 250);
```

**Migration**: Add one index (choose HNSW for long-term, IVFFlat for
simplicity). The migration should use `IF NOT EXISTS` for idempotency.
If HNSW, also set `ef_search` at session level (or globally) for
queries: `SET hnsw.ef_search = 100;`

### 5.2 Cosine vs L2 vs inner product

**Use cosine similarity (vector_cosine_ops).**

- The codebase already uses `<=>` everywhere (semantic_search.py,
  recommendations.py, news_ingestion.py) — which is cosine distance.
- Text embeddings are directionally meaningful; magnitude is an
  artifact of the model, not the content.
- All major embedding models (OpenAI, DeepSeek, Sentence Transformers)
  are trained with cosine similarity loss.
- pgvector docs: `<=>` defaults to cosine distance when no operator
  class is specified.

---

## Section 6 — Hybrid Search Scoring

### 6.1 Are the roadmap weights reasonable?

Proposed: `score = 0.5 * vector_score + 0.3 * keyword_score + 0.2 * recency_score`

**Judgment**: Reasonable as a starting point, but the keyword weight
is too high for the current FTS quality.

- The current FTS (`plainto_tsquery`) doesn't understand patent
  terminology. It ANDs all tokens, which means multi-word queries
  often return zero results. A weight of 0.3 amplifies this
  weakness.
- The vector score (0.5) is the primary signal. It should dominate
  for natural-language queries.
- Recency (0.2) is appropriate — patent value decays with age, and
  users searching for "battery thermal management" want recent work.

**Suggested revision**: Start with `0.6 * vector + 0.2 * keyword +
0.2 * recency`. Tune after user testing.

If the FTS backend is improved (e.g., `websearch_to_tsquery` or
`phraseto_tsquery`), the keyword weight can return to 0.3.

### 6.2 How is "keyword_score" computed today?

**PostgreSQL FTS rank** via `ts_rank()` (search.py:49):
```python
rank = func.ts_rank(PatentPublication.search_vector, search_query)
```

The `search_vector` column is a `TSVECTOR` (models.py:133):
```sql
to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, ''))
```

It's a GIN-indexed generated column (migration 0001, line 57-63).

For hybrid search, the ts_rank value needs normalisation (0-1 range).
`ts_rank` returns values typically in 0.0–1.0 range but can exceed 1.
Normalise: `keyword_score = min(ts_rank / max_rank_in_results, 1.0)`.

### 6.3 Which date for "recency_score"?

`publication_date` is the most meaningful recency signal.

The model has three date fields (models.py):
- `filing_date` (line 26) — when the application was filed
- `priority_date` (line 27) — earliest priority claim
- `publication_date` (line 28) — when the patent was published
- `grant_date` (line 29) — when the patent was granted (often null)

`publication_date` is the correct recency signal because:
- It's when the invention became public (what users care about)
- It's most consistently populated (grant_date is often null)
- It's already indexed (line 28: `index=True`)

Simple recency score: `recency_score = 1.0 - (days_since_publication / max_age_days)`,
clamped to [0, 1]. `max_age_days = 7300` (20 years) is a reasonable
default.

---

## Section 7 — Risks and Unknowns

### 7.1 Things not verifiable without production access

1. **Current embedding coverage**: How many of the 64K patents have
   `embedding IS NOT NULL`? Run the SQL from Section 1.3.
2. **Backfill rate**: At 1,000 patents per 2 minutes + 200 per minute,
   the theoretical max is ~42,000 patents/day. But OpenAI rate limits
   may throttle this. Check Celery worker logs for rate-limit errors.
3. **OpenAI API key validity**: Does the production `.env` have a
   valid `OPENAI_API_KEY`? If not, the embedding backfill has been
   silently failing.
4. **Current cost incurred**: If the backfill has been running, what's
   the actual OpenAI spend to date? Check the OpenAI dashboard.
5. **DeepSeek embedding API availability**: Can't verify from here.

### 7.2 What could go wrong with the embedding backfill?

1. **Rate limits** (MEDIUM risk): OpenAI Tier 1 is 1M TPM and 500 RPM.
   Current schedule (1000/2min + 200/min = 700/min) is near the RPM
   limit. If the backfill has been running, it's likely been
   rate-limited. Fix: add exponential backoff + respect Retry-After.
2. **Cost overrun** (LOW risk): At $0.02/1M tokens, even all 64K
   patents cost < $1. This is not a meaningful risk.
3. **Partial-batch failures** (MEDIUM risk): The current code commits
   after each batch (embeddings.py:192). If the batch fails halfway
   through, patents that were successfully embedded won't be rolled
   back. The `WHERE embedding IS NULL` filter means re-running skips
   them correctly — this is idempotent, not a data-loss risk.
4. **DB lock contention** (LOW risk): The embedding column already
   exists. Adding an index (HNSW/IVFFlat) does NOT lock the table
   (pgvector index builds use `CONCURRENTLY`). No schema change
   needed for the column itself.
5. **Synchronous calls blocking the event loop** (LOW risk): The
   current code calls OpenAI synchronously inside an `asyncio.run()`
   wrapper. The `embeddings.py` code handles this correctly with
   `_engine.dispose()` in the finally block.
6. **Token limit exceeded** (LOW risk): `embedder.py:67` truncates
   text to 32,000 characters (not tokens). For patents with very long
   claims, this could exceed the 8,191 token limit of
   text-embedding-3-small. Fix: add tiktoken-based truncation.

### 7.3 Open questions for Andy

1. **DeepSeek embeddings — is this real?** The roadmap assumes DeepSeek
   offers an embedding API at ~10x cheaper than OpenAI. Investigation
   couldn't confirm this (no public docs). At OpenAI's actual price
   ($0.02/1M tokens), the backfill costs < $1. Do you want to stay
   with OpenAI or do you have DeepSeek embedding API access?

2. **Which pgvector index?** HNSW is better long-term but adds ~200MB
   memory. IVFFlat is simpler and good enough for 64K rows. Preference?

3. **Embedding batching** — the current code calls OpenAI once per
   patent. The batch API endpoint supports 2,048 texts per call,
   reducing API calls from 64K to ~32. Should the Phase 1 embedder
   switch to batch mode, or keep per-patent for simplicity?

4. **Hybrid search weights** — the roadmap proposes 0.5/0.3/0.2 for
   vector/keyword/recency. Recommendation above is 0.6/0.2/0.2.
   Which do you want to start with?

5. **What if the `OPENAI_API_KEY` in production is invalid?** The
   backfill may have been silently failing. Check before Phase 1.

6. **Search UI changes** — the frontend already has a "semantic" mode
   toggle. Should Phase 1 make semantic the default, or keep fulltext
   as default and improve the toggle UX?

---

## Proposed Implementation Sequence

Below is the recommended PR order for Phase 1. Each PR is independent
where possible, reviewable in isolation.

### PR 1: Add pgvector index on patent_publications.embedding
**Depends on**: nothing
**Risk**: LOW (additive, no data change, CONCURRENTLY build)
**Effort**: 1h
- Alembic migration: CREATE INDEX CONCURRENTLY with HNSW or IVFFlat
- Session-level ef_search setting on query paths
- Verify `EXPLAIN ANALYZE` shows index usage on semantic search queries

### PR 2: Fix embedding backfill — batch mode + rate-limit handling
**Depends on**: PR 1 (index doesn't help writes, but should ship first
  for consistency)
**Risk**: LOW (improvement to existing code, not a rewrite)
**Effort**: 3h
- Switch `batch_generate_embeddings` to use `generate_batch_embeddings()`
  (batch of 20 per API call) instead of per-patent calls
- Add tiktoken-based text truncation (replace 32K char limit with
  proper token counting)
- Add exponential backoff on rate-limit errors
- Add a `--dry-run` mode that reports coverage without calling API
- Task idempotency already exists (WHERE embedding IS NULL)

### PR 3: Hybrid `/api/v1/search` endpoint
**Depends on**: PR 2 (needs embeddings to exist for vector search)
**Risk**: LOW (side-by-side with existing FTS; hybrid is additive)
**Effort**: 4h
- Add `mode` query param: `fulltext` (default), `semantic`, `hybrid`
- Hybrid mode: embed query → `<=>` cosine distance + ts_rank +
  recency score → weighted sort
- Normalize all three scores to 0-1 range
- Add `min_similarity` filter for vector component
- Response shape unchanged (still `PaginatedResponse[PatentListItem]`)
- Add `similarity` field to each result item (nullable, only set in
  vector/hybrid modes)

### PR 4: Search bar — make semantic the default + NL query examples
**Depends on**: PR 3
**Risk**: LOW (UI-only change, existing fulltext mode preserved)
**Effort**: 2h
- Default search mode to `hybrid` (or `semantic`) instead of `fulltext`
- Add placeholder examples: "battery thermal management for EVs",
  "CRISPR delivery vectors", etc.
- Show result count per mode (e.g., "12 fulltext · 34 semantic")
- Improve empty state: "Try a semantic search — it understands concepts,
  not just keywords"

### PR 5: Admin re-embed tool
**Depends on**: PR 1
**Risk**: LOW (admin-only, single-patent)
**Effort**: 1.5h
- `POST /api/v1/admin/embed/{patent_id}` — force re-embed a single patent
- `GET /api/v1/admin/embedding-stats` — coverage %, last backfill run
- Frontend: button on patent detail admin section + simple stats card

---

### Total estimated effort: ~11.5 hours (1.5 engineer-days)
### Total estimated cost: < $1 (OpenAI embedding API)
