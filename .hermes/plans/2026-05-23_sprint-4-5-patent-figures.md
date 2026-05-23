# Sprint 4.5 — Patent Figure Ingestion (Link-Out)

> **Scope reduced 2026-05-23.** Inline thumbnails blocked by Google Patents
> image URL hashes. Link-out only. See DEVIATION DETECTED in AGENTS.md.

## What Changed from ROADMAP

| Original | Actual |
|----------|--------|
| Inline `<img src>` thumbnails | Clickable "View Figures on Google Patents →" link |
| `figure_url` column | `figure_page_url` (links to Google Patents thumbnails page) |
| `figure_count` column | Dropped — requires scraping |
| Patent card inline thumbnail | Dropped — link-only |

## Implementation (single pass, no chunks)

1. **Migration 0010:** Add `figure_page_url` (varchar 512, nullable) to patent_publications.
2. **Model:** Add `figure_page_url` to PatentPublication ORM model.
3. **Ingestion:** Compute URL from `publication_number` + `office` prefix:
   `https://patents.google.com/patent/{office_prefix}{publication_number}/thumbnails`
4. **Backfill:** `backfill_figure_urls(limit, offset)` — idempotent.
5. **Frontend:** "View Figures on Google Patents →" styled link on patent detail page.
   Opens in new tab. "Image links provided by Google Patents — verify at source" attribution.
   Empty state: no link rendered when `figure_page_url` is null.
6. **AGENTS.md update:** Document link-out-only limitation for Sprint 6B awareness.
7. **Tests:** Verify URL populated, backfill idempotent, no image files added.

## Affects: Sprint 6B

News Feed cards must be text-forward with a "Figures →" link, not inline
thumbnails. No inline patent images are available without either scraping
(fragile) or a paid image API (post-V1).
