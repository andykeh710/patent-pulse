# Sprint 3 — Patent Detail Credibility: Implementation Plan

> **Status:** All 7 tabs exist. Sprint 3 deepens them, does not rebuild.

## Gap Analysis: What's Present vs What's Missing

| Sprint 3 Item | Current State | Missing |
|---|---|---|
| Claims tab | `ClaimsPanel.tsx` — parses independent/dependent, shows count, toggle | Plain-English summary, key mechanisms, broadness indicators |
| Family tab | `FamilyTab` — lists publication numbers, has legal disclaimer | Jurisdictions, dates, active/expired per member, relationship type, active family risk integration |
| External links | `ExternalPatentLinks.tsx` — Google Patents + USPTO + Espacenet | WIPO link |
| Similar patents | `SimilarTab` — semantic search by embedding, "no embedding" empty state | "Similar by claims" toggle (stretch) |
| Citation indicators | `CitationsTab` — backward citations only with Google Patents links | Forward citations, citation counts in detail header |
| Assignee clickable | `OverviewTab` — already links to `/companies/[name]` | Nothing — DONE |
| Inventor names | `OverviewTab` — displayed in sidebar | Nothing — DONE (could be more prominent but present) |

## Changes NOT in scope for Sprint 3

- Patent figure thumbnails (Sprint 4.5)
- Commercial usage signals (Sprint 5)
- Full INPADOC family reconciliation (needs external data source — deferred)
- Backend family-member detail endpoint (requires per-member DB rows we don't have)
- AI-generated claims summaries via LLM (cost risk — defer to post-Sprint 5)

## Build Strategy

The only backend change needed is adding `citations_forward` to the
`GET /api/v1/patents/{id}` response so the frontend can show both
directions. Everything else is frontend enhancement of existing tabs.

## Files Modified (5)

| File | What Changes |
|------|-------------|
| `backend/app/core/schemas.py` | Add `citations_forward` to `PatentDetailResponse` |
| `frontend/src/components/patents/ClaimsPanel.tsx` | Add key mechanisms extractor + broadness indicator |
| `frontend/src/components/patents/ExternalPatentLinks.tsx` | Add WIPO link |
| `frontend/src/app/patents/[id]/page.tsx` | Family tab rewrite, Citations tab rewrite, add citation counts to header, move inventor names more prominent |
| `frontend/src/lib/types.ts` | Add `citations_forward` to `PatentDetail` interface |

## Files Created (0)

No new files. All work extends existing components and the detail page.

## Build Order (5 chunks — stop after each)

### Chunk 1 — Backend: forward citations in API response

The `PatentPublication` model already has `citations_backward` but the
`PatentDetailResponse` schema field `citations_backward` maps 1:1. Add
a companion field. If `citations_forward` doesn't exist on the model, add
it in a migration.

**Check first:** Does `PatentPublication` have `citations_forward`? If not:
- Create migration 0009 adding `citations_forward JSONB default '[]'`
- Add field to ORM model
- Add to `PatentDetailResponse.from_patent()`
- Add to `PatentDetail` TypeScript interface
- Verify: `pytest -q` stays green (178+), `npm run build` clean

If `citations_forward` already exists, skip migration and just add to schema/TS.

### Chunk 2 — Claims tab: key mechanisms + broadness indicator

Enhance `ClaimsPanel.tsx`:

- Extract key mechanisms from independent claims: look for "comprising,"
  "wherein," "configured to" patterns, show as tags below each claim
- Add broadness indicator: count "comprising" (open-ended, broader) vs
  "consisting of" (closed, narrower) per claim, show as a small badge
- Keep existing parsing logic (already tested and working)
- No LLM — pure regex/text analysis
- Verify: `npm run build` clean

### Chunk 3 — Family tab: jurisdictions, dates, family risk

Rewrite `FamilyTab` in `page.tsx` (replace lines 399–427):

- Parse jurisdiction from family member IDs:
  - `US*` → US, `EP*` → EP, `WO*` → WO, `CN*` → CN, `JP*` → JP, etc.
  - Show office flag/abbreviation next to each member
- Show family member count grouped by jurisdiction
- Pull `active_family_risk` from ExpiryAssessment if available (only
  works if assessment was run — otherwise show "Not assessed")
- Keep the existing legal disclaimer but make it more specific:
  "Active family members in other jurisdictions may still be enforceable."
- If family members > 0 but all in same office as patent → note this
- Verify: `npm run build` clean

### Chunk 4 — Citations: forward + backward, header counts

- Rewrite `CitationsTab` to show both forward and backward citations
  (two sections)
- Add citation counts to patent detail header (line ~184-191 area):
  ```
  US12345678 · USPTO · GRANTED · ⬅ 12 cited · ➡ 5 citing
  ```
- If `citations_forward` is empty/null, show only backward count
- External links remain Google Patents for each citation
- Verify: `npm run build` clean

### Chunk 5 — External links + verification

- Add WIPO link to `ExternalPatentLinks.tsx`:
  `https://patentscope.wipo.int/search/en/detail.jsf?docId={docId}`
  Fallback to office+number search if docId unavailable
- Run full verification:
  - `pytest -q` — stay 178+
  - `npm run build` — 0 errors
  - `npm test` — all pass

## What This Sprint Does NOT Do

- Does NOT generate AI claims summaries (cost-risk, defer)
- Does NOT create per-family-member DB rows (needs INPADOC feeds)
- Does NOT add "similar by claims" toggle (needs claims embedding endpoint)
- Does NOT touch Opportunity, Overview, Legal/Expiry, or Similar tabs
- Does NOT add new NPM packages
- Does NOT change the tab count (still 7)
- Does NOT remove or rename any existing tab
