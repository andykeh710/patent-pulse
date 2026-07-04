# Ops Tickets — Post-Sprint 1.5 (Andy Actions)

**Date:** 2026-06-14
**Author:** Hermes Agent
**Status:** Pending Andy

---

## OPS-01: Run Assignee Backfill on Production

**Priority:** P1 (blocks Companies page enrichment)
**Dependencies:** Sprint 1.5 auth changes deployed

### Context
The `assignees` normalization table has 0 rows on production. All Companies page entity_type/coverage data is empty. The backfill task exists, is tested, and is scheduled daily at 04:00 UTC, but may never have run the initial one-shot.

### Procedure

**Option A — Admin endpoint (recommended for first run):**

1. Log into production as an admin user and get your auth cookie.
2. Trigger the backfill:
```bash
curl -X POST https://inventionindex8.com/api/v1/admin/trigger-assignee-backfill \
  -H "Cookie: auth_session=<your-admin-jwt>"
```
3. Verify immediately:
```bash
# Check row counts via psql or admin endpoint
ssh root@188.245.85.248 \
  "docker compose -f /opt/invention-index-8/docker-compose.yml exec -T db \
   psql -U patent -d patent_pulse -c 'SELECT COUNT(*) FROM assignees;'"
```
Expected: ~16,723 rows.

**Option B — Verify Celery beat already ran:**

1. Check Celery beat logs:
```bash
ssh root@188.245.85.248 \
  "docker compose -f /opt/invention-index-8/docker-compose.yml logs beat | grep -i 'assignee backfill'"
```
2. If it ran, check row count as above.

### Verification Checklist
- [ ] `SELECT COUNT(*) FROM assignees` returns ~16,723
- [ ] `SELECT entity_type, COUNT(*) FROM assignees GROUP BY entity_type` shows corporation/university/gov breakdown
- [ ] Companies page `/companies` shows entity_type badges instead of "Enrichment pending"
- [ ] Entity Type Coverage bar shows ~90% (not "0 of 16,723")

### Rollback
Not needed — the backfill is idempotent (`ON CONFLICT DO UPDATE`). Re-running is safe.

---

## OPS-02: Rotate Production Postgres Password

**Priority:** P1 (security — default password is `secret`)
**Dependencies:** None (no code changes needed)

### Context
`docker-compose.yml` uses `${POSTGRES_PASSWORD:-secret}`. If `POSTGRES_PASSWORD` is not set in `/opt/invention-index-8/.env`, the database password is literally `secret`. This was exploitable before port binding was fixed to 127.0.0.1 (Sprint 1 security fix). Still a bad practice.

### Procedure — DO NOT RECREATE THE DATABASE VOLUME

The `pgdata` volume contains all production data. Recreating it requires a verified backup/restore plan. Instead, use `ALTER USER`:

1. **SSH to production:**
```bash
ssh root@188.245.85.248
```

2. **Check current password state:**
```bash
# Is it set?
grep POSTGRES_PASSWORD /opt/invention-index-8/.env
# If missing or =secret, continue.
```

3. **Generate strong password:**
```bash
NEW_PASSWORD=$(openssl rand -base64 32)
echo "New password: $NEW_PASSWORD"
# Save securely - this is the only time it will be visible
```

4. **Update the Postgres user password (without recreating volume):**
```bash
docker compose -f /opt/invention-index-8/docker-compose.yml exec db \
  psql -U patent -d patent_pulse \
  -c "ALTER USER patent WITH PASSWORD '$NEW_PASSWORD';"
```
Note: The current connection uses the old password. This is fine — `ALTER USER` takes effect on next authentication.

5. **Update .env:**
```bash
cd /opt/invention-index-8
# Backup current .env
cp .env .env.bak.$(date +%Y%m%d)
# Update POSTGRES_PASSWORD
sed -i '' "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASSWORD/" .env
# Or add if not present:
# echo "POSTGRES_PASSWORD=$NEW_PASSWORD" >> .env
```

6. **Restart dependent services (backend, worker, beat):**
```bash
docker compose restart backend worker beat
```

7. **Verify connectivity:**
```bash
# Check backend health
curl https://inventionindex8.com/health
# Should return {"status": "ok", "database": "ok"}
docker compose logs backend | tail -20
# Look for successful DB connection
docker compose logs worker | tail -10
# Worker should reconnect
```

8. **Verify from outside (belt-and-suspenders):**
```bash
# From your local machine:
nc -vz 188.245.85.248 5432
# Should FAIL — port is bound to 127.0.0.1 only
# If it connects, the port binding fix didn't deploy — block with ufw immediately
```

### Rollback
```bash
# Restore old .env
cp .env.bak.$(date +%Y%m%d) .env
# Revert password
docker compose exec db psql -U patent -d patent_pulse \
  -c "ALTER USER patent WITH PASSWORD 'secret';"
# Restart services
docker compose restart backend worker beat
```

### Post-Rotation
- [ ] Store the new password in your password manager
- [ ] Remove `$NEW_PASSWORD` from shell history: `history -d $(history | tail -2 | head -1 | awk '{print $1}')`
- [ ] Document rotation date in ops runbook
- [ ] Schedule next rotation: +90 days (2026-09-12)
