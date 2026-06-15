# Sprint 1.5 — Production & Security Gate

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-1-stabilization`
**Purpose:** Verify production-readiness of admin endpoint security, assignee backfill, database credentials, and npm audit follow-ups before starting UX work.

---

## Gate 1: Admin Trigger Endpoint Authorization

### Status: ✅ CODE FIXED — needs test run

All 8 trigger endpoints now require `admin: _UserModel = Depends(require_admin)`.

| Endpoint | Before | After |
|----------|--------|-------|
| `/admin/trigger-ingest` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-summarize` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-family-resolution` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-expiry-backfill` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-enrich-abstracts` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-resummarize` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-match-themes` | ❌ No auth (env guard only) | ✅ `require_admin` |
| `/admin/trigger-assignee-backfill` | ✅ `require_admin` (added in Sprint 1) | ✅ `require_admin` |

**Defense in depth:** Both layers apply — `require_admin` checks user identity, `settings.environment == "production"` blocks production triggers regardless. An attacker needs to both authenticate as admin AND have the env var misconfigured.

### Tests Added

File: `backend/tests/api/test_admin.py`

| Test | Purpose |
|------|---------|
| `test_trigger_unauthorized_no_cookie` | All 8 endpoints reject requests with no auth cookie (parametrized) |
| `test_trigger_forbidden_non_admin` | All 8 endpoints reject non-admin users (parametrized) |
| `test_trigger_assignee_backfill_admin_accepted` | Admin user can call the assignee backfill trigger |

### Verification (requires backend test runner)

```bash
cd backend && python -m pytest tests/api/test_admin.py -v
```

Expected: 18 parametrized + 1 specific + existing tests = all passing.

### Note

The `trigger_expiry_backfill` and `trigger_match_themes` endpoints had a parameter name collision (`settings: AppSettings` vs module-level `settings` import). Renamed parameter to `app_settings: AppSettings` to avoid shadowing. Production guard references updated accordingly.

---

## Gate 2: Production Assignee Backfill

### Status: ⚠️ NEEDS ANDY SERVER ACTION

The backfill code is deployed-ready, but the backfill has never run on production. Two paths to trigger:

#### Option A: Admin endpoint (recommended for initial run)
```bash
# Requires admin auth cookie from a logged-in admin session
curl -X POST https://inventionindex8.com/api/v1/admin/trigger-assignee-backfill \
  -H "Cookie: auth_session=<admin-jwt>"
```

#### Option B: Celery beat (automatic, daily 04:00 UTC)
The task is already in the Celery beat schedule:
```python
"backfill-assignees-daily": {
    "task": "app.tasks.backfill_assignees.backfill_assignees_task",
    "schedule": crontab(hour=4, minute=0),
    "options": {"queue": "maintenance"},
},
```
It runs daily at 04:00 UTC. If the beat container has been healthy since V3 Phase 5 deployment, it may have already run.

### Before/After Verification

Run these queries on production DB before and after the backfill:

```sql
-- Before backfill
SELECT COUNT(*) FROM assignees;
-- Expected: 0 (or low number if beat already ran)

-- After backfill
SELECT COUNT(*) FROM assignees;
-- Expected: ~16,723 (one per distinct normalized assignee name)

-- Entity type breakdown
SELECT entity_type, COUNT(*) FROM assignees GROUP BY entity_type ORDER BY COUNT(*) DESC;
-- Expected: ~15,000 corporation, ~1,500 university, ~200 gov, some NULL

-- Country breakdown (will be 0 — no data source yet)
SELECT COUNT(*) FROM assignees WHERE country IS NOT NULL;
-- Expected: 0
```

### Companies Page Verification

After backfill:
1. Visit `/companies` page
2. Coverage bars should no longer show "0 of X" for Entity Type
3. Country coverage will still show 0 (no data source) but with the enrichment-pending explanation
4. Company table rows should show entity_type badges (corporation/university/gov) instead of "Enrichment pending"

### Expected After Backfill

| Metric | Before | After |
|--------|--------|-------|
| `suppliers_with_entity_type` | 0 | ~15,000+ |
| `suppliers_with_country` | 0 | 0 (still no country source) |
| `total_suppliers` | 16,723 | 16,723 (unchanged) |
| CoverageBar: Entity Type | "0 of 16,723" + enrichment note | "~15,000 of 16,723" (~90%) |
| CoverageBar: Country | "0 of 16,723" + enrichment note | "0 of 16,723" + enrichment note (unchanged) |

---

## Gate 3: Postgres Password / Deployment Secret

### Status: ⚠️ NEEDS ANDY SERVER ACTION

### Current state
- `docker-compose.yml`: `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secret}` — defaults to "secret" if unset
- `.env.example`: `POSTGRES_PASSWORD=***` — placeholder
- No plaintext production password found in committed files

### Required actions

1. **Set strong password on server:**
   ```bash
   ssh root@188.245.85.248
   # Generate a strong password
   openssl rand -base64 32
   # Add to .env
   echo 'POSTGRES_PASSWORD=<generated-value>' >> /opt/invention-index-8/.env
   ```

2. **Recreate DB container with new password:**
   ```bash
   cd /opt/invention-index-8
   docker compose down db
   docker compose up -d db
   # Wait for healthy, then restart dependent services
   docker compose up -d backend worker beat
   ```

3. **Verify:**
   ```bash
   # From outside the server, these should fail:
   nc -vz 188.245.85.248 5432  # Should be refused/blocked
   nc -vz 188.245.85.248 6379  # Should be refused/blocked
   ```

4. **Consider Docker secrets for future:**
   ```yaml
   # docker-compose.yml with secrets
   secrets:
     db_password:
       file: /run/secrets/db_password
   ```

### Rotation plan
- Current password: unknown (was "secret" default unless overridden on server)
- New password: generate via `openssl rand -base64 32`
- Rotation frequency: quarterly (every 90 days)
- Rotation procedure: update `.env`, restart db container, verify backend connectivity

---

## Gate 4: npm Audit Follow-ups

### Status: ✅ DOCUMENTED

7 remaining vulnerabilities are all transitive, requiring major version bumps:

| Package | Vulns | Blocked by | Follow-up |
|---------|-------|-----------|-----------|
| next → postcss | 1 moderate | Requires next 16 (major) | Defer to post-revamp |
| next | 4 high | Requires next 16 (major) | Defer to post-revamp |
| @sentry/nextjs → rollup | 1 high | Requires @sentry/nextjs 10.x (2 majors) | Defer to post-revamp |
| @sentry/nextjs → uuid | 1 moderate | Requires @sentry/nextjs 10.x (2 majors) | Defer to post-revamp |

These are visible in `docs/tech-audit.md` Section 9.

---

## Gate Checklist

### Code changes (committed to `sprint-1-stabilization`)
- [x] All 8 trigger endpoints have `require_admin` auth
- [x] `trigger_expiry_backfill` and `trigger_match_themes` parameter renamed to avoid `settings` shadowing
- [x] Production guard references updated to use `app_settings`
- [x] Admin auth tests added (parametrized: 8 endpoints × 2 test cases + 1 positive test)
- [x] Existing admin tests preserved and refactored with shared helpers

### Server actions (Andy)
- [ ] Run assignee backfill on production (via admin endpoint or verify Celery beat ran)
- [ ] Capture before/after counts from assignees table
- [ ] Verify Companies page no longer shows broken "0 of 0" for entity type
- [ ] Set strong `POSTGRES_PASSWORD` in `/opt/invention-index-8/.env`
- [ ] Recreate DB container with new password
- [ ] Verify ports 5432 and 6379 are not publicly accessible
- [ ] Add password rotation to operations runbook

### Verified (Hermes, code-only)
- [x] No plaintext production password in committed code
- [x] Password sourced from env var with `:-secret` fallback
- [x] npm audit follow-ups documented in tech-audit.md
- [x] All admin endpoints require authorization (code-level verification)
- [x] Tests exist for unauthorized, non-admin, and admin access patterns
