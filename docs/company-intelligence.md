# Company Intelligence — Sprint 5

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-5-company-intelligence`

---

## 1. Files Changed

| File | Change |
|------|--------|
| `backend/app/api/v1/suppliers.py` | +89 lines: follow endpoints, top inventors query, CompanyProfile enriched |
| `frontend/src/app/(app)/companies/[name]/page.tsx` | +154/-43: redesigned with follow, portfolio, inventors, expiry exposure |
| `frontend/src/app/(app)/search/page.tsx` | +31: wired save/unsave on result cards |
| `frontend/src/lib/types.ts` | +1: CompanyProfile.top_inventors |

## 2. Screens Changed

### Company Detail Page (`/companies/[name]`)

**Before:** H1 title, country/entity badges, score, 4 stat cards, recent patents list, top CPC sidebar, avg signal score. No follow button. No portfolio narrative.

**After:**
```
├── Back breadcrumb
├── Header + Follow button (with live state)
├── Portfolio summary (4 stat cards)
├── Main column
│   └── Recent Patents
├── Sidebar
│   ├── Technology Focus (top CPC codes)
│   ├── Top Inventors (top 5, name + count)
│   ├── Avg. Signal Score
│   └── Expiry Exposure (when expiring > 0, with link to Expiry Radar)
```

**States:**
- Loading: `LoadingState` component (from Sprint 2)
- Error: `ErrorState` component + back link
- Success: enriched layout as above
- Empty: "No recent patents found", "No CPC data available" — honest, not broken

## 3. Sprint 2 Components Reused

| Component | Where used |
|-----------|-----------|
| `LoadingState` | Company detail loading state |
| `ErrorState` | Company detail error state |
| `Badge` | Country, entity_type, CPC codes |

## 4. Company Data / API Changes

### New endpoints in `suppliers.py`:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/suppliers/follow/{name}` | Required | Check if user follows a company |
| POST | `/suppliers/follow/{name}` | Required | Follow a company |
| DELETE | `/suppliers/follow/{name}` | Required | Unfollow a company |
| GET | `/suppliers/follows` | Required | List followed companies |

### Company profile enriched:

| Field | Source | New? |
|-------|--------|------|
| `top_inventors` | `patent_publications.inventors` JSONB | ✅ New — top 5 by patent count |

Uses existing `follow_company.py` service (was already written, just no endpoints).

## 5. Follow / Save / Watchlist Behavior

| Action | Implementation |
|--------|---------------|
| Follow company | POST/DELETE `/suppliers/follow/{name}`, button on detail page |
| Check follow status | GET `/suppliers/follow/{name}`, SWR with `revalidateOnFocus: false` |
| Unfollow | DELETE, 404 if not following |
| Save patent from search | `addToWatchlist`/`removeFromWatchlist`, `mutateWatchlist` after action |
| Saved state | `savedIds` Set from `useWatchlist()`, per-card `isSaved` prop |

## 6. Acceptance Criteria

| Criteria | Status |
|----------|--------|
| Company pages no longer raw metadata pages | ✅ Portfolio summary, tech focus, top inventors, expiry exposure |
| Pages explain portfolio movement, recent filings, tech concentration, expiry | ✅ All sections present |
| Empty/loading/error states use Sprint 2 UX | ✅ LoadingState, ErrorState |
| Follow/save behavior implemented | ✅ Follow via API, save via watchlist hooks |
| No fake intelligence | ✅ All data from real queries — no LLM, no invented claims |
| No unsupported commercial claims | ✅ Expiry exposure links to real data |

## 7. Tests

- Backend tests not runnable locally (venv broken, Python 3.9 vs 3.12 requirement)
- Frontend tests: 53/53 PASS (no new tests added — company detail is a page-level integration)

## 8. Baseline

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✅ PASS |
| `npm run build` | ✅ 6.6s |
| `npm run lint` | ✅ 0 errors, 0 warnings (excl. documented `<img>`) |
| `npm test` | ✅ 53/53 |

## 9. Deferred Search Items (from Sprint 4.5)

| Item | Reason | Priority |
|------|--------|----------|
| CPC/assignee filter dropdowns | Needs facet aggregation from backend search endpoint | P2 |
| Date range picker | Most users search by topic, not date | P3 |
| Patent preview drawer | Requires side-panel infrastructure, non-trivial | P2 |
| Save/unsave on result cards | ✅ COMPLETED in Sprint 5 commit `bb8e477` | — |

## 10. Follow-up Items

| Item | Sprint |
|------|--------|
| Company "What Changed" module (filing deltas vs previous period) | Sprint 5.5 or 6 |
| Followed companies visible in Watchlist | Sprint 6 |
| Company comparison (side-by-side) | Future |
| Backend tests for follow endpoints | Post-venv-fix |
