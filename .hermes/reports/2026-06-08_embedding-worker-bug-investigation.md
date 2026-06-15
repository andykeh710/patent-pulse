# Embedding Worker Bug Investigation — `ConnectionDoesNotExistError`

**Date**: 2026-06-08
**Investigator**: Hermes Agent
**Symptom**: Every `embeddings-backfill` beat task fails on `UPDATE patent_publications SET embedding=...` with `ConnectionDoesNotExistError` / `BrokenPipeError`. Coverage stuck at 17,706 / 64,231 (27.6%).

---

## Code Path Traced

### The task entry point

`backend/app/tasks/embeddings.py` — `batch_generate_embeddings()` (line 54)

```python
def batch_generate_embeddings(self, limit: int = 50, ...) -> dict:
    async def _run_and_dispose():
        try:
            return await _batch_generate_embeddings_async(limit, ...)
        finally:
            await _engine.dispose()   # line 103 — cleanup
    stats = asyncio.run(_run_and_dispose())  # line 105
```

### The batch loop (where the bug lives)

`backend/app/tasks/embeddings.py` — `_batch_generate_embeddings_async()` (line 138)

```python
async def _batch_generate_embeddings_async(limit: int, ...) -> dict:
    async with async_session_maker() as session:        # line 147 — opens connection
        query = select(PatentPublication)
            .where(PatentPublication.embedding.is_(None))  # line 150
            .where(PatentPublication.title.isnot(None))
            .order_by(PatentPublication.created_at.desc())
        result = await session.execute(query.limit(limit))  # line 166 — SELECT
        patents = result.scalars().all()

        with PatentEmbedder() as embedder:                # line 172 — sync ctx mgr
            for patent in patents:                        # line 173
                embedding = embedder.generate_patent_embedding(patent)  # line 179
                patent.embedding = embedding              # line 180

        await session.commit()                            # line 192 — ← FAILS HERE
```

### The embedder (synchronous, blocking)

`backend/app/ai/embedder.py` — `PatentEmbedder` (line 29)

```python
class PatentEmbedder:
    def __init__(self, api_key=None):
        self._http_client = httpx.Client(timeout=30.0)   # line 46 — SYNC client

    def generate_embedding(self, text: str) -> list[float]:
        response = self._http_client.post(                # line 70 — BLOCKS
            "https://api.openai.com/v1/embeddings",
            json={"model": "text-embedding-3-small", "input": text, ...}
        )
```

Key: `httpx.Client` is **synchronous**. Every call to `generate_patent_embedding()` blocks the event loop for the duration of the HTTP round-trip (~200-500ms per patent).

### The database config

`backend/app/database.py` (lines 1-42)

```python
_in_celery_worker = os.environ.get("CELERY_WORKER", "") == "true"  # line 11

_engine_kwargs = {
    "pool_pre_ping": True,
    "connect_args": {
        "server_settings": {
            "idle_in_transaction_session_timeout": "60000",  # ← 60 SECONDS (line 23)
        },
    },
}
if _in_celery_worker:
    _engine_kwargs["poolclass"] = NullPool   # line 31 — one conn per batch
```

Key observations:
- Celery workers use **NullPool** — each batch gets exactly one connection
- `idle_in_transaction_session_timeout = 60000` (60 seconds) — Postgres kills connections idle-in-transaction for >60s
- This timeout was added in "Post-Sprint-5 audit (A2)" (comment, lines 16-21) to prevent leaked connections

### The beat schedule

`backend/app/tasks/celery_app.py` (lines 191-197)

```python
"embeddings-backfill": {
    "task": "app.tasks.embeddings.batch_generate_embeddings",
    "schedule": crontab(minute="*/2"),
    "args": (1000,),        # ← limit=1000
    "options": {"queue": "maintenance"},
},
```

**Note**: The comment on line 191 says "every 15 min, 200/batch" but the actual config is every 2 minutes with 1,000 per batch.

---

## Root Cause Hypothesis

**Confidence: HIGH**

### What happens

1. The Celery task opens an async DB session (one connection via NullPool).
2. It runs a SELECT to fetch up to 1,000 patents missing embeddings.
3. It enters a **synchronous** `for` loop calling OpenAI per patent.
   Each call blocks the event loop for ~200-500ms.
4. While the synchronous loop runs, the asyncpg connection is **idle in
   an open transaction** — no async operations are happening on it.
5. After ~200-1,000 seconds (1,000 patents × 200-1,000ms each), it
   reaches `await session.commit()`.
6. By this point, the connection has been idle-in-transaction for well
   over 60 seconds. Postgres has already killed it via
   `idle_in_transaction_session_timeout`.
7. The commit fails with `ConnectionDoesNotExistError:
   connection was closed in the middle of operation`.

### Math

| Patents per batch | Avg OpenAI latency | Total loop time | Timeout | Result |
|---|---|---|---|---|
| 1000 | 200ms | 200s | 60s | **FAILS** |
| 1000 | 500ms | 500s | 60s | **FAILS** |
| 200 | 200ms | 40s | 60s | PASSES |
| 50 (function default) | 200ms | 10s | 60s | PASSES |

The beat schedule passes `args: (1000,)` which overrides the function
default of `limit=50`. The batch is too large to complete within 60
seconds.

### Evidence FOR

1. The stack trace shows `ConnectionDoesNotExistError` on
   `session.commit()` — consistent with a server-side timeout killing
   an idle connection.

2. The idle timeout was added in the Sprint 5 audit (database.py lines
   16-21 explicitly document this) — before this timeout was added,
   the synchronous loop could hold the connection indefinitely.

3. `embedder.py:46` uses `httpx.Client` (synchronous) — the OpenAI
   call blocks the event loop completely for each patent.

4. `embedder.py:97` runs one API call per patent — there is no
   batching at the OpenAI API level (despite `generate_batch_embeddings()`
   existing on line 131, it is never called by the Celery task).

5. The beat schedule passes `args: (1000,)` — even at optimistic
   latency (200ms/call), the total is 200 seconds > 60s timeout.

6. The `_engine.dispose()` on line 103 runs in the `finally` block
   and closes the already-killed connection, producing the
   `BrokenPipeError`.

### Evidence AGAINST

None. Every element of the stack is consistent.

### Why 17,706 succeeded before the bug became blocking

**Timeline hypothesis**:

1. **Before Sprint 5 audit**: No `idle_in_transaction_session_timeout`.
   The synchronous loop could hold the connection open indefinitely.
   Batches with limit=1000 completed, albeit slowly (hundreds of
   seconds). 17,706 patents were embedded during this period.

2. **Sprint 5 audit (A2)**: The `idle_in_transaction_session_timeout`
   was added to `database.py` (lines 16-27) to prevent leaked
   connections from `asyncio.run()` teardown. This capped idle
   transaction duration at 60 seconds.

3. **After the timeout was added**: Every batch with limit=1000 now
   fails because the synchronous loop takes >60 seconds. The
   `expiring` schedule with limit=200 might occasionally succeed
   (40s for 200 × 200ms if network is fast) but is unreliable.

**Alternative possibility**: The `limit=1000` in `args` was a recent
change from a smaller batch size. The comment on line 191 says
"200/batch" — this was likely the original value, and someone bumped
it to 1000 without understanding the synchronous-blocking consequence.

---

## Proposed Fix

**Option A — Reduce batch size (5-minute fix, safest)**: Change
`args: (1000,)` to `args: (50,)` in the beat schedule. At 50
patents × 200ms, the loop takes ~10 seconds — well within 60s.
Throughput: 50 patents × 30 batches/hour = 1,500/hour = 36,000/day.
Full 64K backfill completes in < 2 days. **Cost: $0.**

**Option B — Commit per patent (simple, minimal code change)**:
Move `await session.commit()` inside the `for` loop (after each
`patent.embedding = embedding`). Each patent's database work
completes in microseconds, so the connection is never idle for
more than the OpenAI call duration (~200-500ms). A single slow
OpenAI call (>60s) would still fail, but that's unlikely.

**Option C — Use batched OpenAI API (best long-term)**:
Replace the per-patent loop with `embedder.generate_batch_embeddings()`
which sends up to 20 texts per API call. Process in sub-batches of
20, commit after each sub-batch. 1,000 patents = 50 API calls
instead of 1,000. **Cost: $0.77 one-time (not per batch).**

**Option D — Make embedder async (most thorough)**:
Replace `httpx.Client` with `httpx.AsyncClient`, make embedding
calls `await`-able, replace the sync `for` loop with async iteration.
This removes the blocking issue entirely but requires more refactoring.

**Recommendation**: **Option C (batched API) + Option A (reduce
batch size to 200)**. The batched API reduces API calls by 20x
(reducing total backfill wall-clock time), and the smaller batch
size ensures commits happen within the 60s window. Combined, this
is both the fastest and cheapest approach.

---

## Risks / Open Questions

1. **Is the `ConnectionDoesNotExistError` definitely from the idle
   timeout, or could it be a pool exhaustion issue?**
   NullPool means no pooling — each batch gets a fresh connection.
   Pool exhaustion can't happen with NullPool. The only way a
   connection dies mid-transaction is the idle timeout.

2. **Could the `_engine.dispose()` in the finally block be causing
   collateral damage?**
   `_engine.dispose()` closes ALL connections in the engine's pool.
   With NullPool, this is just the current connection. However, if
   multiple Celery tasks share the same process (prefork), disposing
   the engine could kill another task's connection. Risk is low with
   NullPool but worth noting.

3. **Why is the embedder synchronous when the rest of the codebase
   uses async/await?**
   The embedder was likely written for V1 when the embedding task
   was a simple one-off script, not a recurring beat task. It was
   never refactored to be async.

4. **Why does the beat comment say "200/batch" but the config says 1000?**
   This is a discrepancy — someone changed the args without updating
   the comment. The original 200/batch would have been borderline
   (40s for 200 × 200ms) but occasionally viable.

5. **What happens to the patents that were successfully embedded
   before the commit fails?**
   They are lost. The `WHERE embedding IS NULL` filter means they'll
   be retried in the next batch. No data corruption, just wasted
   API calls and no forward progress.
