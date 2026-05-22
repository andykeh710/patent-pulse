# Patent Pulse V1 — Production Stabilization Plan

## Phase 0: Foundation (Security + Stability)
*Target: zero critical issues, all API errors handled gracefully*

### 0.1 — Fix SQL Injection (CRITICAL #1, #2)
- [ ] `patents.py:56`: Replace `f'%"${cpc_prefix}%'` with parameterized `func.jsonb_path_exists` or validate against `/^[A-Z][0-9]{2}[A-Z](\/[0-9]+)?$/`
- [ ] `opportunity.py:311`: Same pattern — parameterize jsonb_path_exists
- [ ] `ai_runs.py:240`: Same fix
- [ ] `expiry.py:46`: Sanitize `industry` filter with same regex
- [ ] Add `validate_cpc_prefix()` helper in `app/core/validators.py`
- [ ] Run `pytest tests/api/test_patents.py tests/api/test_opportunity.py -x` to verify

### 0.2 — Fix `str(item)` Bug (CRITICAL #5)
- [ ] `watchlist.py:183`: Change `str(item)` to `str(item.id)`
- [ ] Run `pytest tests/api/test_watchlist.py -x`

### 0.3 — Add Error Handling to All Endpoints (CRITICAL #3)
- [ ] Create `app/api/error_handler.py` with `async_db_handler()` wrapper that catches `SQLAlchemyError` → 500, `ValueError` → 422
- [ ] Wrap all endpoints in `patents.py`, `trends.py`, `themes.py`, `watchlist.py`, `semantic_search.py`
- [ ] Add structured logging on errors: `logger.exception("endpoint_name failed")`
- [ ] Run full backend test suite

### 0.4 — Fix Frontend Error States (CRITICAL #4)
- [ ] Add `error.tsx` at `frontend/src/app/error.tsx` (Next.js error boundary)
- [ ] Add `global-error.tsx` for root-level crashes
- [ ] Create `frontend/src/components/ErrorDisplay.tsx` reusable component
- [ ] Update all 12 pages to consume SWR `error`:
  ```tsx
  const { data, error, isLoading } = useSWR(...)
  if (error) return <ErrorDisplay error={error} onRetry={() => mutate()} />
  ```
- [ ] Run `npm run build` to verify zero regressions

---

## Phase 1: Backend Data Integrity
*Target: consistent API behavior, no N+1, correct pagination*

### 1.1 — Fix N+1 Queries (HIGH #7, #8)
- [ ] `themes.py:70-74`: Replace per-theme count loop with single JOIN + GROUP BY query
- [ ] `families.py:171-177`: Replace per-family query with subquery/window function
- [ ] Verify counts match old implementation

### 1.2 — Fix In-Memory Pagination (CRITICAL #6, MEDIUM #14, #21)
- [ ] Rewrite `suppliers.py:list_suppliers` to push sorting + pagination to SQL
- [ ] Standardize on `PaginatedResponse[T]` for all list endpoints
- [ ] Add pagination to: `list_themes`, `get_watchlist`, `growing_trends`
- [ ] Fix `growing_trends` total count (MEDIUM #22)

### 1.3 — Optimize get_stats (HIGH #9)
- [ ] Convert 6 sequential queries to `asyncio.gather()`
- [ ] Verify response shape unchanged

### 1.4 — Fix Type/Validation Issues (HIGH #12, MEDIUM #17, #23)
- [ ] `watchlist.py:25`: Change `patent_id: str` → `patent_id: UUID`
- [ ] `trends.py:234`: Return 404 instead of None
- [ ] `patents.py`: Add input validation to `generate_trend_snapshot` and `generate_assignee_intelligence` matching existing guards
- [ ] Add `days_until_expiry` to `PatentListItem` schema (MEDIUM #16)

---

## Phase 2: Frontend UX Completion
*Target: all pages handle loading/error/empty, filters work*

### 2.1 — Loading States (HIGH #10)
- [ ] Add `loading.tsx` at root level and per-route
- [ ] Replace raw "0" ghosts with `<Skeleton />` on: dashboard summary stats, trends summary cards, expiry cliff cards
- [ ] Add loading spinners on all mutation buttons (watchlist add/remove, AI generate)

### 2.2 — Pagination & Filters (MEDIUM #18, #20)
- [ ] Add filter controls to `/patents` page (CPC, assignee, office, date range, score range)
- [ ] Add pagination to: watchlist, themes list, trends (hot/growing), convergence
- [ ] Add "View all" link from dashboard Priority Watch → filtered patents page
- [ ] Add sort direction toggle (asc/desc) to all sort dropdowns

### 2.3 — AI Generation UX (HIGH #13 infrastructure)
- [ ] Patent detail page: Disable generate buttons during loading (prevent double-clicks)
- [ ] Patent detail page: Show error feedback on failed generation
- [ ] `usePatentSummary`: Add exponential backoff to polling (start 5s, cap at 60s, stop after 10 failures)
- [ ] Admin AI Runs: Add auto-refresh on active runs (30s interval)

---

## Phase 3: AI Pipeline Activation
*Target: run why_now and opportunity_narrative at scale*

### 3.1 — Fix Empty Opportunity Narrative (MEDIUM #24)
- [ ] Review `opportunity_narrative_v1.md` prompt — likely needs claims text included
- [ ] Test with patent that has full claims_text + abstract + tags
- [ ] Validate output schema before persisting

### 3.2 — Run Batch AI Jobs
- [ ] Set `ANTHROPIC_API_KEY` in `.env`
- [ ] Run `why_now` batch on all 47 scored patents via Admin UI
- [ ] Run `opportunity_narrative` batch on top 20 scored patents
- [ ] Verify artifacts created with valid JSON payloads
- [ ] Verify denormalization to `PatentPublication.why_now_text`

### 3.3 — Trend/Assignee Intelligence (Steps 20-23)
- [ ] Run `trend_snapshot` batch on scored patents
- [ ] Run `assignee_intelligence` batch on scored patents
- [ ] Verify artifacts and dashboard data

---

## Phase 4: Infrastructure Hardening
*Target: production-ready Docker, monitoring, security*

### 4.1 — Docker Cleanup (LOW #30, #31)
- [ ] Add `.dockerignore` excluding: `__pycache__`, `.pytest_cache`, `node_modules`, `.git`, `dist/`, `*.pyc`
- [ ] Move secrets from `.env` to Docker secrets or external vault (placeholder for V1)

### 4.2 — Auth Placeholder
- [ ] Add basic middleware that returns 401 if `X-API-Key` header is missing (dev mode: accept any key)
- [ ] Protect `/admin/ai-runs` page behind the same check

### 4.3 — Database
- [ ] Add `pg_dump` cron in docker-compose (daily backup to `backups/` volume)
- [ ] Document restore procedure in SETUP.md

---

## Phase 5: Polish (LOW items)
*Target: zero warnings, consistent patterns*

### 5.1 — Code Cleanup
- [ ] Extract duplicated `PatentPublication(**row._mapping)` to shared helper (#26)
- [ ] Fix `ThemeResponse.created_at` to use `datetime` type (#27)
- [ ] Standardize `nullslast()` → `nulls_last()` everywhere (#28)
- [ ] Fix `delete_theme` to return typed Pydantic model (#21)

### 5.2 — CPC Labels
- [ ] Load CPC labels from a data file (100+ common codes) instead of hardcoded 17-22 (#25)
- [ ] Fallback: show section label from first character (G=Physics, H=Electricity, etc.)

---

## Execution Order Summary

| Phase | Items | Est. Time | Depends On |
|-------|-------|-----------|------------|
| 0: Foundation | #1-5 | 4-6 hours | Nothing |
| 1: Backend Integrity | #6-9, #12, #16, #17, #22, #23 | 4-5 hours | Phase 0 |
| 2: Frontend UX | #10, #18, #20, #29 | 6-8 hours | Phase 0 |
| 3: AI Pipeline | #13, #24 + batches | 2-3 hours (+ LLM runtime) | Phase 0 + API key |
| 4: Infrastructure | #30, #31, #32 + auth | 2-3 hours | Phase 0 |
| 5: Polish | #21, #25-28 | 2-3 hours | Any time |

**Total: 20-28 hours of engineering + LLM batch runtime**
