# Production Smoke Checklist

Run this after EVERY deploy to `release/revamp-launch-validation`.

**Date:** 2026-06-19
**Commit:** `683d393`

## 1. Health Endpoint

```bash
curl -s https://<prod>/health | python3 -m json.tool
```

| Check | Expected |
|-------|----------|
| `overall` | `ok` |
| `db` | `ok` |
| `redis` | `ok` |
| `resend` | `ok` (production) or `dev_preview` (local) |
| `alembic_head` | `0037` |

## 2. Freshness Endpoint

```bash
curl -s https://<prod>/api/v1/patents/freshness | python3 -m json.tool
```

| Check | Expected |
|-------|----------|
| `last_ingestion_status` | `degraded` (USPTO sources down) or `success` (sources up) |
| `total_patients` | ≥ 64231 |
| `latest_patent_publication_date` | `2026-05-28` or later |

## 3. Auth — Magic Link

```bash
# 1. Request link
curl -s -X POST https://<prod>/api/v1/auth/request-link \
  -H 'Content-Type: application/json' \
  -d '{"email":"andy.keh@gmail.com"}'

# 2. Check email for magic link (production) or backend logs (dev)
# 3. Open link in browser
# 4. Verify: lands on /today or /onboarding
# 5. Refresh: still authenticated
```

## 4. Admin — Source Health

```bash
# Unauth: should 401
curl -s -o /dev/null -w "%{http_code}" https://<prod>/api/v1/admin/source-health

# Auth: should return JSON with providers array
# (test in browser with admin account)
```

| Check | Expected |
|-------|----------|
| Unauth | HTTP 401 |
| Auth (admin) | 200, JSON with `providers` array |
| Auth (non-admin) | 403 or empty |

## 5. Frontend Routes

| Route | Expected |
|-------|----------|
| `/today` | 200, ForYouFeed renders |
| `/patents` | 200, patent list loads |
| `/companies` | 200, no fake badges |
| `/themes` | 200, patent counts > 0 |
| `/topics` | 301 → `/themes` |
| `/expiry` | 200, expiry list |
| `/opportunity` | 200, opportunities load |
| `/trends` | 200, trend data renders |
| `/watchlist` | 200, auth-gated |
| `/search` | 200 |
| `/account/preferences` | 200, preferences load |
| `/admin/source-health` | 200 (admin only) |
| `/login` | 200, shows sign-in form |
| `/login/verify?token=bad` | 200, shows error |

## 6. Services

```bash
docker compose ps
```

| Service | Expected |
|---------|----------|
| backend | Up (healthy) |
| db | Up (healthy) |
| redis | Up (healthy) |
| frontend | Up |
| worker | Up (healthy) |
| beat | Up |

## 7. Celery Tasks

```bash
docker compose exec worker celery -A app.tasks.celery_app inspect registered | grep ingest
```

Expected: `ingest_daily`, `ingest_uspto_bulk`, `ingest_bigquery` tasks registered.

## 8. DB State

```sql
SELECT COUNT(*), MAX(publication_date) FROM patent_publications;
SELECT status, COUNT(*) FROM ingestion_runs GROUP BY status;
SELECT provider, status, COUNT(*) FROM source_fetches GROUP BY provider, status;
```

## Quick-Run (all-in-one)

```bash
curl -s https://<prod>/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK' if d['overall']=='ok' else f'FAIL: {d}')"
curl -s https://<prod>/api/v1/patents/freshness | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'patents={d[\"total_patents\"]}, latest={d[\"latest_patent_publication_date\"]}, status={d[\"last_ingestion_status\"]}')"
curl -s -o /dev/null -w "source-health auth: HTTP %{http_code}\n" https://<prod>/api/v1/admin/source-health
```

## Sign-Off

| Date | Deployer | All checks pass? | Notes |
|------|----------|-----------------|-------|
| | | | |
