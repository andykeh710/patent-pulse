# Production Runbook

**Last updated:** 2026-06-22
**App:** Invention Index 8 (Patent Pulse)
**Release branch:** `release/revamp-launch-validation`

---

## ⚠️ Important: Production Docker Compose

The production server has a LOCAL-MODIFIED `docker-compose.yml`. This file differs from the repo version. It contains production-specific port bindings, volume mounts, env vars, and secrets.

**Do NOT overwrite it with the repo version.** The repo `docker-compose.yml` is a development template. When adding new env vars (like `USPTO_ODP_BASE_URL`), add them manually to the production compose file — do not replace the entire file.

```bash
# On the production server:
ls -la docker-compose.yml docker-compose.prod.yml
# docker-compose.yml: production-local (DO NOT OVERWRITE)
# docker-compose.prod.yml: optional overrides
```

---

## Deployment Steps

```bash
# 1. SSH to production
ssh user@production-host
cd /opt/invention-index-8

# 2. Verify current state
git branch                    # should be release/revamp-launch-validation
git status                    # should be clean (except docker-compose.yml)
git log -1 --oneline          # note current HEAD

# 3. Fetch and pull release
git fetch origin release/revamp-launch-validation
git pull origin release/revamp-launch-validation
git log -1 --oneline          # verify new HEAD

# 4. Rebuild images
docker compose build backend worker beat frontend

# 5. Restart services (one at a time for zero-downtime)
docker compose up -d --force-recreate db redis
sleep 5
docker compose up -d --force-recreate backend
sleep 5
docker compose up -d --force-recreate worker beat
docker compose up -d --force-recreate frontend

# 6. Run migrations
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
# Expected: 0037 (head)

# 7. Verify services
docker compose ps
# All services should be Up (healthy)
```

---

## Health Verification

```bash
# Quick health check
curl -s http://localhost:8080/health | python3 -m json.tool

# Expected:
#   "db": "ok"
#   "redis": "ok"
#   "resend": "ok"
#   "alembic_head": "0037"
#   "overall": "ok"

# Freshness check
curl -s http://localhost:8080/api/v1/patents/freshness | python3 -m json.tool

# Expected fields:
#   "last_ingestion_status": "degraded" or "success"
#   "total_patents": ≥ 64231
#   "latest_patent_publication_date": "2026-05-28" or later
```

---

## Post-Deploy Verification (every deploy)

```bash
# All-in-one verification
curl -s http://localhost:8080/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('HEALTH OK' if d['overall']=='ok' else f'HEALTH FAIL: {d}')"
curl -s http://localhost:8080/api/v1/patents/freshness | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'FRESH: {d[\"last_ingestion_status\"]} pats={d[\"total_patents\"]}')"
curl -s -o /dev/null -w "SOURCE-HEALTH: HTTP %{http_code}\n" http://localhost:8080/api/v1/admin/source-health
curl -s -o /dev/null -w "FRONTEND: HTTP %{http_code}\n" http://localhost:3000/today
```

Expected:
```
HEALTH OK
FRESH: degraded pats=64231  (or success if USPTO recovered)
SOURCE-HEALTH: HTTP 401     (auth-gated)
FRONTEND: HTTP 200
```

---

## Rollback

```bash
# 1. Identify the last known-good commit
git log -5 --oneline

# 2. Reset to that commit
git reset --hard <known-good-commit-hash>

# 3. Rebuild and restart
docker compose build backend worker beat frontend
docker compose up -d --force-recreate backend worker beat frontend

# 4. Re-verify
curl -s http://localhost:8080/health
```

---

## USPTO Recovery (when sources come back online)

```bash
# 1. Test single week
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.ingest_uspto_bulk.ingest_grant_week \
  --kwargs='{"issue_date":"2026-06-16"}'

# 2. Check source_fetches
docker compose exec db psql -U patent -d patent_pulse -c \
  "SELECT provider, status, records_found FROM source_fetches WHERE office='USPTO' ORDER BY started_at DESC LIMIT 4;"

# 3. If successful, run full catch-up
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.ingest_uspto_bulk.catch_up_weeks \
  --kwargs='{"start_date":"2026-05-29","end_date":"2026-06-19"}'

# 4. Verify
docker compose exec db psql -U patent -d patent_pulse -c \
  "SELECT COUNT(*), MAX(publication_date) FROM patent_publications;"
```

---

## Common Issues

| Issue | Fix |
|-------|-----|
| `resend: unauthorized` after deploy | Verify `RESEND_API_KEY` in production env. Health check needs `User-Agent: InventionIndex8/1.0` |
| `alembic_head: (none)` | Run `docker compose exec backend alembic upgrade head` |
| Worker not processing tasks | Check `docker compose logs worker` for import errors. Rebuild with `docker compose build --no-cache worker` |
| Frontend returns 500 | Check `docker compose logs frontend`. Clear `.next` cache and rebuild: `rm -rf frontend/.next && docker compose build --no-cache frontend` |
