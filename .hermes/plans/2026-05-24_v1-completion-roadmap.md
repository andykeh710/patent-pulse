# Patent Pulse — V1 Completion Roadmap

**Author:** Claude session 2026-05-24
**Status:** Ready to hand to Hermes.
**Reading order:** Section 0 (status) → Section 1 (Sprint 6 pre-flight) → Sections 2-5 (sprints in order) → Section 6 (production readiness) → Section 7 (legal/launch).

The list below is what's left to call Patent Pulse "V1 done." Each item
is sized small enough for Hermes to execute chunk-by-chunk. Items
marked **BLOCKING** must be resolved before the dependent sprint can
start.

---

## 0. Where we are today (snapshot)

| Capability | Status |
|---|---|
| Patent ingestion (USPTO grants + applications, EPO, WIPO) | ✓ shipped |
| Patent detail page (claims, family, citations, legal, figures) | ✓ shipped |
| Expiry Radar + opportunity scoring | ✓ shipped (Sprint 2C) |
| Filing trends + assignee intelligence | ✓ shipped (Sprint 4) |
| Trend narratives (Sonnet) | ✓ shipped (Sprint 4) |
| Patent figure link-out | ✓ shipped (Sprint 4.5) |
| Usage signals (evidence + scoring + narrative) | ✓ shipped (Sprint 5) |
| User-created topics ("Themes") | ✓ shipped (Phase 3) |
| LinkedIn post generation | ✓ shipped (Phase 4.1) |
| Pytest infrastructure | ✓ 227 passed, 1 xfailed, 1 xpassed, 0 failed |
| Embedding backfill | running (~17K / 54K, climbing ~30K/hr) |
| Expiry-cohort embedding backfill | running (newly added) |
| Beat schedules for tag/score/why_now/opportunity_narrative backfills | ✓ added 2026-05-24 |
| Server-side idle-in-transaction guard | ✓ 60s timeout |
| Haiku→Sonnet for structured narratives | ✓ swapped |

**Outstanding code-level deferrals:**
- A4 — USPTO citation ingestion (documented in `uspto_client.py:107`)
- 1 LLM-variability xfail (`test_narrative_uses_patent_context`) — flaky 3-5%

**Outstanding sprints:** 6, 7, 8.

---

## 1. Pre-Sprint-6 pre-flight (BLOCKING — must complete first)

These are operator tasks, not code. The user does them; Hermes confirms.

| # | Task | Why | Effort |
|---|---|---|---|
| P1 | **Rotate the Resend API key.** The one shared in chat is compromised. | Security | 2 min |
| P2 | Set `RESEND_API_KEY` in `.env` to the new key. | Sprint 6 dependency | 1 min |
| P3 | Decide and verify the email sending domain in Resend (e.g. `alerts.patentpulse.dev`). Add SPF + DKIM DNS records. | Without domain verification, Resend production sends will be blocked. | 30-60 min (DNS propagation) |
| P4 | Set `EMAIL_FROM_ADDRESS` in `.env` (e.g. `alerts@<verified-domain>`). | Sprint 6 dependency | 1 min |
| P5 | Set `EMAIL_DEV_RECIPIENT` in `.env` to your own email (where dev-mode messages land). | Sprint 6 dev mode | 1 min |
| P6 | Set `AUTH_SECRET_KEY` in `.env`: `openssl rand -base64 32`. | Magic-link auth + session JWT | 1 min |
| P7 | Decide on `MAGIC_LINK_BASE_URL` (e.g. `http://localhost:3000` for dev; production URL later). | Sprint 6 dependency | 1 min |
| P8 | Commit the current uncommitted changes from this session before Hermes starts touching code. | Prevent merge conflicts. | 5 min |

---

## 2. Sprint 6 — User Alerts & Newsletters (9 chunks)

**Plan:** [.hermes/plans/2026-05-24_sprint-6-alerts-newsletters-impl.md](.hermes/plans/2026-05-24_sprint-6-alerts-newsletters-impl.md)
**Scope doc:** [.hermes/plans/2026-05-24_sprint-6-alerts-newsletters-scope.md](.hermes/plans/2026-05-24_sprint-6-alerts-newsletters-scope.md)

Locked decisions:
- Approach C — hybrid (instant alerts + weekly Sonnet briefings)
- Resend for email
- Magic-link auth
- Dedicated `topic_subscriptions` table
- `EMAIL_SEND_MODE` defaults to `dev` (rewrites recipient to dev email)

Chunks (each lands as a separate commit):

| # | Chunk | LOC | Dependencies |
|---|---|---|---|
| S6-1 | Migrations 0012-0014 + ORM models | ~120 | P1-P7 done |
| S6-2 | Magic-link auth backend (token issue + verify + JWT session) | ~250 | S6-1 |
| S6-3 | Magic-link auth frontend (login form, verify page, AuthContext) | ~150 | S6-2 |
| S6-4 | Subscription API (CRUD + ownership + unsubscribe-via-signed-token) | ~180 | S6-1, S6-2 |
| S6-5 | Resend email module + Jinja templates + send-mode guard | ~100 | P3, P4, S6-1 |
| S6-6 | Instant-alert hook in theme_matcher + Celery delivery task | ~80 | S6-4, S6-5 |
| S6-7 | Weekly Sonnet briefing (`ai/weekly_digest.py`) + Sunday beat fan-out | ~200 | S6-5 |
| S6-8 | Frontend subscription UI (topic page subscribe panel + /account page) | ~180 | S6-3, S6-4 |
| S6-9 | Tests + language audit + production-mode acknowledgement gate | ~250 | all above |

**Sprint 6 success criteria:**
- A real user can sign in via magic link, subscribe to a topic, receive
  instant alert on next matching patent, receive Sunday digest.
- All emails carry an unsubscribe link.
- Default send mode is `dev` (no broad sends without user flipping
  `EMAIL_SEND_MODE=production` + `EMAIL_PRODUCTION_ACKNOWLEDGED=true`).
- `pytest -q` shows 0 new failures; new tests for auth, subscriptions,
  send-mode, weekly_digest validators.

---

## 3. Sprint 7 — SaaS Readiness (NOT designed yet — needs brainstorming)

**Goal per AGENTS.md priority #6:** auth, billing, quotas, exports.

### 3a. What it covers
- Production-grade auth (extends Sprint 6 magic-link with optional
  OAuth, password reset, email verification)
- Stripe integration (**TEST MODE ONLY** until explicit approval per
  AGENTS.md)
- Tier model: Free / Pro (TBD pricing)
- Per-user quotas (API calls, alert sends, weekly digests, exports)
- Patent export endpoints (CSV / JSON / PDF)
- Billing portal page
- Admin dashboard (user list, manual tier override, send-mode toggle)

### 3b. Decisions needed before plan-out
| # | Question | Options |
|---|---|---|
| S7-Q1 | Pricing model? | Per-seat / per-alert / per-export / flat tier |
| S7-Q2 | Free tier limits? | E.g. 5 topics, 10 alerts/week, 1 export/month |
| S7-Q3 | Stripe integration depth? | Hosted Checkout vs Stripe Elements (own UI) |
| S7-Q4 | Export formats for V1? | CSV only, or CSV + PDF + JSON |
| S7-Q5 | OAuth or magic-link only? | Magic-link is sufficient; OAuth is polish |

### 3c. Expected chunks (8-10, similar to Sprint 6)
- Migrations: `subscriptions_billing` table (Stripe customer/sub IDs),
  `quotas` table, `exports` table
- Stripe webhook receiver
- Quota middleware (FastAPI dependency)
- Export endpoint(s) — wraps existing list endpoints with CSV/PDF
  rendering
- Billing portal frontend
- Admin dashboard frontend
- Tests + language audit + Stripe TEST MODE verification

**Estimated effort:** ~2,000 LOC. Plan-out can happen mid-Sprint-6.

---

## 4. Sprint 8 — Content Generation (PARTIAL — needs scoping)

**Goal per AGENTS.md priority #7:** "downstream packaging only" — newsletters, reports, LinkedIn posts.

### 4a. What's done
- LinkedIn post generation (Phase 4.1, shipped) — `content_generator.py`
  + `generate_linkedin_post` endpoint
- Weekly digest (will ship in Sprint 6.7)

### 4b. What's left

| # | Item | Effort |
|---|---|---|
| S8-1 | Newsletter packaging — bundle weekly digest content into a public newsletter view (sharable URL) | ~200 LOC |
| S8-2 | PDF report generator (single patent → branded PDF with figures, claims, expiry, usage signals, suggested opportunities) | ~400 LOC |
| S8-3 | Audit Sprint 4.5 `content_generator` for Haiku envelope risk (deferred from A3 — low priority, low risk per Sprint 4 doc) | ~50 LOC |
| S8-4 | Editorial review queue (optional): drafts go to in-app inbox for human approval before send | ~300 LOC (out of scope if S6 dev-mode is sufficient) |

Sprint 8 is the lightest of the remaining sprints. Could be done in
1-2 sittings after Sprint 7.

---

## 5. Outstanding code deferrals

| # | Item | Effort | When |
|---|---|---|---|
| D1 | A4 — USPTO citation ingestion. Required for full usage signals (currently similarity-only). Per `uspto_client.py:107` TODO. | ~400 LOC + ~15hr backfill | Sprint 6.5 or alongside Sprint 7 |
| D2 | A4 forward-citations backfill task — extracts via `PatentBiblio.forward_citations` for all 54K historical patents. Rate-limit aware. | ~150 LOC + ~15hr runtime | After D1 |
| D3 | `test_narrative_uses_patent_context` — flaky LLM-keyword assertion. Either tighten the assertion or mock the LLM response. | ~30 LOC | Any time |
| D4 | content_generator Haiku audit (A3 deferred — low risk but unverified). Run a sample LinkedIn post generation and inspect content_json structure. | ~30 min investigation | Sprint 8 |
| D5 | Live-DB idle-in-transaction connections: 60s server timeout is a workaround. Root fix is engine teardown across asyncio.run boundaries. | ~50 LOC | Post-V1 |

---

## 6. Production readiness (cross-cutting — needed before public launch)

These don't fit neatly into a sprint but are blocking for any
production use.

| # | Item | Owner | Effort |
|---|---|---|---|
| PR1 | Pick a hosting target — Fly.io / Railway / Render / Hetzner — for FastAPI app | User | half day |
| PR2 | Managed Postgres (Supabase / Neon / Crunchy / RDS) with pgvector enabled. Migrate dev data or seed fresh. | User | half day |
| PR3 | Redis hosting (Upstash / Railway add-on / Fly.io Redis) for Celery broker | User | 1 hour |
| PR4 | Worker hosting — Celery worker + beat processes on the same or separate platform | User | 1 hour |
| PR5 | Domain + DNS — buy domain, set A/CNAME records, enable HTTPS (Cloudflare / hosting native) | User | 2 hours |
| PR6 | Resend domain verification (SPF + DKIM + DMARC). Cross-listed with P3. | User | 1 hour |
| PR7 | Environment secrets management — move `.env` to host secrets store (Fly secrets, Railway env, etc.) | User + Hermes | 1 hour |
| PR8 | Sentry or equivalent error tracking — wire SDK on backend + frontend | Hermes | ~50 LOC + setup |
| PR9 | Structured logging — JSON logs to stdout, parseable by host log viewer | Hermes | ~100 LOC |
| PR10 | DB backups — daily automated, off-host retention | User (depends on PR2 choice) | 1 hour |
| PR11 | Healthchecks — extend existing `/health` to include DB + Redis + Resend reachability | Hermes | ~50 LOC |
| PR12 | Rate limiting at API layer — middleware that throttles per-IP / per-user. Not Stripe-tier quotas; that's Sprint 7. | Hermes | ~80 LOC |
| PR13 | Docker images for production — multi-stage build, non-root user, small image size | Hermes | ~30 LOC Dockerfile changes |
| PR14 | CI pipeline — GitHub Actions running `pytest -q` + `npm run build` + a basic e2e smoke test on every PR | Hermes | ~150 LOC YAML |

---

## 7. Legal / compliance / launch (post-tech, pre-public)

| # | Item | Owner | Notes |
|---|---|---|---|
| L1 | Privacy Policy | User (or template + counsel) | Required for any data collection + email sending |
| L2 | Terms of Service | User | Limits liability, especially around patent-data claims |
| L3 | GDPR data deletion endpoint | Hermes | DELETE /api/v1/account/me — cascades to subscriptions, deliveries, magic links |
| L4 | Cookie / tracking consent banner | Hermes | If any analytics added |
| L5 | Patent data attribution display | Hermes | "Source: USPTO / EPO" footer on patent detail pages (partial; double-check coverage) |
| L6 | Marketing landing page | User | Single-page; explains what Patent Pulse does |
| L7 | Onboarding flow — first-login walkthrough (create your first topic, subscribe) | Hermes | ~200 LOC |
| L8 | Help / FAQ docs | User | Minimum: "How is usage_signal_score computed?", "What does expiry confidence mean?", "How do I unsubscribe?" |
| L9 | Pricing page (depends on S7-Q1/Q2) | User | After Sprint 7 decisions |
| L10 | First customer outreach plan | User | Out of scope here |

---

## 8. Suggested execution order (top-to-bottom for Hermes)

1. **Pre-flight: P1-P8** (user does these, then commits the current
   uncommitted changes)
2. **Sprint 6 — Chunks S6-1 through S6-9** (Hermes builds; user commits
   each chunk)
3. **D1 + D2 (Sprint 6.5)** — citation ingestion + backfill. Closes the
   biggest open scope from the audit.
4. **Sprint 7 brainstorm + plan-out** (interactive — pick pricing, tier
   limits, OAuth-or-not) → then build Sprint 7
5. **Sprint 8** — newsletter packaging + PDF report
6. **Production readiness — PR1 through PR14** (interleaves with
   sprints; PR1-PR7 needed before any public launch)
7. **Legal / launch — L1 through L10**

---

## 9. Estimated total effort

| Phase | Effort estimate |
|---|---|
| Pre-flight P1-P8 | 1-2 hours (user) |
| Sprint 6 (9 chunks, ~1,500 LOC) | 1-2 days of focused Hermes work |
| D1 + D2 (citation ingestion) | 1 day Hermes + ~15h compute |
| Sprint 7 brainstorm + 10 chunks | 2-3 days |
| Sprint 8 (3 chunks) | 1 day |
| Production readiness | 2-3 days mixed user + Hermes |
| Legal / launch | variable — counsel-dependent |
| **Total to public V1** | ~2 weeks Hermes engineering + parallel user setup |

---

## 10. Quality gates carried across all remaining sprints

These are non-negotiable per AGENTS.md and prior session lessons:

- `pytest -q` must pass with 0 failures (no `--ignore`). Count + baseline
  diff reported in every chunk verification.
- Language audit — `free to use`, `public domain`, `is used by`,
  `definitely used` return zero matches in changed files.
- Confidence labels + "verify with official registers" caveats on every
  expiry-related surface.
- All LLM output cached as `AIArtifact` + labelled with `AISourceFooter`.
- Stripe always in TEST MODE until explicit user approval.
- No broad email sends without `EMAIL_SEND_MODE=production` flipped by
  user.
- DEVIATION DETECTED protocol — Hermes flags Options A/B/C and waits;
  does not silently work around.
- User commits all code; Hermes never runs git commands.
- Frontend changes require browser smoke test before declared done.
- No `--no-verify`, no `as any` casts to silence type errors, no test
  deletion to make a suite green.
