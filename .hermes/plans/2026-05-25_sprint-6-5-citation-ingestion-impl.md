# Sprint 6.5 — USPTO Forward Citation Ingestion + Historical Backfill

**Status:** Plan-out. Awaiting user approval before S65-1.
**Context:** Sprint 5 `usage_signals.citation_collector` returns `[]` for all 54,903 patents
because `patent_publications.citations_forward` is empty across the entire corpus.
The USPTO client at `backend/app/ingestion/uspto_client.py:107` hardcodes
`"citations": []` — a documented TODO from post-Sprint-5 audit items D1/D2.

**Constraint:** `patent_client.PatentBiblio.forward_citations` is a lazy iterator
that issues a **separate USPTO API call per patent** on iteration. Cannot be
enabled unconditionally on the hot ingestion path without rate-limit safeguards.

---

## Build Order (4 chunks)

### S65-1 — Configuration plumbing

**Files:**
- Modify: `backend/app/config.py` — add `USPTO_FETCH_CITATIONS: bool = False`
- Modify: `backend/app/ingestion/uspto_client.py` — conditionally fetch
  forward citations in `_patent_to_dict()`
- Create: `backend/tests/ingestion/test_citation_fetch.py` — unit tests

**Acceptance:**
- `USPTO_FETCH_CITATIONS` defaults to `False` (backward-compatible — hot ingestion
  path unchanged)
- When `True`: `_patent_to_dict()` iterates `PatentBiblio.forward_citations`,
  extracts doc IDs as `["USPTO:..."]`, stores in `"citations"` key
- Rate-limit retry: wraps the SDK call in a helper with 1 call/sec ceiling +
  exponential backoff on HTTP 429 (2s, 4s, 8s, max 3 retries)
- On failure after retries exhausted: log error, return empty `[]` for that patent
  (don't fail the ingestion batch)
- Test: mock `PatentBiblio.forward_citations` returning a synthetic iterator;
  assert citations populated when flag is True; assert empty when False

---

### S65-2 — Per-patent fetch helper

**Files:**
- Create: `backend/app/ingestion/citation_fetcher.py`

**Functions:**
- `async def fetch_forward_citations(session, patent: PatentPublication) -> int`
  - Looks up the patent via the patent_client SDK using `patent.doc_id`
  - Iterates `PatentBiblio.forward_citations`, extracting doc IDs
  - Updates `patent.citations_forward` in the database via the provided session
  - Returns count of citations found
  - On failure: logs error, returns 0, does NOT raise

- Wrapped in Celery task `app.tasks.backfill_citations.fetch_single_patent_citations`
  with the standard `asyncio.run()` + `engine.dispose()` in `finally` pattern (per
  post-Sprint-5 audit, matching `embeddings.py` and S6-6/S6-7 pattern).

**Acceptance:**
- Calling `fetch_forward_citations(session, patent)` on a real USPTO patent
  updates `citations_forward` from `[]` to a non-empty list
- Rate-limit respected (1 call/sec via `asyncio.sleep(1)` between calls in
  batch mode)
- Engine properly disposed after each Celery task invocation

---

### S65-3 — Historical backfill Celery task

**Files:**
- Create: `backend/app/tasks/backfill_citations.py`
- Modify: `backend/app/tasks/celery_app.py` — include + route + beat schedule

**Task:** `batch_backfill_citations(limit: int = 50)`

```
async def _batch_backfill_async(limit):
    async with async_session_maker() as session:
        # Fetch patents WHERE citations_forward = '[]' OR citations_forward IS NULL
        # ORDER BY opportunity_score DESC NULLS LAST
        # LIMIT $limit
        for patent in patents:
            await fetch_forward_citations(session, patent)
            await asyncio.sleep(1)  # rate limit: 1 call/sec
        return {"processed": count, "updated": updated}
    # engine.dispose() in finally via Celery task wrapper
```

**Acceptance:**
- Idempotent: skips patents where `citations_forward != []`
- Orders by `opportunity_score DESC` (highest-value first)
- Rate: 1 patent/sec → 50 patents ~50 seconds per batch
- Beat schedule: every 5 min, limit=50 → ~600 patents/hr → ~90 hours for full 54K corpus
  (documented in comments as informational, not a guarantee)
- Wired into `celery_app.py`:
  - `include` list: `"app.tasks.backfill_citations"`
  - `task_routes`: `"app.tasks.backfill_citations.*": {"queue": "maintenance"}`
  - `beat_schedule` entry `"citation-backfill"`: crontab every 5 min

---

### S65-4 — Tests + verification

**Files:**
- Create: `backend/tests/ingestion/test_citation_fetch.py` — mocked SDK response
  for `_patent_to_dict` with flag on/off
- Create: `backend/tests/tasks/test_backfill_citations.py` — task harness with
  session injection (S6-9 pattern)

**Test coverage:**
- `_patent_to_dict` with `USPTO_FETCH_CITATIONS=False` → `"citations": []`
- `_patent_to_dict` with `USPTO_FETCH_CITATIONS=True` + mocked SDK → citations populated
- Rate-limit retry: mock 429 response → exponential backoff exercised → eventual success
- Rate-limit exhaustion: mock 429 × 4 → returns empty `[]`, does not raise
- `fetch_forward_citations` updates DB row, returns correct count
- `batch_backfill_citations` idempotency: re-run on already-populated patent → skipped
- `batch_backfill_citations` processes only empty-citation patents

**Live verification:**
- Manually invoke `fetch_forward_citations` on 3 real patents via the dev DB
- Run `batch_backfill_citations(limit=10)` — confirm 10 patents have
  `citations_forward` populated
- Re-run `usage_signal_score` on those 10 patents (via `collect_all_evidence`)
  — show before/after evidence counts (citations were 0, now > 0 for at
  least some patents)
- If the backfill runs successfully against live data: report the first 10
  patents with new citation evidence and their before/after usage signal scores

**Language audit:**
- No new user-facing strings — docstrings and comments only.
- Run grep on all new files for forbidden phrases; must return zero hits.

**pytest -q:**
- Paste literal tail output (5-15 lines)
- Expected: 264 baseline + ~8 new tests = ~272 passed, 0 failed

---

## Acceptance Criteria for Sprint 6.5

| Criterion | Verification |
|-----------|-------------|
| `USPTO_FETCH_CITATIONS=true` populates citations on new ingestion | Unit test with mocked SDK |
| Feature flag defaults to `false` | Existing ingestion path unchanged |
| Backfill task scheduled in beat | `celery_app.py` confirms beat entry |
| Backfill is idempotent | Test: re-run on populated patent → skipped |
| Backfill produces rows | Live test: 10 patents go from empty to non-empty `citations_forward` |
| Citation collector returns non-empty evidence | Re-run `collect_all_evidence` on backfilled patents |
| Rate-limit respected | 1 call/sec enforced via `asyncio.sleep(1)` |
| No forbidden phrases | Language audit passes |
| Tests pass | `pytest -q` shows 0 failed |

---

## Operating Rules (from Sprint 6, still in effect)

- Verification blocks must include **literal** `pytest -q` output tail (copy-pasted,
  not paraphrased).
- No `--ignore`, no xfail-as-pass, no `as any`.
- DEVIATION DETECTED = stop, present Options A/B/C, wait for user.
- `engine.dispose()` in `finally` on every Celery task per A2 audit.
