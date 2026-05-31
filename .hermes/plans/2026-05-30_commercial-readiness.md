# Commercial Readiness Sprint — Implementation Plan

**Goal:** Transform Patent Pulse from a data-sparse prototype into a
commercially viable product with inline images, full abstracts,
working citations, and complete patent detail pages.

**Architecture:** 5 sequential phases. Each builds on the previous.
No overlapping dependencies — each phase is independently verifiable.

---

## Phase 1 — USPTO Images Inline

### Why this first
This is the single highest-impact visual change. Every patent card and
detail page gains a thumbnail. The "patent intelligence with the
receipts" promise becomes visually true.

### Approach
- Create `patent_assets` table (image metadata, not binary blobs)
- Fetch image URLs from USPTO API (public domain — 17 USC §105)
- Store URLs + metadata, render as `<img>` tags
- Cache layer: fetch once, serve cached URLs
- Frontend: thumbnail on PatentCard, image gallery on detail page

### Files
| File | Action |
|---|---|
| `backend/alembic/versions/0023_add_patent_assets.py` | Create |
| `backend/app/core/models.py` | +PatentAsset model |
| `backend/app/patent_sources/uspto_image_provider.py` | Create |
| `backend/app/tasks/fetch_images.py` | Create |
| `frontend/src/components/patents/PatentCard.tsx` | +thumbnail |
| `frontend/src/app/(app)/patents/[id]/page.tsx` | +image gallery |

### Acceptance
- USPTO patent cards show thumbnails
- Patent detail page shows image gallery
- Graceful fallback when no images available
- AGENTS.md updated: USPTO images exempt from link-only rule

---

## Phase 2 — USPTO Bulk Abstract Import

### Why this second
Abstract coverage is 13%. Most patents look empty. A bulk import
from USPTO Open Data takes it to 80%+ instantly.

### Approach
- Download USPTO weekly bulk XML/JSON (public domain)
- Parse abstracts, claims, and descriptions
- Batch upsert into patent_publications
- Mark source = 'uspto_bulk'
- Prioritize by opportunity_score (high-value patents first)

### Files
| File | Action |
|---|---|
| `backend/app/patent_sources/uspto_bulk_provider.py` | Create |
| `backend/app/tasks/import_uspto_bulk.py` | Create |
| `backend/scripts/download_uspto_bulk.py` | Create |

### Acceptance
- Abstract coverage > 50%
- Claims coverage > 20%
- Source provenance = 'uspto_bulk'

---

## Phase 3 — Fix Forward Citations

### Why this third
Citations are stuck at 22. The patent_client SDK can't establish a
USPTO API session. Debug the auth flow and fix it.

### Approach
- Check patent_client SDK version and USPTO API changes
- Test direct USPTO API calls to isolate SDK vs API issue
- Fix SDK auth or switch to alternative USPTO API endpoint
- Verify citation backfill produces results

### Acceptance
- Forward citations > 500
- Backfill task produces non-zero results

---

## Phase 4 — Fix Family Members

### Why this fourth
Family IDs are populated (759) but the family_members list is empty.
The EPO family endpoint parser has the same exchange-document wrapping
bug that was fixed for publications in Round 1.

### Approach
- Re-read EPO family endpoint response structure
- Apply same list-wrapping fix from Round 1 epo_client.py
- Extract family member publication numbers
- Backfill from stored raw_data (no API calls needed)

### Acceptance
- Family members > 500 patents
- Family tab on detail page shows real members

---

## Phase 5 — WIPO Historical Backfill

### Why this last
WIPO has 50 title-only records. A backfill of 2,000+ enriched records
proves global coverage and makes WIPO patents useful.

### Approach
- Run day-by-day BigQuery queries under 100GB budget
- Use per-day iteration from Round 2
- CLI script with resume capability
- Record all fetches to source_fetches

### Acceptance
- WIPO count > 2,000
- WIPO patents have titles + publication dates
- Source fetches populated

---

## Verification per phase

Each phase ends with:
- Pytest: 341 passed, 3 xfailed, 0 failed (or increasing)
- Data-health delta numbers
- Frontend build clean
- AGENTS.md grep: zero forbidden phrases in changed files
