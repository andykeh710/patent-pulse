# Production Launch Runbook — Revamp Release

**Date:** 2026-06-15
**Branch:** release/revamp-launch-validation
**Target:** Invention Index 8 — Hetzner VPS — Docker Compose

---

## STOP CONDITIONS

Halt the launch and escalate if any of these occur:

- `pg_dump` backup fails or produces 0-byte file
- `alembic heads` returns more than one head (migration chain is branched)
- Production branch/commit is unexpected — do NOT force-push
- Any Docker service is unhealthy before deploy
- Admin auth is unavailable (can't log in as admin)
- `alembic upgrade head` fails with an error
- Backend fails to start after upgrade
- Any of these smoke checks fail: auth, Today, Search, Patent Detail, Companies, Expiry Radar, Watchlist
- Worker or beat are unhealthy after restart
- Postgres password rotation breaks backend connectivity

## Email / Resend Health (Non-Blocking)

The health endpoint probes `https://api.resend.com/domains` with the configured
API key. A 403 means the key is invalid or lacks domain permissions.
This is a configuration issue — not a code bug.

**If Resend shows `unauthorized` or `unreachable` on health:**
- Magic-link emails will not send. Users must use a pre-generated login link
  or manual invite.
- This is acceptable for a controlled launch where Andy provisions accounts.
- RESEND_API_KEY and EMAIL_FROM_ADDRESS must both be valid before
  enabling public self-serve signup.

**To fix Resend later:**
- Get a valid API key from https://resend.com/api-keys
- Verify the sending domain at https://resend.com/domains
- Set EMAIL_FROM_ADDRESS to a verified domain address
- Set RESEND_API_KEY to the new key in .env
- Restart backend: `docker compose up -d backend`

## .env Duplicate Key Cleanup

If `.env` contains duplicate keys (e.g. MAGIC_LINK_BASE_URL twice), the
last value wins per Pydantic BaseSettings behavior. Remove duplicates to
avoid ambiguity.

```bash
# Check for duplicates
cd /opt/invention-index-8
grep -n 'MAGIC_LINK_BASE_URL\|EMAIL_PRODUCTION_ACKNOWLEDGED\|EMAIL_SEND_MODE\|EMAIL_FROM_ADDRESS\|RESEND_API_KEY' .env

# Expected: each key appears exactly once
# If duplicates exist, edit .env and remove the earlier duplicate line,
# keeping only the last occurrence (the one that takes effect)
vi .env
```

---

## A. Pre-Deploy Verification (Andy to run on production)

```bash
# 1. Go to the right directory
cd /opt/invention-index-8

# 2. Confirm you're on the right server
hostname
# Expected: your Hetzner production hostname

# 3. Check current commit
git log --oneline -1
# Record this — you'll need it for rollback
# Example: 48354e3 fix(security): harden Postgres...

# 4. Record current migration
docker compose exec backend alembic current
# Record this output — expected: 0031_blog_posts or later
# If already at 0034, migrations are already applied — skip Section D

# 5. Check all services are up
docker compose ps
# Expected: db (healthy), redis (healthy), backend (Up), frontend (Up),
#           worker (Up), beat (Up), nginx (Up)

# 6. Verify admin account exists
# Log in to https://inventionindex.com as admin in your browser
# If admin login fails, STOP — fix auth before proceeding
```

---

## B. Backup (CRITICAL — RUN FIRST)

```bash
# Create backup directory
mkdir -p ~/backups

# Full database backup
docker compose exec db pg_dump -U patent patent_pulse > ~/backups/pre_revamp_$(date +%Y%m%d_%H%M).sql

# Verify backup is valid
ls -la ~/backups/pre_revamp_*.sql
# Expected: file > 0 bytes (several MB minimum for a real database)

# If file is 0 bytes, STOP — do not proceed
```

---

## C. Pull Release

```bash
cd /opt/invention-index-8

# Fetch the release branch
git fetch origin release/revamp-launch-validation

# Merge it
git merge origin/release/revamp-launch-validation

# Verify
git log --oneline -3
# Expected top commit: 6bed631 "launch-ops: production runbook..."

# If there are merge conflicts, STOP — resolve them first
```

---

## D. Apply Migrations

```bash
# Check what will be applied
docker compose exec backend alembic history -r current:heads
# Shows migrations 0032, 0033, 0034 (or fewer if some are already applied)

# Apply them
docker compose exec backend alembic upgrade head

# Expected output: "INFO  [alembic.runtime.migration] Running upgrade ... -> 0032"
#                    "INFO  [alembic.runtime.migration] Running upgrade 0032 -> 0033"
#                    "INFO  [alembic.runtime.migration] Running upgrade 0033 -> 0034"
# If any line says "FAILED" or shows an error, STOP

# Verify head
docker compose exec backend alembic current
# Expected: 0034_feedback_alert_intents

# Verify single head
docker compose exec backend alembic heads
# Expected: 0034 (single line, no branches)

# Verify new tables exist
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN ('feedback', 'alert_intents', 'saved_searches')
  ORDER BY table_name;
"
# Expected: 3 rows

# Verify today_seen_at columns on users table
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name = 'users'
    AND column_name IN ('last_today_seen_at', 'previous_today_seen_at');
"
# Expected: 2 rows, both type 'timestamp with time zone'
```

---

## E. Rebuild + Restart

```bash
# Rebuild only the changed services
docker compose build backend frontend

# Restart all services
docker compose up -d backend frontend worker beat nginx

# Wait for services to come up
sleep 10

# Check all services are healthy
docker compose ps
# Expected: all services Up or Up (healthy)

# Quick health check
curl -s http://localhost:8000/api/v1/health
# Expected: {"status":"healthy"}

curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200
```

---

## F. Post-Deploy Verification (Production)

```bash
# 1. Backend health
curl -s https://inventionindex.com/api/v1/health
# Expected: {"status":"healthy"}

# 2. Key pages respond with 200
for route in /today /search /patents /companies /expiry /watchlist; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://inventionindex.com$route")
  echo "$route → $code"
done
# Expected: all 200

# 3. Check logs for errors
docker compose logs backend --tail 20 | grep -i "error\|critical" || echo "No errors"
docker compose logs worker --tail 10
docker compose logs beat --tail 10

# 4. Verify Celery workers
docker compose exec worker celery -A app.tasks.celery_app inspect ping
# Expected: {"celery@...": {"ok": "pong"}}

# 5. Verify Celery beat schedule
docker compose logs beat --tail 5
# Expected: "beat: Starting..." or task entries visible
```

---

## G. Run Assignee Backfill

Two paths — pick one.

### Path 1: Admin endpoint (instant results)

```bash
# You need an admin session cookie. In your browser:
# 1. Log in as admin at https://inventionindex.com
# 2. Open DevTools → Application → Cookies → copy the session token

# Then run (replace <YOUR_COOKIE> with the actual cookie value):
curl -X POST https://inventionindex.com/api/v1/admin/trigger-assignee-backfill \
  -H "Cookie: <YOUR_COOKIE>" \
  -H "Content-Type: application/json"
# Expected: {"status": "accepted", "task_id": "..."}

# Wait 1-2 minutes, then verify
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT entity_type, COUNT(*) as cnt FROM assignees GROUP BY entity_type ORDER BY cnt DESC;
"
# Expected: rows like corporation/NNNN, university/NNN, etc.
# If empty, the backfill hasn't completed yet — wait and retry
```

### Path 2: Wait for Celery beat (passive)

The task `backfill-assignees-daily` runs at 04:00 UTC. To check if it ran:

```bash
docker compose logs worker --tail 50 | grep -i "backfill\|assignee"
# OR
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT COUNT(*) FROM assignees WHERE entity_type IS NOT NULL;
"
# Expected: > 0 after backfill runs
```

---

## H. Safe Postgres Password Rotation

**WARNING: Do NOT just change POSTGRES_PASSWORD in .env. This does not update the existing database user — it only changes what new containers would use. Existing containers keep their connections. After restart, they will use the new env var AND FAIL because the database user's password hasn't changed.**

### Correct process:

```bash
# 1. Generate a strong password (save the output)
openssl rand -base64 32
# Example output: g7Xp2Kq9mN3vR5sW8yB1dF4hJ6lZ0aC

# 2. Change the password IN the database
docker compose exec db psql -U patent -d patent_pulse -c "
  ALTER USER patent WITH PASSWORD 'g7Xp2Kq9mN3vR5sW8yB1dF4hJ6lZ0aC';
"
# Expected: ALTER ROLE

# 3. Verify the new password works
docker compose exec db psql -U patent -d patent_pulse -c "SELECT 1;"
# Expected: 1
# (This uses the docker network — password is not checked because
#  docker exec skips auth. Skip to step 4 for real verification.)

# 4. Update .env on the host
cd /opt/invention-index-8
# Edit .env:
#   POSTGRES_PASSWORD=g7Xp2Kq9mN3vR5sW8yB1dF4hJ6lZ0aC
# (Replace the old value — do not add a second line)

# 5. Restart only services that connect to the database
docker compose up -d backend worker beat

sleep 5

# 6. Verify backend can connect
curl -s https://inventionindex.com/api/v1/health
# Expected: {"status":"healthy"}

# 7. Verify Celery workers
docker compose exec worker celery -A app.tasks.celery_app inspect ping
# Expected: {"celery@...": {"ok": "pong"}}
```

### If connection fails after step 5 (rollback):

```bash
# Revert .env to the old password
# Then:
docker compose exec db psql -U patent -d patent_pulse -c "
  ALTER USER patent WITH PASSWORD '<OLD_PASSWORD>';
"
docker compose up -d backend worker beat
```

---

## I. Rollback Plan

**Preferred: code-only rollback.** Do not downgrade migrations if production data has been written to new tables (feedback, alert_intents, saved_searches, watchlist). The new tables are harmless if the code doesn't reference them.

```bash
cd /opt/invention-index-8

# 1. Revert code to previous production commit
git revert 6bed631 485617c --no-edit
# OR
git reset --hard <recorded-pre-deploy-commit-hash>

# 2. Rebuild + restart
docker compose build backend frontend
docker compose up -d backend frontend worker beat nginx

# 3. Verify
curl -s https://inventionindex.com/api/v1/health
# Expected: {"status":"healthy"}
```

**Only if migrations themselves caused the failure:** Use migration downgrade. This drops new tables/columns and LOSES any data written to them.

```bash
docker compose exec backend alembic downgrade 0031
# Drops: feedback, alert_intents tables
# Removes: last_today_seen_at, previous_today_seen_at columns
# Loses: all feedback, alert intent, saved search data
```

---

## J. Launch Metrics Queries

Run after 24 hours and daily for the first week:

```sql
-- Run via: docker compose exec db psql -U patent -d patent_pulse

-- Activation funnel
SELECT
  (SELECT COUNT(*) FROM users) AS total_users,
  (SELECT COUNT(*) FROM users WHERE last_today_seen_at IS NOT NULL) AS today_users,
  (SELECT COUNT(DISTINCT user_id) FROM watchlist) AS users_with_saves,
  (SELECT COUNT(DISTINCT user_id) FROM saved_searches) AS users_with_searches,
  (SELECT COUNT(DISTINCT user_id) FROM user_company_follows) AS users_following,
  (SELECT COUNT(DISTINCT user_id) FROM feedback) AS users_with_feedback;

-- Feedback breakdown
SELECT surface, rating, COUNT(*) FROM feedback
GROUP BY surface, rating ORDER BY surface, rating;

-- Assignee enrichment coverage
SELECT
  COUNT(*) AS total_assignees,
  COUNT(*) FILTER (WHERE entity_type IS NOT NULL) AS with_entity_type,
  COUNT(*) FILTER (WHERE country IS NOT NULL) AS with_country
FROM assignees;
```

---

## K. Andy Copy/Paste Launch Checklist

Run each block in order. Check expected output before proceeding.

### A. Pre-deploy

```bash
cd /opt/invention-index-8 && git log --oneline -1
docker compose exec backend alembic current
docker compose ps
```
→ Record commit + migration + service status. Admin login works? If any fail, STOP.

### B. Backup

```bash
mkdir -p ~/backups
docker compose exec db pg_dump -U patent patent_pulse > ~/backups/pre_revamp_$(date +%Y%m%d_%H%M).sql
ls -la ~/backups/pre_revamp_*.sql
```
→ File > 0 bytes? If 0, STOP.

### C. Pull + merge

```bash
cd /opt/invention-index-8
git fetch origin release/revamp-launch-validation
git merge origin/release/revamp-launch-validation
git log --oneline -3
```
→ Top commit is `6bed631`. If conflicts, STOP.

### D. Migrate

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec db psql -U patent -d patent_pulse -c "SELECT table_name FROM information_schema.tables WHERE table_name IN ('feedback','alert_intents','saved_searches');"
```
→ Head is 0034. 3 tables shown. If not, STOP.

### E. Rebuild + restart

```bash
docker compose build backend frontend
docker compose up -d backend frontend worker beat nginx
sleep 10
docker compose ps
```
→ All services Up. If any unhealthy, STOP.

### F. Verify

```bash
curl -s https://inventionindex.com/api/v1/health
docker compose logs backend --tail 20 | grep -i error || echo "No errors"
docker compose exec worker celery -A app.tasks.celery_app inspect ping
```
→ Health returns `{"status":"healthy"}`. No errors. Worker pongs.

### G. Backfill

```bash
# Option A: Admin endpoint (need admin cookie)
curl -X POST https://inventionindex.com/api/v1/admin/trigger-assignee-backfill -H "Cookie: <cookie>" -H "Content-Type: application/json"
# Option B: Check if Celery beat already ran it
docker compose exec db psql -U patent -d patent_pulse -c "SELECT entity_type, COUNT(*) FROM assignees GROUP BY entity_type;"
```
→ entity_type rows appear. If still empty after 5 minutes, retry admin endpoint.

### H. Password rotation (optional — can defer post-launch)

```bash
openssl rand -base64 32
docker compose exec db psql -U patent -d patent_pulse -c "ALTER USER patent WITH PASSWORD '<new_password>';"
# Edit /opt/invention-index-8/.env → POSTGRES_PASSWORD=<new_password>
docker compose up -d backend worker beat
curl -s https://inventionindex.com/api/v1/health
```
→ Health returns `{"status":"healthy"}`.

---

## L. Launch Blocker Summary

| Item | Status | Who |
|------|--------|-----|
| Release branch clean | ✅ | Hermes |
| Frontend baseline | ✅ | Hermes |
| Migration 0034 | ✅ | Hermes |
| Pre-deploy backup | ⬜ | Andy |
| Staging smoke test | ⬜ | Andy |
| Migration apply (prod) | ⬜ | Andy |
| Assignee backfill | ⬜ | Andy |
| Postgres password rotation | ⬜ | Andy |
| Celery beat verify | ⬜ | Andy |

**Proceed when:** backup exists, migrations applied, services healthy, backfill verified. Password rotation can be done post-launch if needed.
