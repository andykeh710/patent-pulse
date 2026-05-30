# Global Patent Data Acquisition + Image Enrichment Sprint

**Status:** Mandated 2026-05-30. Hermes prompt sent.
**Pauses:** Landing page work (`.hermes/plans/2026-05-29_landing-page-design.md`) deferred until data is healthy.

## Mandate

V1 must support **USPTO + EPO + WIPO/PCT** coverage, patent images/drawings, abstracts/claims enrichment, family/citation data, and source-confidence indicators. Not give up on EPO or WIPO.

## Data audit that triggered this (2026-05-30)

| Field | Count | Coverage |
|---|---|---|
| USPTO patents | 62,968 | — |
| EPO patents | 0 | 0% |
| WIPO patents | 0 | 0% |
| Abstracts | 7,671 | 12% |
| Claims text | 934 | 1.5% |
| Figure links | 50,678 | 80% |
| Embeddings | 17,045 | 27% |
| Forward citations | 22 | 0.03% |
| Backward citations | 0 | 0% |
| Family members | 0 | 0% |
| Tags | 0 | 0% (tag task fails 100/100) |
| Opportunity score | 62,968 | 100% |

## Diagnosed root causes (before sprint started)

| Issue | Root cause |
|---|---|
| Abstract/claims gap | Beat sched too slow (Sat 8pm, batch=200); USPTO client hardcodes None for these fields |
| EPO 0 rows | Task auths OK but `processed=0` — query/date/parser bug |
| WIPO 0 rows | PATENTSCOPE search.jsf returning 403 Forbidden (no official query path used) |
| Citation backfill stuck at 22 | Task fires every 5 min but produces nothing — silent error |
| Tags 0 | tag.py:84 errors — every batch is 100/100 failure |
| Family 0 | Unknown — needs investigation |

## Source strategy (layered providers)

### Layer 1 — Official APIs/feeds
- **USPTO**: grants, applications, images, full text, expiry/maintenance
- **EPO OPS**: bibliographic, abstracts, full text where available, images, legal status, family, citations
- **WIPO**: PATENTSCOPE-accessible routes, WIPO API Catalog if applicable

### Layer 2 — Aggregators / public datasets
- Google Patents
- Google Patents BigQuery
- Lens (later)
- IFI / PatBase (later, if revenue supports)

### Layer 3 — ScrapeGraphAI extraction (controlled fallback)
- WIPO record pages
- Espacenet public pages if OPS misses fields
- Google Patents pages
- Patent drawing/image extraction
- Future: commercial usage signal evidence

## New architecture

```
backend/app/patent_sources/
  __init__.py
  base.py
  registry.py
  uspto_provider.py
  epo_ops_provider.py
  wipo_provider.py
  google_patents_provider.py
  scrapegraph_provider.py
  models.py
```

Provider interface:
- `search_by_publication_date(date)`
- `fetch_by_publication_number(pub_no)`
- `fetch_full_text(pub_no)`
- `fetch_images(pub_no)`
- `fetch_family(pub_no)`
- `fetch_citations(pub_no)`

Every field includes: `value`, `source`, `source_url`, `confidence`, `retrieved_at`, `raw_ref`.

## New tables

### `source_fetches` (instrumentation)
- id, provider, office, target_type, target_id, source_url
- status (success | failed | blocked | empty | partial)
- http_status, error_message, records_found, raw_storage_key
- started_at, completed_at, duration_ms, retry_count, created_at

### `patent_assets` (images as first-class data)
- id, patent_publication_id
- asset_type (thumbnail | drawing | figure | first_page | pdf | screenshot)
- source (uspto | epo_ops | wipo | google_patents | scrapegraph)
- source_url, storage_key, mime_type, page_number, figure_label, width, height, checksum
- status (pending | cached | remote_only | failed | unavailable)
- error_message, created_at, updated_at

## Execution order (10 steps)

| Step | What |
|---|---|
| D0 | Source fetch instrumentation + data-health visibility |
| D1 | EPO known-record fix → 1 EP record → 10 → 1 week → 4 weeks |
| D2 | WIPO provider with ScrapeGraphAI fallback ladder → 1 WO → 10 → 100 |
| D3 | Images MVP — show `figure_page_url` thumbnails first, then cache assets |
| D4 | Fix tag task (tag.py:84 100/100 failure) |
| D5 | Abstract/claims enrichment cadence + provider fallback |
| D6 | Family/citation repair (forward, backward, family_members, family_id) |
| — | Verification: EPO > 0, WIPO > 0, images visible, tag batch succeeds, data-health page live |

## Data-health targets for V1

| Metric | Target |
|---|---|
| USPTO records | 63K+ (existing) |
| EPO records | 5K+ or 8 weeks |
| WIPO/PCT records | 2K+ or 8 weeks |
| Images / figure fallback | 70%+ of patent cards |
| Abstracts | 60%+ of high-priority patents |
| Claims | 30%+ of high-priority patents |
| Tags | 80%+ of enriched patents |
| Embeddings | 80%+ of enriched patents |
| Families | 50%+ of high-priority patents |
| Citations | 50%+ of high-priority patents |

High-priority = expiring soon · high opportunity score · in user topics · in trend clusters · has figure link · recent grants/applications · selected for newsletters.

## New env vars

```
SCRAPEGRAPH_API_KEY
SCRAPEGRAPH_BASE_URL
SCRAPEGRAPH_ENABLED=true
SCRAPEGRAPH_MAX_CREDITS_PER_RUN
SCRAPEGRAPH_MAX_PAGES_PER_RUN
```

## What's deferred

- Landing page implementation
- Stripe products + dashboard setup
- Domain + hosting + deploy
- All other V1 ops items

These resume once the source acquisition layer is healthy and the data-health targets are within reach.

## References

- EPO OPS: https://www.epo.org/en/searching-for-patents/data/web-services/ops
- WIPO PATENTSCOPE: https://www.wipo.int/en/web/patentscope
- WIPO API Catalog: https://www.wipo.int/en/web/standards/ip-api-catalog/index
- ScrapeGraphAI: https://scrapegraphai.com/
- ScrapeGraphAI GitHub: https://github.com/ScrapeGraphAI/Scrapegraph-ai
