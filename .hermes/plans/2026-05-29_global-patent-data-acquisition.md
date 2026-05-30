# Global Patent Data Acquisition Sprint — Implementation Plan

> **Goal:** V1 must support USPTO + EPO + WIPO/PCT, images/drawings,
> abstracts/claims enrichment, family/citation repair, and data-health
> visibility.

**Architecture:** 10 sequential steps. Each step has its own
verification block. Stop after each step for user review and commit.

---

## Step 1 — Source Fetch Instrumentation

### Files
| File | Action |
|---|---|
| `backend/alembic/versions/0021_add_source_fetches.py` | Create |
| `backend/app/core/models.py` | Modify — add SourceFetch model |
| `backend/app/ingestion/source_fetch.py` | Create — helper module |

### Migration
- Table: `source_fetches` with columns: id, provider, office, target_type,
  target_id, source_url, status, http_status, error_message,
  records_found, raw_storage_key, started_at, completed_at, duration_ms,
  retry_count, created_at

### Helper
- `record_source_fetch()` — context manager or decorator pattern
- Records start time, wraps fetch, records end time + status + counts

### Verification
- Migration applies cleanly
- Model importable
- `docker compose exec backend alembic current` shows 0021

---

## Step 2 — Admin Data-Health Endpoint + Page

### Files
| File | Action |
|---|---|
| `backend/app/api/v1/admin.py` | Modify — add GET /data-health and GET /source-fetches |
| `frontend/src/app/(app)/admin/data-health/page.tsx` | Create |

### Backend endpoints
- `GET /api/v1/admin/data-health` — aggregated counts by office, coverage
  percentages
- `GET /api/v1/admin/source-fetches?limit=20` — recent fetch log

### Frontend page
- `/admin/data-health` — grid of stat cards, recent fetch failures

### Verification
- Curl endpoint returns JSON
- Frontend page renders
- Backend tests pass

---

## Step 3 — Provider Architecture

### Files
| File | Action |
|---|---|
| `backend/app/patent_sources/__init__.py` | Create |
| `backend/app/patent_sources/base.py` | Create — abstract base provider |
| `backend/app/patent_sources/registry.py` | Create — provider registry |
| `backend/app/patent_sources/epo_ops_provider.py` | Create — wraps EPOClient |
| `backend/app/patent_sources/wipo_provider.py` | Create — wraps WIPOClient |
| `backend/app/patent_sources/google_patents_provider.py` | Create — wraps GooglePatentsClient |
| `backend/app/patent_sources/scrapegraph_provider.py` | Create — stub |

### Provider interface
- `fetch_by_publication_number()`
- `search_by_publication_date()`
- `fetch_full_text()`
- `fetch_images()`
- `fetch_family()`
- `fetch_citations()`

### Verification
- All providers importable
- Registry lists providers
- Existing EPO/WIPO/Google clients are wrapped, not rewritten

---

## Step 4 — Fix EPO Ingestion

### Diagnosis
- EPO task runs, credentials set, returns processed=0
- Likely: date format mismatch, empty search results, or silent 404

### Steps
1. Add source_fetch instrumentation to EPO client
2. Create `backend/scripts/test_epo_known_record.py`
3. Fetch one known EP publication (e.g. EP4000000A1) end-to-end
4. Inspect raw response and normalization
5. Fix query/date/parser issue
6. Insert one EP record
7. Run 10-record test
8. Run one-week EP ingest
9. Confirm EPO count > 0 in data-health

### Verification
- `test_epo_known_record.py` succeeds
- `ingest_weekly_epo` returns created > 0
- Data-health shows EPO count > 0

---

## Step 5 — WIPO Provider with ScrapeGraphAI Fallback

### Diagnosis
- WIPO PATENTSCOPE query returns 403

### Steps (ladder approach)
1. Try official PATENTSCOPE API/catalog route
2. Fetch known WO publication by number (e.g. WO2024001234)
3. If 403 persists, add ScrapeGraphAI extraction
4. Add env vars: SCRAPEGRAPH_API_KEY, SCRAPEGRAPH_ENABLED,
   SCRAPEGRAPH_MAX_CREDITS_PER_RUN, SCRAPEGRAPH_MAX_PAGES_PER_RUN
5. Implement ScrapeGraphAI extraction for WIPO result pages
6. Add Google Patents fallback for WO records

### Verification
- One WO record inserted end-to-end
- 10 WO records
- 100 WO records
- Data-health WIPO count > 0

---

## Step 6 — Images MVP

### Files
| File | Action |
|---|---|
| `backend/alembic/versions/0022_add_patent_assets.py` | Create |
| `backend/app/core/models.py` | Modify — add PatentAsset model |

### Steps
1. Create `patent_assets` table
2. Show existing `figure_page_url` thumbnail on patent cards (frontend)
3. Show images/drawings panel on patent detail page
4. Provider pipeline for fetching/caching images

### Verification
- Migration applies
- Figure page URLs visible in patent list
- Patent detail page shows images panel

---

## Step 7 — Fix Tags

### Diagnosis
- Tag task fails 100/100
- Issue around `backend/app/tasks/tag.py` line 84

### Investigation
- `_tag_patent_async` opens session, runs query, calls LLM, writes tags
- Fails likely from: DB connection, LLM error, or session issue
- Each patent gets its own `_tag_patent_async` call which opens a fresh session

### Steps
1. Run tag on a single patent manually
2. Inspect error
3. Fix root cause
4. 10-patent batch succeeds
5. 100-patent batch succeeds

### Verification
- `batch_tag_patents(10)` returns succeeded > 0
- `batch_tag_patents(100)` returns succeeded > 0
- Data-health tag coverage increases

---

## Step 8 — Abstract/Claims Enrichment

### Steps
1. Increase cadence/batch size for `enrich_abstracts` task
2. Prioritize high opportunity, expiring soon, topics, trends
3. Add provider fallback chain: USPTO → EPO → Google Patents → ScrapeGraph
4. Add "Limited source text available" UI label for title-only patents

### Verification
- Abstract coverage increases from 7,671
- Claims coverage increases from 934
- UI label visible on under-enriched patents

---

## Step 9 — Family/Citation Repair

### Diagnosis
- Forward citations stuck at 22, backward 0, family 0

### Steps
1. Verify `uspto_fetch_citations` is True
2. Run citation backfill manually on 10 patents
3. Fix EPO family resolution task
4. Provider fallback: EPO OPS → USPTO/Google → ScrapeGraph

### Verification
- Forward citations increase from 22
- Backward citations > 0
- Family resolution produces results

---

## Step 10 — Verification Targets

- EPO count > 0
- WIPO count > 0
- Image thumbnails visible
- Data-health page visible
- Tag batch 100 succeeds
- At least one EPO patent detail works
- At least one WIPO patent detail works
- Source_fetches shows successes and failures
- Backend tests pass: 341 passed, 3 xfailed, 0 failed
- Frontend build/typecheck passes
