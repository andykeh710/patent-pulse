# Patent-Pulse Operations

## Backup

### Create a backup
```bash
make backup
```

This produces:
- `backups/pp_YYYYMMDD.dump` — compressed PostgreSQL dump (custom format)
- `backups/figures_YYYYMMDD/` — patent figure files from `/data/figures`

### Restore from backup

```bash
# 1. Stop the application (keeps DB + volumes)
docker compose down

# 2. Start only the database
docker compose up -d db
sleep 3

# 3. Drop and recreate the database
docker compose exec db dropdb -U patent --if-exists patent_pulse
docker compose exec db createdb -U patent patent_pulse

# 4. Restore
docker compose exec -T db pg_restore -U patent -d patent_pulse < backups/pp_YYYYMMDD.dump

# 5. Run migrations to ensure schema is current
docker compose exec backend alembic upgrade head

# 6. Restore figures (if any)
docker compose cp backups/figures_YYYYMMDD/. backend:/data/figures/

# 7. Start all services
docker compose up -d

# 8. Verify
docker compose exec backend curl -sf http://localhost:8000/health
docker compose exec db psql -U patent -d patent_pulse -c "SELECT count(*) FROM patent_publications;"
```

### Verify a backup without restoring
```bash
# List contents
docker compose exec -T db pg_restore --list < backups/pp_YYYYMMDD.dump | head -30

# Restore into a throwaway DB for verification
docker compose exec db createdb -U patent pp_verify
docker compose exec -T db pg_restore -U patent -d pp_verify < backups/pp_YYYYMMDD.dump
docker compose exec db psql -U patent -d pp_verify -c "SELECT count(*) FROM patent_publications;"
docker compose exec db dropdb -U patent pp_verify
```

## Cold Start

From a completely fresh clone with no Docker volumes:

```bash
# 1. Copy .env.example to .env and fill in secrets
cp backend/.env.example .env
# Edit .env — set DEEPSEEK_API_KEY, USPTO_API_KEY, GOOGLE_APPLICATION_CREDENTIALS_HOST, etc.

# 2. Build and start
docker compose up -d --build

# 3. Run migrations
docker compose exec backend alembic upgrade head

# 4. Verify
docker compose exec backend curl -sf http://localhost:8000/health
# → {"db":"ok","redis":"ok","alembic_head":"0039","overall":"ok"}

# 5. Restore from backup (if restoring existing data)
make restore BACKUP=backups/pp_YYYYMMDD.dump
```

## Ingestion

```bash
# Run a 7-day catch-up ingestion
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.ingest_daily.run_catch_up_ingestion \
  --kwargs '{"lookback_days": 7}'

# Monitor progress
docker compose logs -f worker | grep -E "ingest|BigQuery|USPTO|complete"
```

## Health Monitoring

```bash
# API health
curl http://localhost:8080/health

# Source health
curl http://localhost:8080/api/v1/admin/source-health

# Data freshness
curl http://localhost:8080/api/v1/patents/freshness
```
