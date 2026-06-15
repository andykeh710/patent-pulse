# Release Plan — Revamp Launch

**Date:** 2026-06-15
**Branch:** `release/revamp-launch-validation`
**Target environment:** Production (Hetzner VPS)

---

## 1. Merge Order

All branches are stacked linearly. Merge in this order:

```
feat/phase4-pr3-billing-ux-polish  (original base)
  → sprint-1-stabilization
  → sprint-2-ux-foundation
  → sprint-3-today-habit-engine
  → sprint-4-patent-search-intelligence
  → sprint-4-5-search-intelligence-completion
  → sprint-5-company-intelligence
  → sprint-6-expiry-radar-opportunity-workflows
  → sprint-7-retention-feedback
  → release/revamp-launch-validation  (this branch)
```

Since all sprints are already stacked (each built on the previous),
only `release/revamp-launch-validation` (migration 0034 + docs) needs
to be merged on top of `sprint-7-retention-feedback`.

**Command:**
```bash
git checkout main  # or the production branch
git merge release/revamp-launch-validation
```

---

## 2. Deployment Process

### 2.1 Pre-deploy

```bash
# On Hetzner VPS, as the deploy user:
cd /opt/invention-index-8
git pull origin main  # or whichever branch is production
```

### 2.2 Database migrations

```bash
docker compose exec backend alembic upgrade head
# Should apply: 0032 (today_seen_at), 0033 (saved_searches), 0034 (feedback + alert_intents)
# Verify:
docker compose exec backend alembic current
# Expected: 0034
```

### 2.3 Restart services

```bash
docker compose build backend frontend
docker compose up -d backend frontend celery-worker celery-beat nginx
```

### 2.4 Verify health

```bash
# Backend health
curl -s https://inventionindex.com/api/v1/health | jq .

# Frontend serves
curl -s -o /dev/null -w "%{http_code}" https://inventionindex.com

# Celery beat is running
docker compose logs celery-beat --tail 5
```

---

## 3. Expected Downtime

| Window | Duration | What |
|--------|----------|------|
| Docker build | ~60s | New images built, old containers running |
| Restart | ~15s | Containers replaced, nginx buffers requests |
| Migration | ~5s | `alembic upgrade head` (no destructive changes) |
| **Total** | **~90s** | Brief service interruption during container restart |

---

## 4. Rollback Plan

If launch fails:

```bash
# Revert migrations (in reverse order)
docker compose exec backend alembic downgrade 0031
# This drops: feedback, alert_intents, saved_searches, today_seen_at columns

# Revert code
git revert <release-commit-hash>
# OR
git reset --hard <previous-production-commit>

# Rebuild + restart
docker compose build backend frontend
docker compose up -d backend frontend celery-worker celery-beat nginx
```

---

## 5. Post-Deploy Checks

Run these on production after deploy:

- [ ] `curl -I https://inventionindex.com` → 200
- [ ] Login works
- [ ] Today page loads (check `/today`)
- [ ] Search works (query "battery")
- [ ] Patent detail opens (click any result)
- [ ] Company detail loads (`/companies/Qualcomm`)
- [ ] Expiry Radar loads (`/expiry`)
- [ ] Watchlist loads (`/watchlist`)
- [ ] Feedback submits (thumbs up on Today)
- [ ] Admin endpoints return 403 for normal users
- [ ] `docker compose logs backend --tail 20` — no critical errors
- [ ] `docker compose logs celery-worker --tail 10` — no crash loops
- [ ] `docker compose logs celery-beat --tail 10` — scheduled tasks firing
- [ ] Assignee backfill verified (runbook ops-01)

---

## 6. Andy Action Items

These require manual execution:

| # | Task | Command / Reference |
|---|------|-------------------|
| 1 | Run assignee backfill | `POST /api/v1/admin/trigger-assignee-backfill` (with admin cookie) |
| 2 | Rotate Postgres password | `.hermes/runbooks/2026-06-14_post-sprint-1-5-ops-tickets.md` § OPS-02 |
| 3 | Verify Celery beat health | `docker compose logs celery-beat` — check for `backfill-assignees-daily` task |
| 4 | Staging smoke test | Spin up staging, run post-deploy checks, capture screenshots |

---

## 7. Launch Metrics (First 7 Days)

Track via admin retention endpoint + manual queries:

- Total users
- Activated users (2+ steps)
- Saved patents count
- Saved searches count
- Feedback submissions
- Today repeat opens
- Feedback useful/not_useful ratio
- Top missing activation step

Query reference:
```sql
-- Activation summary
SELECT
  COUNT(*) as total_users,
  COUNT(*) FILTER (WHERE last_today_seen_at IS NOT NULL) as today_users,
  (SELECT COUNT(DISTINCT user_id) FROM watchlist) as users_with_saves,
  (SELECT COUNT(DISTINCT user_id) FROM saved_searches) as users_with_searches,
  (SELECT COUNT(*) FROM feedback) as feedback_count
FROM users;
```
