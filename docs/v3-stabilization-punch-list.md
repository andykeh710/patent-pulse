# V3 Stabilization Punch List

**Date:** 2026-06-19
**Release head:** `d36340c` (merged V3.2)
**Deployment:** Pushed to `release/revamp-launch-validation`, local validation passed

## Merged & Deployed

| PR | Title | Status |
|----|-------|--------|
| V3.0 | Boris stabilization | Merged |
| V3.1 | Preference Center + personalization model | Merged |
| V3.2 | Personalized Today + honest USPTO source degradation | Merged |

## Known Data Limitations

| Issue | Status |
|-------|--------|
| DB latest pub = 2026-05-28 | External blocker — USPTO sources (bulkdata DNS, ODP 503) unavailable |
| BigQuery stale since 2026-04-21 | Not suitable as primary source |
| `source_fetches` records source failures honestly | Working — 12+ unavailable rows |
| Freshness API reports `degraded` | Working |

## Known Bugs (V3)

| # | Bug | Severity | Status |
|---|-----|----------|--------|
| 1 | USPTO ingestion blocked — 0 new records since May 28 | HIGH | External blocker |
| 2 | HTML double-escaping in company names (`KALTENBACH &AMP;AMP; VOIGT`) | LOW | Not fixed |
| 3 | CSS class typos (`bg-bg-[var(...)]` in multiple files) | LOW | Partially fixed |
| 4 | Trends page duplicate entries in some CPC lists | LOW | Not investigated |
| 5 | `patent_client` library broken (USPTO Public Search 404) | DORMANT | Replaced by BigQuery + ODP architecture |
| 6 | `Assignee entity_type` enrichment — 0% coverage | MEDIUM | Requires source-backed enrichment (PatentsView or similar) |

## Remaining UX Issues

| Issue | Status |
|-------|--------|
| "Personalize your briefing" empty state shows below ForYouFeed | Redundant — should show only when BOTH old+new personalized sections are empty |
| Company Geography section shows "Unknown" / map placeholder | Honest but visually misleading — hide until real data exists |
| Resend email — `dev_preview` mode locally | Expected — needs production Resend key |
| Digest/alert email delivery not yet implemented | V3.3+ scope |
| ForYouCard action buttons small on mobile | Cosmetic |

## USPTO Source Recovery Playbook

When any USPTO source recovers:

```bash
# 1. Test single week
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.ingest_uspto_bulk.ingest_grant_week \
  --kwargs='{"issue_date":"2026-06-16"}'

# 2. Check source_fetches
docker compose exec db psql -U patent -d patent_pulse -c \
  "SELECT * FROM source_fetches WHERE office='USPTO' ORDER BY started_at DESC LIMIT 4;"

# 3. If successful, run full catch-up
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.ingest_uspto_bulk.catch_up_weeks \
  --kwargs='{"start_date":"2026-05-29","end_date":"2026-06-19"}'

# 4. Verify
docker compose exec db psql -U patent -d patent_pulse -c \
  "SELECT COUNT(*), MAX(publication_date) FROM patent_publications;"
```

## What Must Be Fixed Before V3 is "Complete"

| Item | Priority |
|------|----------|
| USPTO ingestion recovery (once sources available) | CRITICAL |
| Assignee entity_type enrichment | V3.5 or V4 — requires external data source |
| Double-escaped company names | LOW — cosmetic |
| CSS class typos cleanup | LOW — cosmetic |
| Trends deduplication | LOW |

## Ready for V4.0 Planning

YES — V3 code is stable, honest, and deployable. Data staleness is a known external blocker, not a code bug.
