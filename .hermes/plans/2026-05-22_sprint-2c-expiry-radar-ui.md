# Sprint 2C — Expiry Radar UI: Implementation Plan

> **Status:** Backend complete (Sprints 2A, 2B — 178 tests pass). UI only.

## Goal

Turn `/expiry` from a table of estimated dates into the core product
surface — with sectioned views, confidence badges, legal caveats, and
export. No unsafe "free to use" language anywhere.

## Backend API Endpoints Consumed

| Endpoint | Used for |
|----------|----------|
| `GET /api/v1/expiry` | Main list with filters: `expiry_status`, `confidence`, `maintenance_status`, `active_family_risk`, `min_expiry_opportunity_score`, plus existing `days_ahead`, `office`, `industry`, `time_horizon`. Sorts: `expiry_urgency`, `expiry_date`, `opportunity_score`, `expiry_opportunity_score`, `confidence`, `recently_assessed`. |
| `GET /api/v1/expiry/summary` | Dashboard cards at top: `total_with_expiry`, `by_status`, `by_confidence`, `with_family_risk`, `without_family_risk`, `high_opportunity_count`, `by_maintenance`. |
| `GET /api/v1/expiry/opportunities` | High-Opportunity section: `min_score` filter, ranked by `expiry_opportunity_score` desc. |

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/app/expiry/page.tsx` | Full rewrite: sections, filters, URL state, CSV export |
| `frontend/src/lib/types.ts` | Add `ExpiryRadarItem`, `ExpirySummaryResponse`, `ExpiryOpportunityItem` interfaces |
| `frontend/src/lib/api.ts` | Add `expiryApi.getSummary()`, `expiryApi.getOpportunities()`, extend `expiryApi.list()` params |

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/expiry/ExpiryRadarCard.tsx` | Single patent card: expiry date, status badge, confidence badge, family risk indicator, opportunity scores, caveat footer |
| `frontend/src/components/expiry/ExpiryRadarSection.tsx` | Section wrapper: title, item count, card list, empty state with legal explanation |
| `frontend/src/components/expiry/ExpirySummaryCards.tsx` | Top-of-page summary: mini stat cards pulling from `/api/v1/expiry/summary` |

## Component Breakdown

```
/expiry page
├── ExpirySummaryCards         ← GET /api/v1/expiry/summary
│   ├── TotalWithExpiry
│   ├── ExpiringSoonCount
│   ├── HighOpportunityCount
│   └── NeedsVerificationCount
├── FilterBar                  ← URL-state synced, matches /opportunity pattern
│   ├── Status dropdown
│   ├── Confidence dropdown
│   ├── Family Risk toggle
│   ├── Days Ahead slider/input
│   └── Sort selector
├── Section: Expiring Soon     ← GET /api/v1/expiry?expiry_status=expiring_soon
│   └── ExpiryRadarCard × N
├── Section: Recently Expired   ← GET /api/v1/expiry?expiry_status=expired_estimated
│   └── ExpiryRadarCard × N
├── Section: Likely Lapsed     ← GET /api/v1/expiry?expiry_status=lapsed_possible
│   └── ExpiryRadarCard × N
├── Section: Revival Candidates ← (same list, filtered client-side by tags/score)
│   └── ExpiryRadarCard × N
├── Section: Patent Cliffs     ← (reuses existing cliff data from /trends)
│   └── PatentCliffCard × N
├── Section: High-Opportunity   ← GET /api/v1/expiry/opportunities
│   └── ExpiryRadarCard × N
├── Section: Needs Verification ← GET /api/v1/expiry?confidence=low
│   └── ExpiryRadarCard × N
└── CSV Export button           ← uses current filter state
```

## Build Order (5 chunks, stop after each)

### Chunk 1 — Section Count Cards

- Add types: `ExpirySummaryResponse`
- Add API method: `expiryApi.getSummary()`
- Build `ExpirySummaryCards` component
- Wire into `/expiry` page as top section
- Render 4 stat cards: Total With Expiry, Expiring Soon, High Opportunity, Needs Verification
- Each card loads from `/api/v1/expiry/summary`
- Verify: `npm run build` clean

### Chunk 2 — Main List with Filters

- Add types: `ExpiryRadarItem` (extends existing `ExpiryItem` with assessment fields)
- Extend `expiryApi.list()` with new filter/sort params
- Build `ExpiryRadarCard` component — single patent row/card showing:
  - Title + doc_id link to patent detail
  - Expiry date (formatted)
  - Status badge (color-coded: green=active/expiring, amber=estimated, red=expired/lapsed, gray=unknown)
  - Confidence badge (confirmed/high/medium/low)
  - Active family risk indicator (⚠ icon + tooltip when true)
  - Opportunity score + expiry opportunity score
  - Legal caveat footer: "Verify with official registers before relying on expiry status."
- Build `ExpiryRadarSection` wrapper
- Wire 7 sections into page (some data-driven from backend, some client-filtered)
- Verify: `npm run build` clean

### Chunk 3 — URL State

- Sync filters to URL query params (matches `/opportunity` and `/patents` pattern)
- Use `useSearchParams` + `useRouter` from Next.js
- Filters synced: `expiry_status`, `confidence`, `active_family_risk`, `days_ahead`, `sort_by`, `sort_order`
- Deep-linkable: sharing a URL preserves the filter state
- Verify: `npm run build` clean, URL params survive page refresh

### Chunk 4 — Empty States

- Replace generic "no data" messages with legal-context explanations
- Per-section empty state examples:
  - "No patents found in this expiry window. This does not mean patents in this category are safe to use — always verify with official registers."
  - "Expiry status could not be determined for these patents. Missing filing dates, grant dates, or legal status data. Treat all estimated expirations as unverified."
  - "No high-opportunity expired patents found. Opportunity scoring depends on confirmed expiry status, commercial relevance, and legal clarity. As data improves, this section will populate."
- Verify: `npm run build` clean

### Chunk 5 — CSV Export

- Add "Export CSV" button in filter bar (visible when list has items)
- Generate CSV from currently-filtered results
- Columns: Title, Assignee(s), Expiry Date, Days Until Expiry, Status, Confidence, Family Risk, Opportunity Score, Expiry Opportunity Score, Legal Caveat
- Download via `Blob` + `URL.createObjectURL`
- Filename: `expiry-radar-{date}.csv`
- Disabled state when no results
- Verify: `npm run build` clean

## Hard Constraints

- **No "free to use" or "public domain"** language anywhere in the UI
- **"Verify with official registers"** caveat on every card
- **Usage signal count** renders as "0" with a tooltip "Usage signals coming in Sprint 5" — no blocking
- **Reuse existing components**: ExpiryRadarCard similar to PatentListItem card pattern, FilterBar similar to opportunity page
- **Patent figures NOT in scope** — Sprint 4.5
- **Do not run git commands**

## Verification

Between each chunk:
- `npm run build` — must be clean (0 errors, pre-existing warnings OK)
- Backend `pytest -q` — must stay 178 passed
- Visual check: navigate to `/expiry` in browser

## Reference: Existing Patterns

- URL state + filter pattern: `frontend/src/app/opportunity/page.tsx`
- Patent card pattern: `frontend/src/components/patents/PatentCard.tsx` (or inline in opportunity list)
- API method pattern: `frontend/src/lib/api.ts` — `expiryApi.list()`, `opportunityApi.list()`
