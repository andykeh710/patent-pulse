# V3.5 Source Health Admin Console

## Purpose

Operational layer for observing and retrying the patent ingestion pipeline.
Admin-only. Does not expose sensitive details to public users.

## Routes

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/admin/source-health` | GET | Admin | Aggregated source health dashboard |
| `/api/v1/admin/source-health` | GET | Admin | Provider status, freshness, source lag |
| `/api/v1/admin/source-fetches` | GET | Admin | Paginated fetch history (existing, enhanced) |
| `/api/v1/admin/ingestion/retry-grant-week` | POST | Admin | Dispatch `ingest_grant_week` Celery task |
| `/api/v1/admin/ingestion/retry-application-week` | POST | Admin | Dispatch `ingest_application_week` Celery task |
| `/api/v1/admin/ingestion/catch-up` | POST | Admin | Dispatch `catch_up_weeks` Celery task |

## Data Sources

- `source_fetches` table — per-fetch instrumentation logs
- `patent_publications` table — aggregate counts, latest publication date
- Celery task dispatch — reuses existing `ingest_uspto_bulk` tasks

## Retry Playbook

1. Navigate to `/admin/source-health`
2. Check Provider Status table — identify which provider is `failed`/`unavailable`
3. Check Source Lag — if >10d, data is stale
4. Use Manual Retry cards:
   - **Retry Grant Week**: enter Tuesday issue date (e.g., 2026-06-17)
   - **Retry Application Week**: enter Thursday publication date
   - **Catch Up Weeks**: for bulk backfill, enter start/end date range
5. After dispatch, note the task ID and monitor in `/admin/ai-runs` or Celery logs

## Production Validation Checklist

- [ ] Admin email is in `ADMIN_EMAILS` env var
- [ ] `/admin/source-health` loads without error
- [ ] Recent USPTO unavailable rows are visible in fetch history
- [ ] Freshness degraded status is consistent with source health
- [ ] Retry grant week dispatches Celery task (returns task_id)
- [ ] Non-admin users receive 403 on all admin endpoints

## Known Source Outage Behavior

- When USPTO Bulk Data API is unreachable: `source_fetches` logs `status="unavailable"` with HTTP error
- When USPTO returns empty week: `status="empty"` with records_found=0
- Source lag persists until USPTO publishes new weekly data (Tue/Thu)
- `bigquery` fallback provider may have older data than `uspto_bulkdata`

## Next Steps When USPTO Recovers

1. Check source-health dashboard — provider status should return to "success"
2. Run Catch Up for the outage period to backfill missed weeks
3. Verify `source_lag_days` returns to <7

## Files Changed

**Backend:**
- `backend/app/api/v1/admin.py` — Added `/source-health`, `/ingestion/retry-grant-week`, `/ingestion/retry-application-week`, `/ingestion/catch-up`

**Frontend:**
- `frontend/src/app/(app)/admin/source-health/page.tsx` — New admin dashboard page
- `frontend/src/app/(app)/NavSidebar.tsx` — Added "Source Health" nav link

**Tests:**
- `backend/tests/api/test_source_health.py` — Admin auth tests for new endpoints

## Remaining Risks

- Celery worker must be running for retry tasks to execute (existing infrastructure)
- No automated source health alerting (deferred to future sprint)
- No historical trend visualization for source health
- catch_up_weeks may be slow for large date ranges
