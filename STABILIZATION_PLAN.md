     1|# Invention Index 8 V1 — Production Stabilization Plan
     2|
     3|## Phase 0: Foundation (Security + Stability)
     4|*Target: zero critical issues, all API errors handled gracefully*
     5|
     6|### 0.1 — Fix SQL Injection (CRITICAL #1, #2)
     7|- [ ] `patents.py:56`: Replace `f'%"${cpc_prefix}%'` with parameterized `func.jsonb_path_exists` or validate against `/^[A-Z][0-9]{2}[A-Z](\/[0-9]+)?$/`
     8|- [ ] `opportunity.py:311`: Same pattern — parameterize jsonb_path_exists
     9|- [ ] `ai_runs.py:240`: Same fix
    10|- [ ] `expiry.py:46`: Sanitize `industry` filter with same regex
    11|- [ ] Add `validate_cpc_prefix()` helper in `app/core/validators.py`
    12|- [ ] Run `pytest tests/api/test_patents.py tests/api/test_opportunity.py -x` to verify
    13|
    14|### 0.2 — Fix `str(item)` Bug (CRITICAL #5)
    15|- [ ] `watchlist.py:183`: Change `str(item)` to `str(item.id)`
    16|- [ ] Run `pytest tests/api/test_watchlist.py -x`
    17|
    18|### 0.3 — Add Error Handling to All Endpoints (CRITICAL #3)
    19|- [ ] Create `app/api/error_handler.py` with `async_db_handler()` wrapper that catches `SQLAlchemyError` → 500, `ValueError` → 422
    20|- [ ] Wrap all endpoints in `patents.py`, `trends.py`, `themes.py`, `watchlist.py`, `semantic_search.py`
    21|- [ ] Add structured logging on errors: `logger.exception("endpoint_name failed")`
    22|- [ ] Run full backend test suite
    23|
    24|### 0.4 — Fix Frontend Error States (CRITICAL #4)
    25|- [ ] Add `error.tsx` at `frontend/src/app/error.tsx` (Next.js error boundary)
    26|- [ ] Add `global-error.tsx` for root-level crashes
    27|- [ ] Create `frontend/src/components/ErrorDisplay.tsx` reusable component
    28|- [ ] Update all 12 pages to consume SWR `error`:
    29|  ```tsx
    30|  const { data, error, isLoading } = useSWR(...)
    31|  if (error) return <ErrorDisplay error={error} onRetry={() => mutate()} />
    32|  ```
    33|- [ ] Run `npm run build` to verify zero regressions
    34|
    35|---
    36|
    37|## Phase 1: Backend Data Integrity
    38|*Target: consistent API behavior, no N+1, correct pagination*
    39|
    40|### 1.1 — Fix N+1 Queries (HIGH #7, #8)
    41|- [ ] `themes.py:70-74`: Replace per-theme count loop with single JOIN + GROUP BY query
    42|- [ ] `families.py:171-177`: Replace per-family query with subquery/window function
    43|- [ ] Verify counts match old implementation
    44|
    45|### 1.2 — Fix In-Memory Pagination (CRITICAL #6, MEDIUM #14, #21)
    46|- [ ] Rewrite `suppliers.py:list_suppliers` to push sorting + pagination to SQL
    47|- [ ] Standardize on `PaginatedResponse[T]` for all list endpoints
    48|- [ ] Add pagination to: `list_themes`, `get_watchlist`, `growing_trends`
    49|- [ ] Fix `growing_trends` total count (MEDIUM #22)
    50|
    51|### 1.3 — Optimize get_stats (HIGH #9)
    52|- [ ] Convert 6 sequential queries to `asyncio.gather()`
    53|- [ ] Verify response shape unchanged
    54|
    55|### 1.4 — Fix Type/Validation Issues (HIGH #12, MEDIUM #17, #23)
    56|- [ ] `watchlist.py:25`: Change `patent_id: str` → `patent_id: UUID`
    57|- [ ] `trends.py:234`: Return 404 instead of None
    58|- [ ] `patents.py`: Add input validation to `generate_trend_snapshot` and `generate_assignee_intelligence` matching existing guards
    59|- [ ] Add `days_until_expiry` to `PatentListItem` schema (MEDIUM #16)
    60|
    61|---
    62|
    63|## Phase 2: Frontend UX Completion
    64|*Target: all pages handle loading/error/empty, filters work*
    65|
    66|### 2.1 — Loading States (HIGH #10)
    67|- [ ] Add `loading.tsx` at root level and per-route
    68|- [ ] Replace raw "0" ghosts with `<Skeleton />` on: dashboard summary stats, trends summary cards, expiry cliff cards
    69|- [ ] Add loading spinners on all mutation buttons (watchlist add/remove, AI generate)
    70|
    71|### 2.2 — Pagination & Filters (MEDIUM #18, #20)
    72|- [ ] Add filter controls to `/patents` page (CPC, assignee, office, date range, score range)
    73|- [ ] Add pagination to: watchlist, themes list, trends (hot/growing), convergence
    74|- [ ] Add "View all" link from dashboard Priority Watch → filtered patents page
    75|- [ ] Add sort direction toggle (asc/desc) to all sort dropdowns
    76|
    77|### 2.3 — AI Generation UX (HIGH #13 infrastructure)
    78|- [ ] Patent detail page: Disable generate buttons during loading (prevent double-clicks)
    79|- [ ] Patent detail page: Show error feedback on failed generation
    80|- [ ] `usePatentSummary`: Add exponential backoff to polling (start 5s, cap at 60s, stop after 10 failures)
    81|- [ ] Admin AI Runs: Add auto-refresh on active runs (30s interval)
    82|
    83|---
    84|
    85|## Phase 3: AI Pipeline Activation
    86|*Target: run why_now and opportunity_narrative at scale*
    87|
    88|### 3.1 — Fix Empty Opportunity Narrative (MEDIUM #24)
    89|- [ ] Review `opportunity_narrative_v1.md` prompt — likely needs claims text included
    90|- [ ] Test with patent that has full claims_text + abstract + tags
    91|- [ ] Validate output schema before persisting
    92|
    93|### 3.2 — Run Batch AI Jobs
    94|- [ ] Set `ANTHROPIC_API_KEY` in `.env`
    95|- [ ] Run `why_now` batch on all 47 scored patents via Admin UI
    96|- [ ] Run `opportunity_narrative` batch on top 20 scored patents
    97|- [ ] Verify artifacts created with valid JSON payloads
    98|- [ ] Verify denormalization to `PatentPublication.why_now_text`
    99|
   100|### 3.3 — Trend/Assignee Intelligence (Steps 20-23)
   101|- [ ] Run `trend_snapshot` batch on scored patents
   102|- [ ] Run `assignee_intelligence` batch on scored patents
   103|- [ ] Verify artifacts and dashboard data
   104|
   105|---
   106|
   107|## Phase 4: Infrastructure Hardening
   108|*Target: production-ready Docker, monitoring, security*
   109|
   110|### 4.1 — Docker Cleanup (LOW #30, #31)
   111|- [ ] Add `.dockerignore` excluding: `__pycache__`, `.pytest_cache`, `node_modules`, `.git`, `dist/`, `*.pyc`
   112|- [ ] Move secrets from `.env` to Docker secrets or external vault (placeholder for V1)
   113|
   114|### 4.2 — Auth Placeholder
   115|- [ ] Add basic middleware that returns 401 if `X-API-Key` header is missing (dev mode: accept any key)
   116|- [ ] Protect `/admin/ai-runs` page behind the same check
   117|
   118|### 4.3 — Database
   119|- [ ] Add `pg_dump` cron in docker-compose (daily backup to `backups/` volume)
   120|- [ ] Document restore procedure in SETUP.md
   121|
   122|---
   123|
   124|## Phase 5: Polish (LOW items)
   125|*Target: zero warnings, consistent patterns*
   126|
   127|### 5.1 — Code Cleanup
   128|- [ ] Extract duplicated `PatentPublication(**row._mapping)` to shared helper (#26)
   129|- [ ] Fix `ThemeResponse.created_at` to use `datetime` type (#27)
   130|- [ ] Standardize `nullslast()` → `nulls_last()` everywhere (#28)
   131|- [ ] Fix `delete_theme` to return typed Pydantic model (#21)
   132|
   133|### 5.2 — CPC Labels
   134|- [ ] Load CPC labels from a data file (100+ common codes) instead of hardcoded 17-22 (#25)
   135|- [ ] Fallback: show section label from first character (G=Physics, H=Electricity, etc.)
   136|
   137|---
   138|
   139|## Execution Order Summary
   140|
   141|| Phase | Items | Est. Time | Depends On |
   142||-------|-------|-----------|------------|
   143|| 0: Foundation | #1-5 | 4-6 hours | Nothing |
   144|| 1: Backend Integrity | #6-9, #12, #16, #17, #22, #23 | 4-5 hours | Phase 0 |
   145|| 2: Frontend UX | #10, #18, #20, #29 | 6-8 hours | Phase 0 |
   146|| 3: AI Pipeline | #13, #24 + batches | 2-3 hours (+ LLM runtime) | Phase 0 + API key |
   147|| 4: Infrastructure | #30, #31, #32 + auth | 2-3 hours | Phase 0 |
   148|| 5: Polish | #21, #25-28 | 2-3 hours | Any time |
   149|
   150|**Total: 20-28 hours of engineering + LLM batch runtime**
   151|