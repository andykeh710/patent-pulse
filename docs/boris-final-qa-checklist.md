# V3.0 Stabilization — Final QA Report

**Branch:** sprint-boris-stabilization
**Head:** 447f445 (stray file removal) + 1 uncommitted (verify page fix)
**Diff from:** release/revamp-launch-validation (fe3ebcb)
**Commits:** 24

---

## All Commits (oldest → newest)

1. `9e2bbd0` — Theme label, nav scroll, landing sections
2. `cff99ca` — Topic follow/create/delete with auth
3. `ceff343` — Today For You vs More Signals
4. `5da444a` — GET /themes/following endpoint
5. `e90aa41` — QA plan doc
6. `501f85a` — User-context labels, login docs, CPC groundwork
7. `3fb8449` — Resend health /emails endpoint
8. `41dba00` — Real followed companies, empty personalized state
9. `94ea684` — Boris P0 QA checklist
10. `4d8585a` — Missing Depends import in themes.py
11. `a01e7b6` — Topics page: unfollow, plain-English creation, dark mode
12. `0a3c334` — CSP font-src fix
13. `5d600c9` — Revert CSP headers
14. `02ed528` — Auth gating, dev magic link logging, login docs
15. `afcdf41` — Move middleware.ts to project root
16. `6e7ad26` — Layout-level auth gating
17. `0253afe` — Dockerfile + theme_matcher + docker-compose fixes
18. `e196439` — P0 release-readiness: auth, health, worker/beat, honesty
19. `c3e6a93` — Theme matching whole-word, admin defaults, beat schedule
20. `ea6d315` — Force-dynamic auth verify flow + topics redirect
21. `36286e7` — Daily incremental ingestion pipeline
22. `ed8c80f` — Separate ingestion freshness from source lag
23. `447f445` — Remove accidentally committed empty stray files
24. *(uncommitted)* — Verify page: window.location.href redirect

---

## V3.0 Stabilization — All Items

### API & Auth

| # | Check | Result |
|---|-------|--------|
| 1 | All 11 API endpoints return 200/401, no 500s | PASS |
| 2 | Auth-gating: logged-out /today → login | PASS |
| 3 | Middleware in src/middleware.ts (Next 15) | PASS |
| 4 | Dev mode login notice ("check backend logs") | PASS |
| 5 | /health overall=ok, resend=dev_preview | PASS |
| 6 | Magic-link verify → cookie → onboarding | PASS |

### Today

| # | Check | Result |
|---|-------|--------|
| 7 | Platform Overview moved below fold | PASS |
| 8 | More Signals with Why/Evidence blocks | PASS |
| 9 | Personalize your briefing empty state | PASS |
| 10 | Your Topics shows real counts (435/465/367) | PASS |
| 11 | FreshnessBanner: 3-tier (stale/source-lag/normal) | PASS |
| 12 | "Since earlier today" freshness indicator | PASS |

### Themes / Topics

| # | Check | Result |
|---|-------|--------|
| 13 | System themes DB-seeded, not hardcoded | PASS |
| 14 | Theme matching: whole-word, 435/465/367 | PASS |
| 15 | /themes/following route works | PASS |
| 16 | Follow/unfollow via subscriptions | PASS |
| 17 | Custom topic create/delete | PASS |
| 18 | /topics → /themes redirect | PASS |

### Companies

| # | Check | Result |
|---|-------|--------|
| 19 | No "Map-ready data" badge when empty | PASS |
| 20 | Honest "enrichment pending" | PASS |
| 21 | Real company rankings with scores | PASS |

### Pipeline

| # | Check | Result |
|---|-------|--------|
| 22 | Worker/beat running (6/6 services) | PASS |
| 23 | Nightly ingestion (2am daily) | PASS |
| 24 | Dynamic catch-up (30-day lookback) | PASS |
| 25 | ingestion_runs tracking table | PASS |
| 26 | Freshness API: ingestion vs source fields | PASS |
| 27 | Redis lock prevents overlapping runs | PASS |
| 28 | Downstream chain: enrich → match → score → trends | PASS |

### Housekeeping

| # | Check | Result |
|---|-------|--------|
| 29 | tsconfig.tsbuildinfo gitignored | PASS |
| 30 | Stray files 0035/401 removed | PASS |
| 31 | docker-compose.prod.yml inherits env var | PASS |
| 32 | patent_client pydantic-settings v2 fix | PASS |
| 33 | Admin defaults verified | PASS |

---

## Manual QA Checklist for Andy

### Landing Page
- [ ] Pricing scrolls to #pricing section
- [ ] About scrolls to #about section
- [ ] Theme toggle: System → Dark → Light → System

### Login
- [ ] Dev mode notice appears ("check backend logs")
- [ ] Magic link in backend logs
- [ ] Open verify link → lands on onboarding
- [ ] Onboarding → complete → lands on Today

### Today
- [ ] "Personalize your briefing" shown for new user
- [ ] Your Topics shows real counts
- [ ] More Signals section with Why/Evidence
- [ ] Platform Overview at bottom
- [ ] Freshness: "Ingestion: Last ran X (no new records)" or similar
- [ ] No red "Data is not live" banner when pipeline is healthy

### Themes
- [ ] System themes have Follow buttons
- [ ] Click Follow → appears in Your Topics
- [ ] Delete works on user topics
- [ ] Create Topic form works

### Companies
- [ ] No "Map-ready data" badge when no country data
- [ ] "Enrichment pending" labels
- [ ] Company rankings load with real data

### Expiry Radar
- [ ] Horizon tabs work
- [ ] Save/unsave works

### API Health
- [ ] GET /health → overall=ok, alembic_head=0036
- [ ] GET /api/v1/patents/freshness → last_ingestion_status=success
- [ ] GET /themes → patent_count > 0 on all themes
- [ ] GET /themes/following → returns followed themes

### Pipeline
- [ ] `docker compose ps` shows 6 services
- [ ] `docker compose exec backend celery -A app.tasks.celery_app call app.tasks.ingest_daily.run_catch_up_ingestion --kwargs='{"lookback_days":30}'` succeeds
- [ ] `docker compose exec db psql -U patent -d patent_pulse -c "SELECT * FROM ingestion_runs ORDER BY started_at DESC LIMIT 3;"` shows recent runs

---

## Remaining Uncommitted

```
frontend/src/app/(auth)/login/verify/page.tsx  — window.location.href redirect fix
```

Commit this, then rebuild frontend one final time.

---

## Merge Decision

**READY** — after committing the verify page fix. All 33 items pass. 24 commits. No fake data, no misleading badges, pipeline healthy. Do not merge until Andy completes visual QA.
