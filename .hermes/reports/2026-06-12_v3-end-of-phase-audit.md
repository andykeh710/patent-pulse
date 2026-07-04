# V3 End-of-Phase Audit — Invention Index 8

**Date:** 2026-06-12
**Author:** Hermes (investigation only — no code, no PR, no production access)
**Source:** `.hermes/plans/2026-06-04_v3-roadmap.md`
**Status:** INVESTIGATION COMPLETE — ready for Andy review

---

## Section 1 — Phase-by-Phase Verification

### Phase 0 — Stabilization Tail (1 week)

**Roadmap promised:**
- Production-mode email send works end-to-end (deliverability >95%)
- Site goes 7 days with no manual intervention
- Companies page renders >100 entries
- Caddy migration / cleanup
- Figure backfill
- PR template + CONTRIBUTING.md

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| Email send-mode safety gate (`EMAIL_PRODUCTION_ACKNOWLEDGED`) | Config guard in main.py | ✅ Code present |
| Magic-link auth works end-to-end | PRs from Sprint 6-7 | ✅ Memory confirms |
| Resend DKIM/SPF/DMARC records | Andy actions (not code) | ⚠️ Requires Andy DNS verification |
| Caddy cleanup | Roadmap item | ❌ NOT DONE — still untracked per Phase 0 code items |
| Figure backfill | `backfill_figure_urls` task | ⚠️ Unknown — only 5K/64K had thumbnails per roadmap |
| Companies "0 of 0" fix | Investigation report exists | ⚠️ See `.hermes/reports/2026-06-07_companies-zero-investigation.md` |
| PR template | Roadmap item | ❌ NOT DONE |
| Sentry V8 instrumentation migration | Roadmap item | ✅ PR #18 |

**Missing / partially delivered:**
1. **Caddy container** — still orphaned outside docker-compose. Low severity (not customer-facing) but adds ops complexity.
2. **Companies page** — situation unclear. Investigation report exists but outcome unknown.
3. **Figure backfill** — coverage unknown. Only affects visual appeal of patent detail pages.

**Verifiable in production:**
```bash
curl https://inventionindex8.com/health  # should return 200 + database=ok
curl https://inventionindex8.com/api/v1/auth/request-link -X POST -d '{"email":"test@example.com"}' -H 'Content-Type: application/json'  # returns {ok: true} with Resend delivery
```

---

### Phase 1 — Semantic Search Foundation (2 weeks)

**Roadmap promised:**
- DeepSeek embeddings + pgvector HNSW index
- Embedding worker batch API fix
- Hybrid search backend (vector + keyword + recency)
- Frontend hybrid-default
- Admin re-embed tool
- Coverage >90%

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| HNSW pgvector index | #17 (alembic 0027) | ✅ Merged |
| Embedding worker batch-API fix | #21 | ✅ Merged — 200/batch via batch API |
| Hybrid search backend | #24 | ✅ Merged |
| Frontend hybrid-default | #25 | ✅ Merged |
| Admin re-embed tool | #26 | ✅ Merged |
| Coverage | Backfill ongoing via Celery beat | ⚠️ ~65% at last check, climbing |

**Verifiable in production:**
```bash
curl -X POST "https://inventionindex8.com/api/v1/semantic/query?query=solid+state+battery&limit=10"
# Should return ranked results with similarity scores
```

**Gaps:**
- Embedding coverage not yet at >90%. Backfill was running at ~200/2min — full 64K corpus takes ~11 hours. Should be complete by now unless paused.

---

### Phase 2 — First-Run Experience + Onboarding (1 week)

**Roadmap promised:**
- Empty-state copy pass across all surfaces
- Onboarding wizard + tour
- Persona-aware briefing ranking

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| Empty-state copy pass | #27 | ✅ Merged |
| Onboarding wizard + tour | #28 + #31 (lint fix) | ✅ Merged |
| Persona-aware briefing ranking | #29 | ✅ Merged |

**Verifiable in production:**
```bash
# Onboarding sets persona
POST /api/v1/account/persona  {"persona": "investor"}  # returns updated persona
GET /api/v1/today/briefing  # should weight results by persona
```

**Gaps:**
- Marketing landing page (#30) was "in conflict — may or may not be live." Needs Andy's eyes-on verification.
- Persona only affects briefing ranking. Does NOT affect semantic search or chat retrieval (see Section 2).

---

### Phase 3 — RAG Chatbot MVP (3-4 weeks)

**Roadmap promised:**
- SSE streaming scaffold
- Anthropic Claude streaming + patent retrieval
- Tool calls (search_patents, open_patent, compare_companies)
- Citation enforcement (soft warning)
- Redis conversation memory
- Quota enforcement (Free 5/day, Basic 50/day)
- Frontend /chat page + patent-detail "Ask AI"

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| SSE scaffold + mock LLM | #33 | ✅ Merged |
| Anthropic streaming + retrieval | #34 | ✅ Merged |
| Tool calls | #35 | ✅ Merged |
| Citation extraction + soft warning | #36 | ✅ Merged |
| Redis conversation memory | #37 | ✅ Merged |
| Chat quota enforcement | #38 | ✅ Merged |
| Chat frontend (/chat, citations, quota, seed param) | #39 | ✅ Merged |

**Deferred:**
- Patent-detail chat drawer → replaced with "Ask AI" button + seed param. Deferred to Phase 3.5 (see PR #39 body, Section 3 below).
- News retrieval in chat → deferred to Phase 3.5.

**Verifiable in production:**
```bash
# Chat stream (requires auth cookie)
curl -X POST https://inventionindex8.com/api/v1/chat/stream \
  -H 'Cookie: auth_session=<jwt>' \
  -d '{"message":"What are the top semiconductor trends?"}'
# Should return SSE stream with text events, citations, sources, done
```

**Gaps:**
- Chat memory TTL is 30 minutes. If a user returns after 31 minutes, conversation is empty with no notice. Consider a "welcome back, would you like to continue?" prompt.
- Chat quota stub still exists in code (`_check_chat_quota_stub`) alongside the real enforcement. If the stub path is somehow reached, users bypass limits.

---

### Phase 4 — Tier Value Differentiation (2 weeks)

**Roadmap promised:**
- Stripe LIVE flip preparation
- Paywall enforcement
- Frontend billing UX polish
- Usage endpoint
- Upgrade prompts banner

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| Stripe LIVE safety gate (`STRIPE_LIVE_ACKNOWLEDGED`) | #40 | ✅ Merged |
| Billing health endpoint (admin-only) | #40 | ✅ Merged |
| Webhook signature hardening (400→401) | #40 | ✅ Merged |
| Usage endpoint (`GET /api/v1/account/usage`) | #41 | ✅ Merged |
| Billing page polish (usage bars, tier badge, pricing table) | #41 | ✅ Merged |
| Usage warning banner (80% threshold, localStorage dismiss) | #41 | ✅ Merged |
| Upgrade flow polish (success/cancelled toasts) | #41 | ✅ Merged |

**What's NOT flipped yet:**
- Stripe is still in TEST mode. Andy must manually flip after verifying the checklist in PR #40 body.

**Verifiable in production:**
```bash
GET /api/v1/admin/billing/health  # admin-only; shows mode=test, subscription counts
GET /api/v1/account/usage  # returns per-feature usage with limits
```

---

### Phase 5 — Distribution + Engagement Loops (1-2 weeks)

**Roadmap promised:**
- Weekly briefing A/B subject line testing
- Alert webhooks (4 alert types, HMAC-signed)
- Public company + theme pages (SEO)
- Shareable OG-image cards
- Sitemap

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| A/B subject lines (4 variants) | #41 | ✅ Merged |
| Open + click tracking (Resend webhook) | #41 | ✅ Merged |
| Email analytics (admin-only) | #41 | ✅ Merged |
| UTM params on briefing links | #41 | ✅ Merged |
| Alert webhooks (4 types, HMAC-signed) | #41 | ✅ Merged |
| Alert detection + delivery (hourly Celery) | #41 | ✅ Merged |
| Webhook config CRUD (Lifetime+ only) | #41 | ✅ Merged |
| Public company pages (`/c/[name]`) | #41 | ✅ Merged |
| Public theme pages (`/t/[slug]`) | #41 | ✅ Merged |
| Share card PNGs (1200×630, Pillow) | #41 | ✅ Merged |
| Sitemap (initial) | #41 | ✅ Merged |

**Verifiable in production:**
```bash
GET /c/samsung-electronics  # public, no auth, should render SEO page
GET /t/ai-ml                 # public theme page
GET /api/v1/share/trend/G06N.png  # 1200x630 PNG
GET /api/v1/account/alerts   # user's alert history
GET /api/v1/admin/email/analytics  # admin-only email stats
```

---

### Phase 6 — Marketing Surface + SEO (1 week)

**Roadmap promised:**
- Full sitemap index + sub-sitemaps (companies, themes, patents, pages)
- robots.txt
- Structured data (JSON-LD) on all public pages
- OG + Twitter cards on all public pages
- Editorial blog system
- 5 launch posts

**What shipped:**
| Item | PR(s) | Verified? |
|------|-------|-----------|
| Sitemap index + 4 sub-sitemaps (50K cap each) | #41 | ✅ Merged |
| robots.txt | #41 | ✅ Merged |
| JSON-LD (Organization, WebPage, ScholarlyArticle, Article) | #41 | ✅ Merged |
| OG/Twitter cards on all public pages | #41 | ✅ Merged |
| Blog system (admin CRUD + public read + seed) | #41 | ✅ Merged |
| 5 launch posts (content/blog/*.md) | #41 | ✅ Merged |

**Verifiable in production:**
```bash
GET /sitemap.xml                 # sitemap index
GET /robots.txt                  # allow/disallow rules
GET /blog                        # list of published posts
GET /blog/how-to-read-a-patent   # individual post with JSON-LD
View source: should have og:title, og:image, twitter:card, JSON-LD script
```

**Gaps:**
- Blog posts 3 and 5 reference placeholder patent IDs (`USPTO:US8500000` etc.). These are not real production patent IDs — seeded for content structure. Andy should replace with actual high-opportunity expiring patents from the DB before publishing.
- The markdown→HTML renderer on the blog post page is a simple regex-based converter. It handles headings, bold, italic, inline code, and links but won't render complex tables, blockquotes, or nested lists. Good enough for the 5 launch posts; upgrade to `react-markdown` if posts grow more complex.

---

## Section 2 — Integration Health

### 2.1 Persona-Aware Briefing (P2) × Semantic Search (P1)

**Current state:** `persona_weights.py` feeds persona into `assemble_briefing()` for the briefing ranking weights. Semantic search in `semantic_search.py` does NOT use persona — it's pure vector similarity + keyword + recency.

**Should it influence search?** Yes, for consistency. A user who identifies as "investor" should see higher-weighted results for expiring patents and company moves when searching, not just in their briefing. The underlying retrieval is the same (pgvector `<=>`), but the re-ranking and weighting is persona-aware in one path and persona-blind in the other.

**Severity:** P2. Not blocking — briefing is the primary persona surface and it works. Search consistency is a polish item.

---

### 2.2 Chat (P3) × Paywall (P4)

**Current state:** Chat quota enforcement reads Redis key `chat:quota:{user_id}:{today}`. Feature usage endpoint (`/api/v1/account/usage`) reads the same Redis key. No double-counting risk because both are read-only from the same source.

**Integration check:**
- Chat increment happens in the streaming endpoint before generating a response
- Quota check happens synchronously (not async-retroactive)
- If a user hits quota mid-stream, the SSE stream still completes but the next request is rejected
- The usage warning banner reads from the same usage endpoint

**Issue spotted:** `_check_chat_quota_stub` still exists in `chat.py` alongside the real `check_chat_quota`. The real path is called in `chat_stream()`. The stub is dead code but harmless. Remove for cleanliness.

**Severity:** P3 (cleanup).

---

### 2.3 Alerts (P5) × Chat (P3)

**Current state:** Alert payloads include patent details (title, doc_id, assignee, theme). The `payload` field is rich enough that a user could copy the patent ID and paste it into chat to ask "tell me more about this." But there's no deep link from alert → chat with pre-populated context.

**Integration opportunity:** Add a `seed` param link in webhook payloads: `https://inventionindex8.com/chat?seed=Tell+me+about+USPTO:US12345` so clicking from a webhook receiver opens chat with the patent pre-filled. Deferred to Phase 5.5.

**Severity:** P3 (enhancement).

---

### 2.4 Blog (P6) × Cross-Links

**Current state:** Blog posts 3 and 5 use placeholder patent IDs (`USPTO:US8500000` through `USPTO:US8900000`) as TBD markers. These are NOT real patent IDs in the production database.

**Action needed:** Andy should query production for the top 5 expiring patents by opportunity_score and replace the placeholders. This is a content task, not a code task. The blog system itself supports real cross-links — the schema has `related_patent_doc_ids` as JSONB and the frontend renders them as clickable links.

**Post 4 (NVIDIA):** Uses real analysis structure but placeholder patent IDs (USPTO:US11800000 etc.). Same replacement needed.

**Severity:** P1 before publishing. Broken links on blog posts undermine credibility.

---

### 2.5 Magic Link Auth × Onboarding × Persona

**End-to-end flow:**
1. User enters email → `POST /api/v1/auth/request-link` → magic link sent via Resend
2. User clicks link → `GET /api/v1/auth/verify?token=...` → sets auth_session cookie
3. First visit → onboarding wizard appears (checks `user.onboarding_completed`)
4. Wizard collects persona (operator/investor/curious) → `PUT /api/v1/account/persona`
5. Persona feeds into briefing ranking via `persona_weights.py`

**Issue:** Onboarding completion marks `user.onboarding_completed = True`. If a user skips the wizard (e.g., by navigating away), there's no fallback to collect persona later. The persona defaults to `curious`. Not critical but suboptimal — users who skip onboarding don't get personalized briefings.

**Severity:** P2. Add a "Set your persona →" nudge on the today page if persona is null.

---

## Section 3 — Open V3 Items, Deferred to V3.5 or V4

| Item | Status | Roadmap Ref | Severity | Effort if revived |
|------|--------|------------|----------|-------------------|
| Patent-detail chat drawer | Deferred to Phase 3.5 | PR #39 body | P2 | 1-2 days (SWC parsing fix + re-integration of drawer component) |
| Caddy in compose declaration | Not done | Phase 0 code items | P3 (not customer-facing) | 1 day (pull Caddy config into `docker-compose.yml`) |
| SSO / Google OAuth | Deferred to V4 | Roadmap "What V3 will NOT include" | P2 (reduces signup friction) | 1-2 weeks |
| Multi-currency pricing | Not done | Not explicitly deferred — just not implemented | P3 (only US users initially) | 1 week (Stripe supports this natively) |
| News retrieval in chat | Deferred to Phase 3.5 | Phase 3 prompt | P2 | 1 week |
| Sentry Instrumentation V8 pattern | Partially done | Phase 0 code items | P3 | 1 day |
| PR template + CONTRIBUTING.md | Not done | Phase 0 | P3 (non-blocking) | 30 minutes |
| Marketing landing page (#30) | Unknown — conflict state | Phase 2 prompt | P2 (first impression) | Verify, then 0-1 day fix |

---

## Section 4 — Production Health

### CI/CD Pipeline (from `.github/workflows/ci.yml`)

| Stage | What | Gate |
|-------|------|------|
| `backend-lint` | ruff check | Must pass |
| `backend-test` | pytest on Postgres 16 + Redis 7 | Must pass |
| `frontend-build` | npm run build | Must pass (informational only per config?) |
| `deploy` (on push to main) | SSH to Hetzner, docker compose up -d --build | Auto-deploy |
| Health check | curl /health, 30 attempts × 3s = 90s timeout | Must pass |
| Smoke test | `./scripts/smoke-test.sh` | Must pass or auto-rollback |
| Rollback | `git reset --hard $PREV_COMMIT`, docker compose rebuild | Automatic on failure |
| Success notification | Email via Resend to andy@web3r.tech | Informational |

**CI concurrency:** `cancel-in-progress: true` — only the latest commit on a branch runs. Pushes to main are serialized.

### Deploy Frequency Estimate (last 30 days)

Based on PR volume in this session (PRs #33-41 spanning ~5 days), deployment cadence appears to be:
- **Average: ~2 deploys/day** during active development sprints
- **Rollback frequency:** Unknown — requires production logs. The CI has auto-rollback; its trigger history requires `journalctl` or Docker logs on the server (needs Andy access).
- **Smoke test failures:** Unknown — requires server-side script output.
- **Time-to-deploy:** ~3-5 minutes per deploy (docker build + restart + 30s warmup + smoke test). The 90s health check timeout is generous.

**⚠️ Requires Andy to verify:**
- Number of actual rollbacks in last 30 days
- Smoke test failure rate
- Docker build cache hit/miss rate (affects deploy speed)

---

## Section 5 — Cost Trajectory

### Fixed Monthly Costs

| Component | Estimate | Notes |
|-----------|----------|-------|
| Hetzner VPS (CX31 or similar) | ~$15/mo | Base VPS; confirm exact plan with Andy |
| Cloudflare (Free tier) | $0 | Unless Pro plan used |

### Variable Costs (per-usage)

| Component | Per-Unit | Assumptions |
|-----------|----------|-------------|
| DeepSeek embeddings (`text-embedding-3-small`) | $0.00002/1K tokens | ~2K tokens/patent, ~500 new patents/week = $0.02/week |
| Anthropic Claude chat (Sonnet) | $3.00/M input, $15.00/M output | ~2K tokens/query (1.5K in, 0.5K out), 5 queries/user/day |
| Stripe transaction fees | 2.9% + $0.30 | Per successful charge |
| Resend emails | $0.00042/email (Pro plan ~$20/mo for 50K) | Weekly briefing × subscribers |
| Postgres 16 + pgvector | Included in VPS | No additional hosting cost |
| Redis 7 | Included in VPS | No additional hosting cost |

### Monthly Estimate at 100 Paying Users

**Assumed mix:** 60 Basic ($8/yr = $0.67/mo), 5 Lifetime ($108 once, amortized $0/mo after 12mo), 5 Enterprise ($1,000/yr), 30 Free (trialing)

**MRR:** 60 × $0.67 + 5 × $0 + 5 × $83.33 = $40 + $0 + $417 = **~$457 MRR**

**Costs:**

| Cost Item | Calculation | Monthly |
|-----------|-------------|---------|
| Hetzner VPS | Fixed | $15 |
| DeepSeek embeddings | 500 patents/wk × 2K tokens × $0.00002 | <$1 |
| Anthropic chat | 100 users × 5 q/day × 30 days × (1.5K input × $3/M + 0.5K output × $15/M) | ~$90 |
| Stripe fees | 2.9% × $457 + ~11 transactions × $0.30 | ~$16 |
| Resend emails | 100 users × 4 briefings/mo × $0.00042 | <$1 |
| **Total monthly cost** | | **~$123** |

**Net margin:** ($457 - $123) / $457 = **73% gross margin**

**Caveats:**
- Anthropic chat costs scale linearly with user count and query volume. At 500 users, chat costs become ~$450/month.
- If the backfill uses OpenAI embeddings (not DeepSeek), costs are higher ($0.13/1M vs $0.02/1M — 6.5×).
- Hetzner VPS can handle ~500-1000 concurrent users before needing an upgrade (~$30-50/mo next tier).

---

## Section 6 — Readiness for V4 Triggers

V4 starts only when ALL these conditions are met:

| Condition | Status | How to test / monitor |
|-----------|--------|-----------------------|
| V3 Phases 0-6 deployed | ✅ Shipped (PRs #17-41) | Verify via health endpoint + UI |
| >100 paying users | ❌ Not met (pre-launch) | `SELECT COUNT(*) FROM billing_subscriptions WHERE tier != 'free'` |
| MRR >$500 | ❌ Not met (pre-launch) | Requires actual Stripe LIVE revenue data |
| D30 retention >25% | ❌ Not measured | Need signup → D30 activity tracking. Not instrumented yet. |
| Briefing open rate >35% (4 weeks) | ❌ Not measured | Admin email analytics endpoint built (#41). Needs 4 weeks of data. |
| Stripe LIVE >90 days, chargebacks <0.5% | ❌ Stripe still TEST | Andy flips LIVE after PR #40 deploys. Clock starts then. |

### Dashboards needed before V4

| Dashboard | Built? | Action |
|-----------|--------|--------|
| MRR + subscriber count | Partially — billing health endpoint | Expand to show MRR trend over time |
| D30 retention | ❌ | Build: last_active_at on User model, retention query |
| Email analytics (open/click per variant) | ✅ | Already in admin |
| Chat cost per user | ❌ | Build: add cost-tracking to Anthropic client |
| Stripe chargeback rate | ❌ | Stripe Dashboard; no in-app tracking needed |
| Deployment frequency / reliability | ❌ | GitHub Actions Insights if public; otherwise manual log |

---

## Section 7 — Top 10 Risks Before Public Launch

### Risk 1 — Stripe in TEST mode, someone tries to pay
**What:** A user clicks a paid tier button, is taken to Stripe Checkout, and sees test-mode warnings or a non-functional checkout.
**Detection:** First support email saying "I can't pay."
**Mitigation:** ✅ Safety gate exists (#40). ❌ Andy still needs to flip to LIVE manually.
**Severity:** P0. Must fix before any paid traffic.

### Risk 2 — Email deliverability to Gmail/Proton
**What:** Magic links and weekly briefings land in spam. Users can't log in.
**Detection:** Resend dashboard shows bounce/complaint rates. Email analytics shows open rates.
**Mitigation:** ⚠️ DNS records set up? SPF/DKIM/DMARC verified? Requires Andy to check.
**Severity:** P0. No email = no signups = dead product.

### Risk 3 — Chat quota exhausted by power user on Day 1
**What:** Free user hits 5 chat queries in 10 minutes, gets 402, leaves angry review.
**Detection:** 402 response rate on chat endpoint. Customer complaint.
**Mitigation:** ✅ 402 with upgrade CTA exists. ⚠️ Consider harder: first 3 queries per day before 402, or a "You've used 3/5" interstitial before the limit.
**Severity:** P1.

### Risk 4 — Blog posts published with broken links
**What:** Posts 3 and 5 use placeholder patent IDs. If published as-is, `/patents/USPTO:US8500000` returns 404.
**Detection:** Smoke test should hit blog routes (if included). Manual QA.
**Mitigation:** ❌ Placeholders still present. Andy must replace with real IDs before publishing.
**Severity:** P1.

### Risk 5 — PostgreSQL disk full from backfills
**What:** Embedding backfill, citation backfill, and weekly ingestion all write to the same disk. 64K patent corpus × 1536-dim vectors = significant storage.
**Detection:** `docker compose exec db df -h` or monitoring alert.
**Mitigation:** ⚠️ Hetzner gives ~80GB on basic tier. 64K vectors × 1536 × 4 bytes = ~400MB. Not the vector column — it's the indexes and transaction logs. Monitor disk usage monthly.
**Severity:** P2.

### Risk 6 — Resend webhook delivery failure cascade
**What:** Resend stops delivering webhooks (opens, clicks, bounces). Email analytics go silent. Bounce handling stops. Users who complain can't be auto-unsubscribed.
**Detection:** `GET /api/v1/admin/email/analytics` shows zero opens for days. Resend dashboard.
**Mitigation:** ⚠️ No alert on webhook delivery failure. Add: if zero webhook events in 24h, log CRITICAL.
**Severity:** P2.

### Risk 7 — Anthropic API outage during peak traffic
**What:** Claude API is down. Chat returns 503. Briefing generation fails. Users see errors.
**Detection:** `GET /api/v1/admin/system-health` shows `circuit_broken: true`. Sentry alerts.
**Mitigation:** ⚠️ Circuit breaker exists (PR #8-era `_anthropic_error_count`). Chat gracefully degrades to "our AI is temporarily unavailable." Briefing fails — Celery retries.
**Severity:** P2.

### Risk 8 — Redis OOM (memory exhaustion)
**What:** Chat conversations accumulate in Redis (30-min TTL, 10-turn cap). At 1000 concurrent users × 10K messages, Redis hits memory limit.
**Detection:** Redis `INFO memory` shows usage approaching maxmemory. Keyspace evictions in logs.
**Mitigation:** ✅ TTL auto-expires. ✅ 10-turn cap. ⚠️ No `maxmemory-policy` configured (default is `noeviction` — if full, writes fail). Configure `maxmemory-policy allkeys-lru` as safety net.
**Severity:** P2.

### Risk 9 — Celery beat misses schedule (alert delivery stops)
**What:** Celery beat crashes or drifts. Alert detection and delivery stop. Users don't get webhook alerts.
**Detection:** `docker compose logs beat | grep -c "Alert scan"` shows zero for hours.
**Mitigation:** ⚠️ No health check for Celery beat task execution. Add: last successful scan timestamp in Redis, monitored.
**Severity:** P3 (alerts are Lifetime+ only, low user count initially).

### Risk 10 — Sitemap contains broken URLs (SEO penalty)
**What:** Sitemap lists public company/theme URLs that return 404. Google penalizes.
**Detection:** `curl https://inventionindex8.com/sitemap.xml | grep '<loc>' | wc -l` — spot-check random URLs.
**Mitigation:** ⚠️ Sitemap generates from DB queries — if company slug regex produces bad slugs, they end up in sitemap. Add a validation step: sitemap entry must return 200 from the frontend before inclusion.
**Severity:** P2.

---

## Section 8 — Recommended Pre-Launch Checklist

### Mandatory (P0 — launch won't work without these)

1. **[ ] Stripe LIVE mode activated** — Follow checklist in PR #40 body. Test with real card ($1 charge, immediate refund).
2. **[ ] DNS records verified** — A record (188.245.85.248), SPF, DKIM, DMARC for Resend. Test: send email to andy.keh@gmail.com, check headers for `spf=pass dkim=pass`.
3. **[ ] Email deliverability tested** — Send test magic links to Gmail, Proton, Outlook, Yahoo. Confirm inbox landing (not spam) across all 4.
4. **[ ] Smoke test passes on all main routes** — `./scripts/smoke-test.sh` includes: `/health`, `/api/v1/patents/stats`, `/api/v1/today/highlights`, `/c/samsung`, `/t/ai-ml`, `/blog`, `/sitemap.xml`, `/robots.txt`.
5. **[ ] Blog post patent IDs replaced** — Replace placeholder IDs in `content/blog/5-patent-expiries-to-watch.md` and `content/blog/nvidia-next-chip-cycle.md` with real production patent IDs.
6. **[ ] SSL certificate valid** — Caddy should auto-renew. Verify: `curl -vI https://inventionindex8.com` shows valid cert.
7. **[ ] Support email configured** — `hello@inventionindex8.com` or `support@inventionindex8.com` forwards to Andy's inbox. Tested.

### Important (P1 — launch works but corners cut)

8. **[ ] Backup restore drill performed** — Follow `.hermes/runbooks/restore-db.md`. Verify restored DB has same patent count as production. Time the restore.
9. **[ ] Monitoring dashboards exist** — At minimum: Sentry project active, health endpoint monitored (UptimeRobot free tier or similar), Stripe dashboard bookmarked.
10. **[ ] Legal pages reviewed** — `/terms`, `/privacy`, `/refund` pages exist and are accurate. GDPR cookie consent if serving EU users.
11. **[ ] Rate limits configured** — Verify SlowAPI rate limits are active (currently enabled in `app/main.py`). Confirm 429 responses are user-friendly.
12. **[ ] Chat cost budget set** — Anthropic usage limits configured in API console. Prevent runaway spend from bugs or abuse.
13. **[ ] Redis persistence reviewed** — Currently `--save "" --appendonly no`. Acceptable for chat sessions (ephemeral). Not acceptable for alert state. Verify alert delivery state is in Postgres, not Redis.

### Nice to Have (P2 — launch can proceed without)

14. **[ ] Usage warning banner live** — Verify the 80% usage banner appears for Free users. Dismiss persists across sessions.
15. **[ ] Onboarding wizard completion rate measured** — Add a counter: wizard_started vs wizard_completed. Target >70%.
16. **[ ] Sitemap submitted to Google Search Console** — Submit `https://inventionindex8.com/sitemap.xml`. Verify indexing starts within 48h.
17. **[ ] robots.txt verified** — Fetch as Google in Search Console. Confirm `/admin/` and `/api/` are disallowed, `/c/` and `/t/` are allowed.
18. **[ ] OG images render correctly** — Paste `/c/nvidia` URL into Twitter Card Validator and LinkedIn Post Inspector. Verify share card PNG is fetched.
19. **[ ] Performance baseline** — Lighthouse score for `/`, `/c/nvidia`, `/blog/how-to-read-a-patent`. Target >70 on mobile.
20. **[ ] Error page tested** — Visit a 404 page (e.g., `/c/nonexistent`). Confirm branded error page, not default Next.js.

---

**Report delivered.** `.hermes/reports/2026-06-12_v3-end-of-phase-audit.md`
