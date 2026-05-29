# Patent Pulse V1 — Code Complete (2026-05-29)

Every code-side V1 item from the completion roadmap has shipped.
What remains is user-side ops only.

## Journey

| When | What | Final state |
|---|---|---|
| 2026-05-24 (session start) | Mid-Sprint 5 with audit-sprint debt: 11 xfails, 5 deviations across earlier sprints, 0 embeddings, 0 citations | Sprint 5 closed, A1-A5 audit done, embeddings backfill running |
| 2026-05-25 | Sprint 6 (alerts + newsletters) | Magic-link auth, instant alerts, weekly Sonnet digests, /account + /admin pages |
| 2026-05-25 | Sprint 6.5 (citation ingestion) | patent-client SDK wired, backfill task every 5 min, citations populating |
| 2026-05-26 / 27 | Sprint 7 (SaaS readiness) | 4-tier billing (Free/Basic/Lifetime/Enterprise), Stripe TEST MODE webhooks, quota middleware, CSV + PDF exports, API keys, admin dashboard |
| 2026-05-27 / 28 | Production-readiness (PR8-PR14) | Sentry, structlog JSON logs, healthchecks, rate limiting, multi-stage Dockerfile, GitHub Actions CI |
| 2026-05-28 / 29 | Legal (L3 + L5) | GDPR account deletion endpoint, source attribution component |

## Numbers

| Metric | Value |
|---|---|
| Tests at session start | 213 passed, 11 xfailed |
| Tests at V1 code complete | **341 passed, 3 xfailed, 0 failed** |
| Sprint-by-sprint LOC | Sprint 6: 4,015 · Sprint 7: 2,453 · Production+Legal: ~1,200 |
| Migrations 0011 → | **0020** (9 new migrations) |
| Frontend pages added | /login, /login/verify, /account, /account/billing, /admin, /unsubscribed, /newsletter (deferred), /themes/[id] |
| Backend endpoints added | 22 (auth, billing, subscriptions, exports, reports, api_keys, admin, account, health probes) |

## Required env vars for production

Must be set before `EMAIL_SEND_MODE=production` or any paid traffic:

| Var | Purpose | Set in V1? |
|---|---|---|
| `AUTH_SECRET_KEY` | Magic-link JWT signing (HS256). 32+ bytes. | YES |
| `MAGIC_LINK_BASE_URL` | Base URL embedded in magic links. | YES |
| `RESEND_API_KEY` | Email API. | YES |
| `EMAIL_FROM_ADDRESS` | Sender address, must be in Resend-verified domain. | YES |
| `EMAIL_DEV_RECIPIENT` | Target for dev-mode emails. | YES |
| `EMAIL_SEND_MODE` | `dev` / `dry_run` / `production`. Defaults to dev. | YES |
| `EMAIL_PRODUCTION_ACKNOWLEDGED` | Must be `"true"` for production mode. App refuses to start otherwise. | YES (gate) |
| `STRIPE_API_KEY` | `sk_test_...` only. App refuses to start on `sk_live_`. | YES |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret. | YES |
| `STRIPE_PRICE_ID_BASIC` | Annual $8 subscription. | YES |
| `STRIPE_PRICE_ID_LIFETIME` | One-time $108 payment. | YES |
| `STRIPE_PRICE_ID_ENTERPRISE` | Annual $1000 subscription. | YES |
| `OPENAI_API_KEY` | Embeddings (text-embedding-3-small). | YES |
| `ANTHROPIC_API_KEY` | All AI narratives (Sonnet, per A3 audit). | YES |
| `USPTO_API_KEY` | USPTO ingestion. | YES |
| `SENTRY_DSN` | Backend error tracking. Silently noops if unset. | Recommended |
| `NEXT_PUBLIC_SENTRY_DSN` | Frontend error tracking. Silently noops if unset. | Recommended |
| `RELEASE_SHA` | Sentry release tagging. Populated by CI on deploy. | Recommended |

## Migration ledger (0011 → 0020, all in chronological order)

| # | Purpose |
|---|---|
| 0011 | Sprint 5 usage_signals tables |
| 0012 | Sprint 6 topic_subscriptions |
| 0013 | Sprint 6 auth_magic_link_tokens |
| 0014 | Sprint 6 email_deliveries |
| 0015 | Sprint 6 TIMESTAMPTZ conversions |
| 0016 | Sprint 7 billing_subscriptions |
| 0017 | Sprint 7 api_keys |
| 0018 | Sprint 7 exports |
| 0019 | Sprint 7 users.tier column |
| 0020 | L3 nullable user_id / created_by for GDPR anonymization |

## Beat-scheduled background tasks

All run in Celery beat:

| Schedule | Task | Purpose |
|---|---|---|
| `*/2 min` | embeddings.batch_generate_embeddings | Backfill embeddings (1000/batch) |
| `:5,15,25,35,45,55` | embeddings.batch_generate_embeddings (prioritize_expiring) | Embed expiry-window cohort |
| `:15 hourly` | backfill_usage_signals.batch_backfill_usage_signals | Compute usage signal scores |
| `*/5 min` | backfill_citations.batch_backfill_citations | USPTO forward-citation backfill |
| `:20 hourly` | tag.batch_tag_patents | Patent tagging |
| `*/15 min` | opportunity.batch_score_opportunity | Opportunity scoring (no LLM) |
| `:25 hourly` | why_now.batch_why_now | Why-now narratives (Sonnet) |
| `:35 hourly` | opportunity_narrative.batch_opportunity_narrative | Opportunity narratives (Sonnet) |
| `Sun 7am` | send_weekly_digest.fan_out_weekly_digests | Per-user weekly briefing |
| (event-driven) | send_instant_alert | Fires on theme_matcher match |
| (existing) | Various ingestion + family resolution + summary tasks | Phase 1 work |

## What's left (you-side ops, ~1-2 days)

| # | Item | Effort | Where |
|---|---|---|---|
| O1 | Stripe TEST MODE: create 3 Products + Prices in dashboard, copy IDs to `.env` | 15 min | dashboard.stripe.com (toggle Test mode top-right) |
| O2 | Resend domain verification: add sending domain, add SPF/DKIM/DMARC DNS records, wait for propagation | 30-60 min | resend.com + your DNS provider |
| O3 | Generate strong `AUTH_SECRET_KEY` (`openssl rand -base64 32`) | 1 min | local |
| O4 | Buy/configure production domain | 30 min | any registrar |
| O5 | Pick hosting platform (Fly.io / Railway / Render recommended for Docker-friendly + Postgres + Redis) | half day | platform of choice |
| O6 | Managed Postgres with pgvector enabled (Supabase / Neon / Crunchy Bridge / RDS) | half day | platform of choice |
| O7 | Redis hosting (Upstash / Railway add-on / Fly Redis) | 1 hour | platform of choice |
| O8 | Worker hosting (separate Celery worker + beat services) | 1 hour | same platform as backend |
| O9 | Domain + HTTPS (Cloudflare in front OR platform-native TLS) | 2 hours | DNS + platform |
| O10 | Move secrets from `.env` to host secrets store | 1 hour | platform secrets manager |
| O11 | DB backups (daily, off-host retention) | 1 hour | platform DB add-on |
| O12 | Set `SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN` for live error tracking | 15 min | sentry.io free tier |
| O13 | First production deploy + smoke test the magic-link → subscribe → upgrade → CSV export flow end-to-end | half day | the new deploy |
| O14 | Flip `EMAIL_SEND_MODE=production` + `EMAIL_PRODUCTION_ACKNOWLEDGED=true` | 1 min after smoke | host secrets |

## Deferred to V1.1 (don't let scope creep grab them)

From the close-out reports of each sprint:

- Sprint 6: cookie banner (L4) — only if you add analytics; SQLAlchemy log duplication; Resend healthcheck "skipped" semantics; 1 flaky LLM-keyword test
- Sprint 7: tier-aware rate limits (currently uniform 60/min); Redis-backed slowapi storage; sourcemap upload to Sentry; pytest 9.0.3 vs ^8.3 lock drift; SQLAlchemy server_default constraint name drift (mitigated by L3 schema-drop conftest)
- Sprint 8 (entirely deferred): newsletter public-URL view, PDF report polish, editorial review queue
- D1/D2 historical citation backfill — running in background, completing gradually
- ESLint frontend cleanup (~14 unused-var warnings, none failing CI)
- OAuth (Google/GitHub) — magic-link is sufficient
- Multi-currency / tax ops for non-US customers

## V1 launch checklist (final ordered sequence)

1. ✅ All code shipped (this doc)
2. ⏳ CI green on `7774541` (the L5 commit — verify in GitHub Actions)
3. ⏳ Ops items O1-O11 (parallelize as much as possible)
4. ⏳ First production deploy (O13)
5. ⏳ End-to-end smoke test on production:
   - Sign up via magic link
   - Create a topic
   - Receive instant alert (will arrive at `EMAIL_DEV_RECIPIENT` for dev-mode confirmation)
   - Upgrade via Stripe TEST MODE checkout
   - Verify tier flips after webhook
   - Run a CSV export
   - Run a PDF report (Lifetime+)
   - Create + revoke an API key
   - Delete account → verify cascade
6. ⏳ Flip `EMAIL_SEND_MODE=production` (O14)
7. ⏳ Flip Stripe live keys (when you're ready to take real money — gate on `sk_test_` → `sk_live_` requires removing the startup-refuse check)
8. 🚀 Tag `v1.0.0`, announce, take customers

## The single most valuable lesson from this session

When verification gets sloppy, results drift from reality. The session-saving rule was **"paste the literal pytest tail, no summaries"** — once enforced, fabrication stopped. Carry this into every future chunk:

- A chunk isn't done until the artifact it produced actually runs.
- Dockerfile written ≠ Dockerfile working.
- Test written ≠ test passing.
- Endpoint coded ≠ endpoint returning 200.
- "Estimated" is a stop signal, not a verification.
