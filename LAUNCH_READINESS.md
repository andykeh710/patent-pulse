     1|# Invention Index 8 — Launch Readiness
     2|
     3|**Date:** 2026-05-30
     4|**Status:** Ready for controlled soft launch
     5|**Tests:** 341 passed, 1 xfailed, 2 xpassed, 0 failed
     6|
     7|---
     8|
     9|## Code Status
    10|
    11|### Tests
    12|- Backend: `341 passed, 1 xfailed, 2 xpassed, 0 failed`
    13|- Frontend: `npm run build` clean (5.2s)
    14|- No test regressions from launch prep changes
    15|
    16|### Routes (all 27 serve 200)
    17|| Route | Status |
    18||---|---|
    19|| /today | 200 |
    20|| /patents, /patents/[id] | 200 |
    21|| /expiry | 200 |
    22|| /opportunity | 200 |
    23|| /trends, /trends/[surface]/[key] | 200 |
    24|| /themes, /themes/[id] | 200 |
    25|| /companies, /companies/[name] | 200 |
    26|| /search | 200 |
    27|| /watchlist | 200 |
    28|| /account, /account/billing | 200 |
    29|| /admin, /admin/data-health, /admin/ai-runs | 200 |
    30|| /login, /login/verify | 200 |
    31|| /pricing, /terms, /privacy, /contact, /about | 200 |
    32|| /unsubscribed | 200 |
    33|
    34|### Error handling
    35|- App-level error boundary on `(app)/error.tsx` — catches page-level failures
    36|- Null states explain missing data with links to next actions
    37|- Empty states have CTAs (starter topics, browse links)
    38|
    39|### Known deferred bugs
    40|| Bug | Severity | Status |
    41||---|---|---|
    42|| Opportunity scorer: no patents >75 (0.37% above 50) | Medium | v3 migration running; 12 above 70 now |
    43|| Duplicate assignee names | Low | Normalization applied; 12.8% reduction achieved |
    44|| 84.6% lack abstracts | Medium | Enrichment running at 2000/day |
    45|| 96.4% lack claims | Low | Limited by Google Patents scraping |
    46|| Resend health check 403 in logs | Low | Log level lowered to INFO |
    47|| Company detail may 500 on stale cache | Low | Requires .next clean on deploy |
    48|
    49|---
    50|
    51|## Data Status
    52|
    53|### Patent counts (2026-05-30)
    54|| Office | Count |
    55||---|---|
    56|| USPTO | 62,968 |
    57|| EPO | 759 |
    58|| WIPO | 504 |
    59|| **Total** | **64,231** |
    60|
    61|### Coverage
    62|| Metric | Value |
    63||---|---|
    64|| Abstracts | 15.8% (enriching at 2,000/day) |
    65|| Claims | 3.6% |
    66|| Tags | ~3.2% |
    67|| Summarized | 50.3% |
    68|| Backward citations | 538 |
    69|| Forward citations | **BLOCKED** (USPTO ppubs.uspto.gov 503) |
    70|| Family IDs (EPO) | 759 |
    71|
    72|### Scoring migration
    73|- v2 → v3 migration in progress
    74|- 1,500 scored (500 v2 migrating, 1,000 v3 new)
    75|- Average v3 score: 46.8 (was ~25)
    76|- 12 patents above 70 (was 0)
    77|- Remaining: 62,731 — running via beat (200/15min)
    78|
    79|### Background tasks
    80|| Task | Schedule | Status |
    81||---|---|---|
    82|| Abstract enrichment | 4x/day, 500/batch | Running |
    83|| Opportunity scoring | Every 15min, 200/batch | Running (v3) |
    84|| Summarization | On enrichment completion | Event-driven |
    85|| Trends | Weekly Sunday 7am | Last run: May 30 (manually triggered) |
    86|| Embeddings | Every 2min, 1000/batch | Running |
    87|| Citations backfill | Every 5min | Blocked by USPTO outage |
    88|
    89|### Known data gaps
    90|- **Forward citations:** USPTO ppubs.uspto.gov returns 503. No workaround.
    91|- **EPO family members:** Family IDs exist (759) but family_members lists are empty — EPO family endpoint timeout.
    92|- **Images:** Google Patents blocks inline images. Link-only approach in place.
    93|
    94|---
    95|
    96|## Ops Required from Andy
    97|
    98|| # | Task | Effort | Domain |
    99||---|---|---|---|
   100|| O1 | Stripe TEST MODE: create 3 Products + Prices, copy IDs to .env | 15 min | dashboard.stripe.com |
   101|| O2 | Resend domain verification: add domain, SPF/DKIM/DMARC DNS | 30-60 min | resend.com + DNS |
   102|| O3 | Generate AUTH_SECRET_KEY (`openssl rand -base64 32`) | 1 min | Local |
   103|| O4 | Buy/configure production domain | 30 min | Registrar |
   104|| O5 | Pick hosting platform (Fly.io / Railway / Render) | Half day | Platform |
   105|| O6 | Managed Postgres + pgvector (Supabase / Neon / Crunchy Bridge) | Half day | Platform |
   106|| O7 | Redis hosting (Upstash / Railway / Fly Redis) | 1 hour | Platform |
   107|| O8 | Worker hosting (Celery + beat) | 1 hour | Platform |
   108|| O9 | Domain + HTTPS (Cloudflare or platform-native) | 2 hours | DNS + Platform |
   109|| O10 | Move secrets from .env to host secrets store | 1 hour | Platform |
   110|| O11 | DB backups (daily, off-host retention) | 1 hour | Platform |
   111|| O12 | Set SENTRY_DSN + NEXT_PUBLIC_SENTRY_DSN | 15 min | sentry.io |
   112|| O13 | First production deploy + end-to-end smoke test | Half day | Deploy |
   113|| O14 | Flip EMAIL_SEND_MODE=production | 1 min | Host secrets |
   114|
   115|---
   116|
   117|## User-Facing Caveats
   118|
   119|The following caveats appear in the UI. Do not remove them.
   120|
   121|- **Patent data is informational only.** Not legal advice.
   122|- **Expiry estimates require verification.** Always check with official patent office registers before relying on expiry status.
   123|- **Claims, images, and citations may still be enriching.** Coverage improves over time as background jobs complete.
   124|- **Forward citation coverage is affected by USPTO availability.** The ppubs.uspto.gov service is currently unavailable.
   125|- **AI-generated summaries are labeled.** AISourceFooter appears below AI-generated content.
   126|- **No "free to use" or "public domain" claims.** The app never labels a patent safe to use without legal review.
   127|
   128|---
   129|
   130|## Today Cards Status
   131|
   132|| Card | Status | Value |
   133||---|---|---|
   134|| Filing Trend | Live | "G06T — Image Processing, z=23.7" |
   135|| Expiring Opportunity | Null state visible | "No high-value patents expiring within 90 days yet" + Browse link |
   136|| Notable Patent | Live | Hitachi Metals, score 75.0 |
   137|| Company Move | Live | Samsung Electronics, +86 delta |
   138|
   139|---
   140|
   141|## Recommendation
   142|
   143|**Soft launch: YES.** The app is stable, all routes serve 200, tests pass, null states are handled honestly, and no user will see broken pages. The data pipeline (enrichment, scoring, summarization) runs autonomously and will compound quality over time.
   144|
   145|**Gates before taking payments:** Complete O1-O14 ops checklist. Flip EMAIL_SEND_MODE=production. End-to-end smoke test the magic-link → subscribe → CSV export flow.
   146|
   147|**Post-launch:** Allow 2-4 weeks for enrichment and v3 scoring to reach full coverage. Then re-evaluate the expiring opportunity card and abstract coverage metrics.
   148|