# V3 Stabilization Punch List

**Date:** 2026-06-19
**Release head:** `b4ccea1`
**Validation:** HEALTH=ok, ALEMBIC=0037, FRESHNESS=degraded, PATENTS=64231

## A. Must-Fix Before Production Launch

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| A1 | USPTO ingestion blocked — DB frozen at 2026-05-28 | CRITICAL | Wait for USPTO bulkdata/ODP recovery, then run `catch_up_weeks` |
| A2 | Resend email in production | HIGH | Configure production Resend API key with `full_access` scope |
| A3 | Auth/login must work without backend log extraction | HIGH | Resend email delivery required in production |

## B. Should-Fix Soon

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| B1 | "Personalize your briefing" empty state shows below ForYouFeed | MEDIUM | Guard: show only when BOTH legacy + V3.2 feed sections are empty |
| B2 | Company Geography shows "Unknown" + map placeholder with 0% coverage | MEDIUM | Hide section when country coverage is 0% |
| B3 | HTML double-escaping in company names (`KALTENBACH &AMP;AMP; VOIGT`) | LOW | Unescape or fix data source encoding |
| B4 | CSS class typos (`bg-bg-[var(...)]`) in 8+ files | LOW | Find-and-replace sweep |
| B5 | ForYouCard action buttons small on mobile | LOW | Increase touch target size |
| B6 | Trends page duplicate CPC/top-patent entries | LOW | Add dedup logic |

## C. Known External Blockers

| # | Issue | Status |
|---|-------|--------|
| C1 | USPTO bulkdata DNS failure — `bulkdata.uspto.gov` unresolvable globally | Awaiting recovery |
| C2 | USPTO ODP/IBD API HTTP 503 — all endpoints down | Awaiting recovery |
| C3 | BigQuery `patents-public-data` stale since 2026-04-21 | Not suitable as primary |
| C4 | PatentsView API blocked by Cloudflare (HTML instead of JSON) | No known workaround |

**When any source recovers**, run the USPTO Source Recovery Playbook (below).

## D. Deferred to V3.5 / V4

| # | Issue | Rationale |
|---|-------|-----------|
| D1 | Assignee `entity_type` enrichment (0% coverage) | Requires PatentsView or similar external data source |
| D2 | Deeper company intelligence (filing velocity, competitor comparison) | V3.3 Watchlist scope |
| D3 | Source health dashboard (admin view of all source_fetches) | V3.5 admin tools |
| D4 | Ingestion admin console (manual trigger, backfill UI) | V3.5 admin tools |
| D5 | Major UX/UI overhaul | Separate design sprint |
| D6 | `patent_client` library — permanently replaced by BigQuery + ODP | No action needed |

## Bug Count by Severity

| Severity | Count | Items |
|----------|-------|-------|
| CRITICAL | 1 | A1 (USPTO ingestion) |
| HIGH | 2 | A2, A3 (email auth in prod) |
| MEDIUM | 2 | B1, B2 |
| LOW | 4 | B3, B4, B5, B6 |
| EXTERNAL | 4 | C1-C4 |
| DEFERRED | 6 | D1-D6 |

## USPTO Source Recovery Playbook

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

## Production Safe?

**Yes** — code is stable, honest, deployable. Data staleness is an external blocker (USPTO sources unavailable), not a code bug. The product correctly reports `degraded` status instead of false `success`.
