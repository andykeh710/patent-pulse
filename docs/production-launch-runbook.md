# Production Launch Runbook — Revamp Release

**Date:** 2026-06-15
**Release branch:** `release/revamp-launch-validation`
**Target:** Invention Index 8 (Hetzner VPS, Docker Compose)

---

## A. Pre-Deploy Checklist (Before Any Changes)

Run these on production BEFORE deploying:

```bash
# 1. Confirm current state
cd /opt/invention-index-8
git log --oneline -1
# Expected: the current production commit

# 2. Backup database (critical — do not skip)
docker compose exec postgres pg_dump -U <user> invention_index > ~/backups/pre_revamp_$(date +%Y%m%d_%H%M).sql
ls -la ~/backups/pre_revamp_*.sql
# Expected: file exists, > 0 bytes

# 3. Current migration state
docker compose exec backend alembic current
# Expected: 0031_blog_posts (or whatever was last applied)

# 4. Service health
docker compose ps
# Expected: all services Up (healthy) or Up

# 5. Environment variables
cat /opt/invention-index-8/.env | wc -l
# Expected: .env file exists with all required vars

# 6. Admin user available
docker compose exec backend python -c "
from app.core.ai_models import User
from app.core.database import get_session
# Confirm at least one admin user exists
"
# OR: test with known admin credentials

# ----- STOP HERE if any check fails -----
```

---

## B. Deploy Steps (Production)

### B.1 Pull + merge

```bash
cd /opt/invention-index-8

# If release branch is separate from main:
git fetch origin release/revamp-launch-validation
git merge origin/release/revamp-launch-validation

# Or if merging into main:
git checkout main
git merge release/revamp-launch-validation

# Verify
git log --oneline -3
# Expected: 485617c "release-gate: migration 0034..."

# DO NOT proceed if merge conflicts
```

### B.2 Apply migrations

```bash
# Apply all pending migrations (0032, 0033, 0034)
docker compose exec backend alembic upgrade head

# Verify head
docker compose exec backend alembic current
# Expected: 0034_feedback_alert_intents

# Verify head
docker compose exec backend alembic heads
# Expected: 0034 (single head, no branches)
```

### B.3 Verify new tables exist

```bash
docker compose exec postgres psql -U <user> -d invention_index -c "\dt feedback alert_intents saved_searches"
# Expected: 3 tables listed

# Verify today_seen_at columns
docker compose exec postgres psql -U <user> -d invention_index -c "\d users" | grep today
# Expected: last_today_seen_at, previous_today_seen_at columns
```

### B.4 Rebuild + restart

```bash
docker compose build backend frontend
docker compose up -d backend frontend celery-worker celery-beat nginx

# Wait for healthy
sleep 10
docker compose ps
# Expected: all services Up
```

### B.5 Health checks

```bash
# Backend health
curl -s http://localhost:8000/api/v1/health
# Expected: {"status": "healthy"}

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200

# Nginx (external)
curl -s -o /dev/null -w "%{http_code}" https://inventionindex.com
# Expected: 200
```

---

## C. Staging Deployment (Andy to Execute)

If a staging environment exists, use the same steps as Section B on staging first.

### C.1 Staging migration verification

```bash
# On staging:
cd /opt/invention-index-staging  # or wherever staging lives
git pull origin release/revamp-launch-validation
docker compose exec backend alembic upgrade head

# Verify tables
docker compose exec postgres psql -U <user> -d invention_index -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_name IN ('feedback', 'alert_intents', 'saved_searches', 'watchlist')
  ORDER BY table_name;
"
# Expected: all 4 tables exist
```

### C.2 Staging smoke test checklist

Run each item. Record pass/fail.

```
Core functionality:
[ ] Homepage loads (https://staging.inventionindex.com → 200)
[ ] Login works
[ ] Today loads (no broken empty states)
[ ] Today mark-seen: open Today, check comparison label
[ ] Search: query "battery" → results appear
[ ] Search filters: set legal_status=GRANTED → FilterChips appear
[ ] Search sort: change to "Newest first" → results reorder
[ ] Saved searches: create, list, open, delete
[ ] Patent detail: click any result → page loads
[ ] Patent detail tabs: switch between Overview, Commercial, Claims
[ ] Save patent: click bookmark on patent card → appears in Watchlist
[ ] Save patent: click bookmark on patent detail → consistent state
[ ] Share/Copy link: click → URL copied
[ ] Company list: /companies → loads with data
[ ] Company detail: /companies/<name> → loads with portfolio, follow button
[ ] Follow company: click "Follow company" → toggles to "Following"
[ ] Expiry Radar: /expiry → loads with cards
[ ] Expiry Radar: horizon tabs switch days_ahead
[ ] Expiry Radar: FilterChips appear for active filters
[ ] Expiry Radar: save from card → appears in Watchlist
[ ] Expiry Radar: CSV export → downloads file
[ ] Watchlist: /watchlist → loads 3 tabs
[ ] Watchlist: Saved Patents tab shows saved patents
[ ] Watchlist: Followed Companies tab shows followed companies
[ ] Watchlist: Saved Searches tab shows saved searches
[ ] Feedback: thumbs up on Today → "Thanks" message
[ ] Alert intent: POST /api/v1/alert-intent → returns intent_captured
[ ] Activation state: GET /api/v1/activation-state → returns real values

Security:
[ ] Anonymous: GET /api/v1/admin/retention → 401/403
[ ] Normal user: GET /api/v1/admin/retention → 403
[ ] Admin user: GET /api/v1/admin/retention → 200 with metrics
[ ] Anonymous: GET /api/v1/feedback/admin → 401/403
[ ] Normal user: GET /api/v1/activation-state → 200 (own data only)
[ ] User A: GET /api/v1/saved-searches → only User A's searches
[ ] User A: DELETE /api/v1/saved-searches/<User B's id> → 404

Workers:
[ ] Celery worker: docker compose logs celery-worker --tail 5 → no crash loop
[ ] Celery beat: docker compose logs celery-beat --tail 5 → tasks firing
[ ] docker compose logs backend --tail 20 → no critical errors
```

---

## D. Assignee Backfill (Andy — After Deploy)

Two paths. Choose one.

### Path 1: Admin endpoint (recommended — instant results)

```bash
# 1. Get admin cookie (login through browser, copy from DevTools → Application → Cookies)
# OR use the admin API key if available

# 2. Trigger backfill
curl -X POST https://inventionindex.com/api/v1/admin/trigger-assignee-backfill \
  -H "Cookie: <admin-cookie>" \
  -H "Content-Type: application/json"
# Expected: {"status": "accepted", "task_id": "..."}

# 3. Wait 1-2 minutes, then verify
docker compose exec postgres psql -U <user> -d invention_index -c "
  SELECT entity_type, COUNT(*) FROM assignees GROUP BY entity_type;
"
# Expected: rows for 'corporation', 'university', 'gov', etc.

# 4. Check company coverage
docker compose exec postgres psql -U <user> -d invention_index -c "
  SELECT COUNT(*) as total_assignees,
         COUNT(*) FILTER (WHERE entity_type IS NOT NULL) as with_entity_type
  FROM assignees;
"
# Expected: with_entity_type > 0 (was 0 before backfill)
```

### Path 2: Wait for Celery beat (passive)

The backfill task is scheduled daily at 04:00 UTC in Celery beat:

```bash
docker compose logs celery-beat --tail 20
# Look for: "backfill-assignees-daily" task entry
```

### Verification after backfill

```bash
# Companies page coverage
# Visit https://inventionindex.com/companies
# Expected: Entity Type Coverage > 0 (was "0 of N — enrichment pending")
# Country Coverage will still be 0 until external data source is integrated
```

---

## E. Safe Postgres Password Rotation

**CRITICAL: Do NOT change POSTGRES_PASSWORD in .env for an existing database.**
PostgreSQL stores the password in the database, not in env vars. Changing the
env var without also updating the database user will break all connections.

### Correct process:

```bash
# 1. Generate a strong password
openssl rand -base64 32
# Copy output: e.g. "g7Xp2Kq9mN3vR5sW8yB1dF4hJ6lZ0aC..."

# 2. Connect to PostgreSQL as superuser
docker compose exec postgres psql -U postgres

# 3. Change the application user's password (NOT creating a new user)
ALTER USER <app_user> WITH PASSWORD '<new_password>';
# Replace <app_user> with the actual DB user (check .env POSTGRES_USER)
# Replace <new_password> with the output from step 1
\q

# 4. Update .env file
vi /opt/invention-index-8/.env
# Change: POSTGRES_PASSWORD=<new_password>
# Also update: DATABASE_URL if it contains the password inline

# 5. Update backend env (if separate from .env)
# The docker-compose.yml uses ${POSTGRES_PASSWORD} from .env — no code change needed

# 6. Restart dependent services
docker compose up -d backend celery-worker celery-beat

# 7. Verify connectivity
docker compose exec backend python -c "from app.core.database import engine; print('DB OK')"
# Expected: "DB OK"

docker compose exec celery-worker celery -A app.tasks.celery_app status
# Expected: OK

# 8. Verify app works
curl -s https://inventionindex.com/api/v1/health
# Expected: {"status": "healthy"}

# 9. Rollback (if needed)
# docker compose exec postgres psql -U postgres
# ALTER USER <app_user> WITH PASSWORD '<old_password>';
# Restore .env to old password
# docker compose up -d backend celery-worker celery-beat
```

---

## F. Post-Deploy Verification

Run these on production AFTER deploy + backfill + password rotation:

```bash
# Quick health
curl -s https://inventionindex.com/api/v1/health && echo ""

# Key screens
curl -s -o /dev/null -w "Today: %{http_code}\n" https://inventionindex.com/today
curl -s -o /dev/null -w "Search: %{http_code}\n" https://inventionindex.com/search
curl -s -o /dev/null -w "Companies: %{http_code}\n" https://inventionindex.com/companies
curl -s -o /dev/null -w "Expiry: %{http_code}\n" https://inventionindex.com/expiry
curl -s -o /dev/null -w "Watchlist: %{http_code}\n" https://inventionindex.com/watchlist
# Expected: all 200

# Logs (last 20 lines, check for ERROR or CRITICAL)
docker compose logs backend --tail 20 | grep -i error || echo "No errors in backend logs"
docker compose logs celery-worker --tail 10
docker compose logs celery-beat --tail 10

# Workers
docker compose exec celery-worker celery -A app.tasks.celery_app inspect active
# Expected: no stuck tasks

# Celery beat
docker compose logs celery-beat --tail 5 | grep -i "Scheduler\|beat"
# Expected: "beat: Starting..." or similar healthy message
```

---

## G. Rollback Plan

If the release must be rolled back:

```bash
# 1. Revert code
cd /opt/invention-index-8
git revert <release-commit> --no-edit
# OR
git reset --hard <previous-production-commit-hash>

# 2. Downgrade migrations (reverse order: 0034→0033→0032→0031)
docker compose exec backend alembic downgrade 0031
# This drops: feedback, alert_intents, saved_searches tables
# Removes: last_today_seen_at, previous_today_seen_at columns
# Data in those tables/columns will be LOST — acceptable for a revert

# 3. Rebuild + restart
docker compose build backend frontend
docker compose up -d backend frontend celery-worker celery-beat nginx

# 4. Verify
curl -s -o /dev/null -w "%{http_code}" https://inventionindex.com
# Expected: 200
```

**Data safety:** The migration downgrade drops new tables. If feedback or alert
intent data was collected, it will be lost. For a non-destructive rollback,
skip the migration downgrade and only revert the code — the new tables will
simply be unused.

---

## H. Launch Metrics (First 7 Days)

Run these queries daily to track adoption:

```sql
-- Activation funnel
SELECT
  (SELECT COUNT(*) FROM users) AS total_users,
  (SELECT COUNT(*) FROM users WHERE last_today_seen_at IS NOT NULL) AS today_users,
  (SELECT COUNT(DISTINCT user_id) FROM watchlist) AS users_with_saves,
  (SELECT COUNT(DISTINCT user_id) FROM saved_searches) AS users_with_searches,
  (SELECT COUNT(DISTINCT user_id) FROM user_company_follows) AS users_following_companies,
  (SELECT COUNT(DISTINCT user_id) FROM feedback) AS users_with_feedback;

-- Feedback ratio
SELECT surface, rating, COUNT(*) FROM feedback
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY surface, rating ORDER BY surface, rating;

-- Top missing activation steps
-- (requires per-user activation state calculation — check GET /api/v1/activation-state)
```

---

## I. Launch Blocker Classification

| Item | Status | Blocker? | Who | Notes |
|------|--------|----------|-----|-------|
| Release branch clean | ✅ Verified | No | Hermes | git status clean, alembic chain 0034→0033→0032 |
| Frontend baseline | ✅ tsc 0e, build 6.5s | No | Hermes | 53/53 tests, lint clean |
| Migration 0034 | ✅ Created, chained | No | Hermes | feedback + alert_intents tables |
| Staging deployment | ⬜ Andy to run | Yes | Andy | Section C — staging smoke checklist |
| Migration apply (prod) | ⬜ Andy to run | Yes | Andy | `alembic upgrade head` |
| Assignee backfill | ⬜ Andy to run | Yes | Andy | Section D — admin endpoint or Celery beat |
| Postgres password rotation | ⬜ Andy to run | Yes | Andy | Section E — safe ALTER USER process |
| Celery beat health | ⬜ Andy to verify | Yes | Andy | Check logs after deploy |
| npm audit major upgrades | ⬜ Deferred | No | — | Next 16, Sentry 10 — post-launch |
| Staging smoke test | ⬜ Andy to run | No | Andy | 27 checks in checklist |
| Backup before deploy | ⬜ Andy to run | Yes | Andy | pg_dump before any changes |

---

## J. What I Verified Directly vs What Andy Must Run

### Verified by Hermes (local):

- ✅ Release branch: clean tree, correct HEAD (485617c)
- ✅ Migration chain: 0034 → 0033 → 0032 → 0031, single head, no gaps
- ✅ Migration files: all 5 revamp migrations present
- ✅ Alembic chain: revision/down_revision all correct
- ✅ Frontend: tsc 0 errors, build 6.5s, lint 0 errors/warnings, tests 53/53
- ✅ Admin auth: all 16+ trigger endpoints + admin endpoints require `require_admin`
- ✅ User isolation: retention endpoints require `current_user`, admin endpoints check `is_admin`
- ✅ Docs: all 12 documents present (app-map through release-plan)
- ✅ No debug artifacts: clean git status, no __pycache__ outside venv

### Andy must run (on staging + production):

1. **Pre-deploy backup** — `pg_dump` before any changes (Section A)
2. **Staging deploy** — `git pull` + `alembic upgrade head` + rebuild (Section C)
3. **Staging smoke test** — run 27 checks from checklist (Section C.2)
4. **Production deploy** — merge + migrate + rebuild (Section B)
5. **Migration verify** — confirm 0034 applied, tables exist (Section B.3)
6. **Assignee backfill** — admin endpoint OR wait for Celery beat (Section D)
7. **Password rotation** — safe ALTER USER, NOT env-only change (Section E)
8. **Post-deploy verify** — health endpoints, logs, workers (Section F)
