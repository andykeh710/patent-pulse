# Database Restore Runbook

## Restore from latest backup

### If backups are on S3 (Hetzner Object Storage / AWS / Backblaze)

1. Download the latest backup:
   ```bash
   aws s3 cp s3://patent-pulse-backups/daily/patent_pulse_2026-06-03_030000.sql.gz /tmp/restore.sql.gz
   ```

2. Gunzip:
   ```bash
   gunzip /tmp/restore.sql.gz
   ```

3. Drop and recreate the database:
   ```bash
   docker compose exec db psql -U patent -c "DROP DATABASE IF EXISTS patent_pulse_restore"
   docker compose exec db psql -U patent -c "CREATE DATABASE patent_pulse_restore"
   ```

4. Restore:
   ```bash
   docker cp /tmp/restore.sql invention-index-8-db-1:/tmp/restore.sql
   docker compose exec db psql -U patent -d patent_pulse_restore -f /tmp/restore.sql
   ```

5. Verify row counts:
   ```bash
   docker compose exec backend python -c "
   import asyncio
   from app.database import async_session_maker
   from sqlalchemy import text
   async def c():
       async with async_session_maker() as s:
           r = await s.execute(text('SELECT COUNT(*) FROM patent_publications'))
           print(f'Restored patents: {r.scalar()}')
   asyncio.run(c())
   "
   ```

6. If counts match production, promote the restore DB:
   ```bash
   docker compose exec db psql -U patent -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='patent_pulse'"
   docker compose exec db psql -U patent -c "DROP DATABASE patent_pulse"
   docker compose exec db psql -U patent -c "ALTER DATABASE patent_pulse_restore RENAME TO patent_pulse"
   ```

### If backups are only local (no S3)

Look in `/tmp/backups/` inside the backend container:

```bash
docker compose exec backend ls -la /tmp/backups/
```

The backup task creates `patent_pulse_YYYY-MM-DD_HHMMSS.sql.gz` files.

## Manual backup

To trigger a backup immediately:
```bash
docker compose exec backend python -c "
from app.tasks.backup import backup_database_daily
result = backup_database_daily()
print(result)
"
```

## Retention policy

- Daily backups: kept for 30 days
- Weekly backups (Sundays): manually retained (not yet automated)
- Monthly backups (1st of month): manually retained (not yet automated)
