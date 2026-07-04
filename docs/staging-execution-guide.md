# Staging Deployment + Smoke Test — Launch Step 3

**Date:** 2026-06-15
**Release branch:** `release/revamp-launch-validation`
**Last release commit:** `9a0dc7e` — migration chain repair

---

## Migration Chain Repair (Launch Blocker — Fixed)

Three migration files (0029, 0030, 0031) had filename-based `down_revision`
values that didn't match the actual `revision` attributes in their parent
files. This caused `KeyError` when Alembic built the dependency graph.

**Fixed:** `9a0dc7e` changes down_revision to numeric IDs matching the
parent revision attribute.

- 0029: `"0028_user_onboarding_fields"` → `"0028"`
- 0030: `"0029_email_deliveries_tracking"` → `"0029"`
- 0031: `"0030_alerts_webhook_configs"` → `"0030"`

After fix: `alembic heads` returns single head 0034. Chain: 0027→...→0034.

---

## S0. Staging Environment Confirmation

Before running any commands, fill in these values:

```bash
# CONFIRM THESE (edit to match your staging setup):
STAGING_PATH="/opt/invention-index-staging"   # path to staging directory
STAGING_DOMAIN="staging.inventionindex.com"    # or IP/port

cd $STAGING_PATH
pwd
# Expected: the staging directory path you set above
```

Stop here if you can't confirm the staging path. Do not proceed with guesswork.

---

## S1. Pre-Deploy Checks

```bash
cd $STAGING_PATH

# 1.1 Current commit
git log --oneline -1
# Expected: the current deployed commit on staging
# Record this: _______

# 1.2 Working tree clean
git status --short
# Expected: no output (clean tree)
# If dirty, STOP — resolve first

# 1.3 Current migration
docker compose exec backend alembic current
# Expected: 0031_blog_posts or 0032/0033 if already partially applied
# Record this: _______

# 1.4 Services healthy
docker compose ps
# Expected: db (healthy), redis (healthy), backend (Up), frontend (Up),
#           worker (Up), beat (Up), nginx (Up)
# If any service is not Up, STOP

# 1.5 .env exists
test -f .env && echo "OK" || echo "MISSING"
# Expected: OK
# If MISSING, STOP

# 1.6 Admin login (manual — open browser)
# Navigate to https://$STAGING_DOMAIN/login
# Log in with admin credentials
# If admin login fails, STOP — fix auth
```

---

## S2. Backup Staging Database

```bash
cd $STAGING_PATH
mkdir -p ~/backups

docker compose exec db pg_dump -U patent patent_pulse > ~/backups/staging_pre_revamp_$(date +%Y%m%d_%H%M).sql

ls -la ~/backups/staging_pre_revamp_*.sql
# Expected: file > 0 bytes
# If 0 bytes or error, STOP
```

---

## S3. Deploy Release to Staging

```bash
cd $STAGING_PATH

# 3.1 Fetch + merge
git fetch origin release/revamp-launch-validation
git merge origin/release/revamp-launch-validation

# 3.2 Verify commit
git log --oneline -3
# Expected top commit: 4865132 "launch-ops QA: fix all placeholders..."
# If the wrong commit or merge conflicts, STOP

# 3.3 Apply migrations
docker compose exec backend alembic upgrade head
# Expected output:
#   INFO  [alembic.runtime.migration] Running upgrade ... -> 0032
#   INFO  [alembic.runtime.migration] Running upgrade 0032 -> 0033
#   INFO  [alembic.runtime.migration] Running upgrade 0033 -> 0034
# Note: some migrations may already be applied — that's OK as long
# as the final line shows reaching 0034 without errors

# 3.4 Verify migration head
docker compose exec backend alembic current
# Expected: 0034_feedback_alert_intents

docker compose exec backend alembic heads
# Expected: 0034 (single line — no branches)

# 3.5 Verify new DB objects
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN ('feedback', 'alert_intents', 'saved_searches')
  ORDER BY table_name;
"
# Expected output:
#  alert_intents
#  feedback
#  saved_searches
# (or 2 rows if some already existed)

docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name = 'users'
    AND column_name IN ('last_today_seen_at', 'previous_today_seen_at');
"
# Expected: 2 rows, type 'timestamp with time zone'

# 3.6 Rebuild + restart
docker compose build backend frontend
docker compose up -d backend frontend worker beat nginx

sleep 10
docker compose ps
# Expected: all services Up / Up (healthy)

# 3.7 Health check
curl -s http://localhost:8000/api/v1/health
# Expected: {"status":"healthy"}
```

---

## S4. Staging Smoke Test Checklist

Run each item. Mark ✅ or ❌.

### Core App

| # | Check | Command / Steps | Result |
|---|-------|----------------|--------|
| 1 | Homepage | Open https://$STAGING_DOMAIN in browser | |
| 2 | Auth — login | Log in with known credentials | |
| 3 | Today loads | Navigate to /today | |
| 4 | Today mark-seen | Check comparison label (e.g. "Since earlier today") | |
| 5 | Today hard refresh | Refresh — label unchanged (5-min idempotency) | |
| 6 | Search | Query "battery" — results appear | |
| 7 | Search filter | Set legal_status=GRANTED — FilterChips appear | |
| 8 | Search sort | Change to "Newest first" — results reorder | |
| 9 | Saved search create | Name + Save — appears in Saved Searches | |
| 10 | Saved search open | Click saved search — query/filters restored | |
| 11 | Saved search delete | Delete saved search — removed from list | |
| 12 | Patent detail | Click any search result — page loads | |
| 13 | Patent tabs | Switch Overview → Commercial → Claims | |
| 14 | Save patent card | Click bookmark on search result card | |
| 15 | Save patent detail | Click bookmark on patent detail page | |
| 16 | Share/Copy link | Click "Copy link" on patent detail | |
| 17 | Company list | Navigate to /companies — loads with data | |
| 18 | Company detail | Click a company — portfolio, follow button visible | |
| 19 | Follow company | Click "Follow company" — toggles to "Following" | |
| 20 | Expiry Radar | Navigate to /expiry — loads with cards | |
| 21 | Expiry horizons | Click "0-6 mo" tab — results filter | |
| 22 | Expiry FilterChips | Apply status filter — chip appears | |
| 23 | Expiry save | Click bookmark on expiry card | |
| 24 | Expiry CSV export | Click Export button — file downloads | |
| 25 | Watchlist Patents | Navigate to /watchlist — saved patent visible | |
| 26 | Watchlist Companies | Switch to Followed Companies tab | |
| 27 | Watchlist Searches | Switch to Saved Searches tab | |
| 28 | Feedback | Scroll to bottom — click thumbs up → "Thanks" | |

### API Endpoints

Run these via curl or browser DevTools:

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 29 | Feedback API | `curl -X POST -H "Cookie: <cookie>" https://$STAGING_DOMAIN/api/v1/feedback -H "Content-Type: application/json" -d '{"route":"/today","surface":"today","rating":"useful"}'` | `{"id":"...", "status":"submitted"}` |
| 30 | Alert intent API | `curl -X POST -H "Cookie: <cookie>" https://$STAGING_DOMAIN/api/v1/alert-intent -H "Content-Type: application/json" -d '{"alert_type":"company_expiry","frequency":"weekly"}'` | `{"id":"...", "status":"intent_captured", "note":"Alert delivery will be..."}` |
| 31 | Activation state | `curl -H "Cookie: <cookie>" https://$STAGING_DOMAIN/api/v1/activation-state` | JSON with activated, missing_steps |
| 32 | Admin retention (admin) | `curl -H "Cookie: <admin_cookie>" https://$STAGING_DOMAIN/api/v1/admin/retention` | JSON with total_users, today_views, etc |

### Security

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 33 | Anonymous → admin | `curl https://$STAGING_DOMAIN/api/v1/admin/retention` | 401 or 403 |
| 34 | Normal user → admin | `curl -H "Cookie: <user_cookie>" https://$STAGING_DOMAIN/api/v1/admin/retention` | 403 |
| 35 | Admin → admin | `curl -H "Cookie: <admin_cookie>" https://$STAGING_DOMAIN/api/v1/admin/retention` | 200 + JSON |
| 36 | Anonymous → feedback admin | `curl https://$STAGING_DOMAIN/api/v1/feedback/admin` | 401 or 403 |
| 37 | Normal user → feedback admin | `curl -H "Cookie: <user_cookie>" https://$STAGING_DOMAIN/api/v1/feedback/admin` | 403 |

### Workers

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 38 | Worker ping | `docker compose exec worker celery -A app.tasks.celery_app inspect ping` | `{"celery@...": {"ok": "pong"}}` |
| 39 | Worker logs | `docker compose logs worker --tail 20` | No "error" or "traceback" |
| 40 | Beat logs | `docker compose logs beat --tail 20` | "beat: Starting...", no crash |
| 41 | Backend logs | `docker compose logs backend --tail 20 \| grep -i error` | No output (or only known non-critical) |

---

## S5. Assignee Backfill (Staging)

```bash
cd $STAGING_PATH

# 5.1 Before counts
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE entity_type IS NOT NULL) AS with_entity_type
  FROM assignees;
"
# Record: total=____ with_entity_type=____

# 5.2 Trigger backfill (need admin cookie from browser)
# Get admin cookie from DevTools → Application → Cookies
curl -X POST https://$STAGING_DOMAIN/api/v1/admin/trigger-assignee-backfill \
  -H "Cookie: <admin_cookie>" \
  -H "Content-Type: application/json"
# Expected: {"status": "accepted", "task_id": "..."}

# 5.3 Wait and check progress
sleep 30
docker compose logs worker --tail 30 | grep -i "assignee\|backfill"
# Expected: task execution logs

# 5.4 After counts (wait 2-3 minutes if needed)
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT
    entity_type,
    COUNT(*) AS cnt
  FROM assignees
  GROUP BY entity_type
  ORDER BY cnt DESC;
"
# Expected: rows like corporation/NNNN, university/NNN, etc.
# Record: ____

docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE entity_type IS NOT NULL) AS with_entity_type
  FROM assignees;
"
# Record: total=____ with_entity_type=____
# Expected: with_entity_type > 0 (was 0 before backfill if staging was fresh)

# 5.5 Check Companies page
# Navigate to https://$STAGING_DOMAIN/companies
# Expected: Entity Type Coverage badge no longer shows "enrichment pending"
```

If staging has no assignee data (empty database), record this and skip. Production verification will be required.

---

## S6. Issues Classification

Fill in this table after smoke testing:

| # | Area | Check | Status | Blocker? | Notes |
|---|------|-------|--------|----------|-------|
| — | — | — | ⬜ | — | — |

Classification guide:
- **Launch blocker** — must fix before production deploy
- **Fix before production** — not blocking but should be resolved
- **Acceptable post-launch** — can ship, track in backlog
- **Staging-only** — staging env issue, not production
- **Needs Andy** — requires manual action

---

## S7. Final Staging Decision

After completing all checks above, fill in:

```
Staging deployed: YES / NO
Migration head: _______
Smoke tests: ___ / 41 passed
Backfill: SUCCESS / SKIPPED / FAILED
Worker healthy: YES / NO
Beat healthy: YES / NO
Launch blockers: NONE / LIST BELOW

Production deployment can proceed: YES / NO

If NO, blockers:
1.
2.
3.
```

---

## What Hermes Verified vs What Andy Must Run

| Verified by Hermes (local) | Andy must run (staging) |
|---|---|
| ✅ Release branch clean: 4865132 | ⬜ Section S1: pre-deploy checks |
| ✅ Migration chain: 0034 → 0033 → 0032 | ⬜ Section S2: backup |
| ✅ Frontend: tsc 0e, build 6.5s, lint clean, 53/53 tests | ⬜ Section S3: deploy + migrate + verify |
| ✅ Admin endpoints guarded (code audit) | ⬜ Section S4: 41 smoke checks |
| ✅ All 12 docs present | ⬜ Section S5: assignee backfill |
| ✅ Service names match docker-compose.yml | ⬜ Section S6: classify issues |
| ✅ Runbook commands validated | ⬜ Section S7: staging decision |
