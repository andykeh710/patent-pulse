# V3.8E Summarization Batch Event-Loop Fix

**Date:** 2026-06-21
**Branch:** v3-8e-summarization-batch-event-loop-fix

## Root Cause

`batch_summarize_pending()` called `asyncio.run()` three times:
1. Once to fetch pending patents (creates event loop A)
2. Once per patent in the loop (creates event loop B, C, D... per patent)

Each `asyncio.run()` creates a new event loop. SQLAlchemy/asyncpg connections established in loop A become invalid when loop B starts, causing:

```
RuntimeError: Event loop is closed
got Future attached to a different loop
Exception terminating connection <AdaptedConnection ...>
coroutine 'Connection._cancel' was never awaited
```

## Fix

Both `batch_summarize_pending()` and `batch_resummarize_enriched()` now call exactly ONE `asyncio.run()` that runs the entire batch in a single event loop:

```
batch_summarize_pending → asyncio.run(_batch_summarize_async(limit))
  → await _get_pending_patents(limit)
  → for patent: await _summarize_patent_async(patent_id)
```

## Changed Files

`backend/app/tasks/summarize.py` — refactored with:
- `_batch_summarize_async(limit)` — single-event-loop batch runner
- `_batch_resummarize_async(limit)` — single-event-loop re-summarize runner
- `summarize_patent()` — single-patent task unchanged (one asyncio.run is fine)
- `_summarize_patent_async()` — unchanged

## Validation

```
5-patent batch: 5 succeeded, 0 failed, 0 skipped ✅
50-patent batch: running...
```

## Recommendation

Safe to resume AI backlog processing in staged batches.
