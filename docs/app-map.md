# Invention Index 8 — Application Map

**Date:** 2026-06-14
**Author:** Hermes Agent
**Purpose:** Complete system map before any revamp work begins

---

## 1. Architecture Overview

```
User Browser
    │
    ▼
┌──────────────────────────────────────────────┐
│  Caddy (reverse proxy — production only)      │
│  inventionindex8.com → frontend:3000          │
│              /api/* → backend:8000            │
└──────────────────────────────────────────────┘
    │
    ├──► Next.js Frontend (port 3000)
    │    React 19, Next.js 15.1, Tailwind 3.4, SWR 2.2
    │
    └──► FastAPI Backend (port 8000)
         Python 3.12, SQLAlchemy 2.0 async, Celery 5.4
              │
              ├──► PostgreSQL 16 + pgvector (port 5432)
              ├──► Redis 7 (port 6379, Celery broker)
              ├──► Anthropic Claude API (chat, summaries, analysis)
              ├──► OpenAI/DeepSeek API (embeddings)
              ├──► Stripe API (billing)
              ├──► Resend API (email)
              └──► External patent sources:
                   USPTO, EPO OPS, WIPO, Google Patents,
                   PatentsView, Google BigQuery
```

---

## 2. Frontend Map

### 2.1 Route Groups

#### (marketing) — Public pages, no auth required
| Route | File | Purpose |
|-------|------|---------|
| `/` | `(marketing)/page.tsx` | Landing page with hero, features, CTA |
| `/about` | `(marketing)/about/page.tsx` | About page |
| `/pricing` | `(marketing)/pricing/page.tsx` | Pricing tiers (4 tiers: Free, Basic, Lifetime, Enterprise) |
| `/contact` | `(marketing)/contact/page.tsx` | Contact form |
| `/privacy` | `(marketing)/privacy/page.tsx` | Privacy policy |
| `/terms` | `(marketing)/terms/page.tsx` | Terms of service |
| `/refund` | `(marketing)/refund/page.tsx` | Refund policy |

Marketing layout includes `MarketingNav.tsx` and `BriefingPreview.tsx`.

#### (auth) — Authentication pages
| Route | File | Purpose |
|-------|------|---------|
| `/login` | `(auth)/login/page.tsx` | Magic-link login form |
| `/login/verify` | `(auth)/login/verify/page.tsx` | Token verification callback |
| `/unsubscribed` | `(auth)/unsubscribed/page.tsx` | Email unsubscribe confirmation |

#### (app) — Authenticated main app (protected by middleware.ts)
| Route | File | Purpose |
|-------|------|---------|
| `/today` | `(app)/today/page.tsx` | Daily briefing hub |
| `/patents` | `(app)/patents/page.tsx` | Patent list/search |
| `/patents/[id]` | `(app)/patents/[id]/page.tsx` | Patent detail page |
| `/search` | `(app)/search/page.tsx` | Semantic + keyword search |
| `/companies` | `(app)/companies/page.tsx` | Company list with coverage bars |
| `/companies/[name]` | `(app)/companies/[name]/page.tsx` | Company detail/profile |
| `/expiry` | `(app)/expiry/page.tsx` | Expiry Radar |
| `/themes` | `(app)/themes/page.tsx` | Technology themes list |
| `/themes/[id]` | `(app)/themes/[id]/page.tsx` | Theme detail |
| `/trends` | `(app)/trends/page.tsx` | Filing trends |
| `/trends/[surface]/[key]` | `(app)/trends/[surface]/[key]/page.tsx` | Trend drilldown |
| `/opportunity` | `(app)/opportunity/page.tsx` | Opportunity discovery |
| `/watchlist` | `(app)/watchlist/page.tsx` | User's watched/followed items |
| `/onboarding` | `(app)/onboarding/page.tsx` | First-run wizard |
| `/chat` | `(app)/chat/page.tsx` | AI chatbot (Claude-powered, SSE streaming) |
| `/account` | `(app)/account/page.tsx` | Account settings |
| `/account/billing` | `(app)/account/billing/page.tsx` | Billing management |
| `/account/email-preferences` | `(app)/account/email-preferences/page.tsx` | Email settings |
| `/account/webhooks` | `(app)/account/webhooks/page.tsx` | Alert webhook configs |
| `/admin` | `(app)/admin/page.tsx` | Admin dashboard |
| `/admin/ai-runs` | `(app)/admin/ai-runs/page.tsx` | AI run monitoring |
| `/admin/data-health` | `(app)/admin/data-health/page.tsx` | DB data health |
| `/dev/components` | `(app)/dev/components/page.tsx` | Dev component showcase |

App layout: `(app)/layout.tsx` — wraps with `NavSidebar.tsx` + `TopNav.tsx` + `ErrorBoundary.tsx`.
App loading state: `(app)/loading.tsx` — provides skeleton fallback for Suspense boundaries.
App error state: `(app)/error.tsx` — catches render errors.

#### Public SEO pages (no auth)
| Route | File | Purpose |
|-------|------|---------|
| `/c/[name]` | `c/[name]/page.tsx` | Public company profile (SEO) |
| `/t/[slug]` | `t/[slug]/page.tsx` | Public theme page (SEO) |
| `/blog` | `blog/page.tsx` | Blog index |
| `/blog/[slug]` | `blog/[slug]/page.tsx` | Blog post |

### 2.2 Component Hierarchy

```
Root layout (layout.tsx)
├── MarketingNav            — Public top navigation
├── (app) layout
│   ├── TopNav              — App top bar (search, account dropdown, brand)
│   ├── NavSidebar          — Left-side persistent navigation
│   │   ├── BrandMark       — Logo/brand mark
│   │   └── AccountDropdown — User menu (settings, logout)
│   ├── UsageWarningBanner  — 80% usage threshold banner
│   └── ErrorBoundary       — React error boundary
├── UI primitives (/components/ui/)
│   ├── Badge, Pill         — Tag/chip components
│   ├── Button              — Styled button
│   ├── Card                — Universal card wrapper
│   ├── Counter             — Animated number
│   ├── EmptyState          — Empty state component
│   ├── FreshnessBanner     — Data freshness indicator
│   ├── LiveIndicator       — Real-time/recent indicator
│   ├── Reveal              — Staggered reveal animation
│   ├── SectionHeader       — Page section header
│   ├── Skeleton            — Loading skeleton
│   ├── Spinner             — Loading spinner
│   ├── StarterTopics       — Topic selection chips
│   └── StatTile            — Stat display tile
├── Patent components (/components/patents/)
│   ├── AISourceFooter      — AI content attribution
│   ├── AISummaryPanel      — AI-generated summary
│   ├── AssigneeIntelligencePanel — Assignee analysis
│   ├── ClaimsPanel         — Patent claims display
│   ├── ExternalPatentLinks — Links to external patent offices
│   ├── LegalConfidenceBadge— Legal status confidence level
│   ├── LinkedInPostPanel   — LinkedIn content generation
│   ├── OpportunityBreakdown— Opportunity scoring breakdown
│   ├── OpportunityNarrativePanel — Opportunity narrative
│   ├── OpportunityScoreBadge — Opportunity score badge
│   ├── PatentCard          — Patent list card
│   ├── PatentDetailTabs    — Tab navigation on patent detail
│   ├── PatentFiguresPanel  — Patent figures/images
│   ├── RiskFlagsBadge      — Risk indicator badges
│   ├── ScoreBadge          — Interest score badge
│   ├── TagsPanel           — Technology tags
│   ├── TrendSnapshotPanel  — Trend snapshot
│   ├── UsageSignalsPanel   — Commercial usage signals
│   └── WhyNowPanel         — Why-now narrative
├── Expiry components (/components/expiry/)
│   ├── ExpiryRadarCard     — Individual expiry card
│   ├── ExpiryRadarSection  — Expiry timeline section
│   └── ExpirySummaryCards  — Summary bar
├── Onboarding (/components/onboarding/)
│   ├── StepRole            — Persona selection
│   ├── StepIndustry        — Industry focus
│   ├── StepInterests       — Technology interests
│   └── StepConfirm         — Confirmation
└── Tour (/components/tour/)
    └── Tour                — Product tour overlay
```

### 2.3 Data Fetching Pattern

- **SWR** (`swr@2.2.5`) for all client-side data fetching
- Custom hooks in `/hooks/`: `usePatents`, `useExpiry`, `useTrends`, `useThemes`, `useWatchlist`, `useOpportunity`, `useSuppliers`, `useFreshness`, `useAIRuns`, `useAsyncAction`
- API client: `lib/api.ts` — typed fetch wrappers for every backend endpoint
- Auth context: `lib/AuthContext.tsx` — session management
- No React Server Components for data — all data is fetched client-side via SWR

### 2.4 Styling

- **Tailwind CSS 3.4** — utility-first
- **Dark-by-default** theme with Palantir-inspired aesthetic
- Custom CSS tokens in `styles/tokens.css`
- `geist` font for typography
- `motion` (Framer Motion fork) for animations
- Theme toggle available in user settings
- **No `next/image`** usage detected — `<img>` used in `PatentFiguresPanel` (lint warning)

### 2.5 State Management

- SWR for server state (automatic caching, revalidation, deduplication)
- `AuthContext` for auth state (React context)
- `ThemeProvider` for theme state
- URL search params for filter state on list pages
- No Redux, Zustand, or other global state library

### 2.6 Middleware

- `middleware.ts` — Edge middleware at root level
- Handles auth redirects: unauthenticated users → `/login`
- Currently has a `middleware.ts.disabled` variant (edge eval bug workaround)

---

## 3. Backend Map

### 3.1 API Endpoints (v1 — `/api/v1`)

| Prefix | Module | Purpose | Auth |
|--------|--------|---------|------|
| `/api/v1/auth` | `auth.py` | Magic-link auth: request, verify, logout | Public |
| `/api/v1/patents` | `patents.py` | Patent CRUD, list, detail | Mixed |
| `/api/v1/search` | `search.py` | Keyword search | Mixed |
| `/api/v1/semantic` | `semantic_search.py` | Vector similarity + hybrid search | Mixed |
| `/api/v1/suppliers` | `suppliers.py` | Company list, summary, map | Mixed |
| `/api/v1/expiry` | `expiry.py` | Expiry radar data | Mixed |
| `/api/v1/families` | `families.py` | Patent family data | Mixed |
| `/api/v1/themes` | `themes.py` | Technology themes | Mixed |
| `/api/v1/today` | `today.py` | Daily briefing (persona-weighted) | Auth |
| `/api/v1/watchlist` | `watchlist.py` | User's follows/saves | Auth |
| `/api/v1/opportunity` | `opportunity.py` | Opportunity discovery | Mixed |
| `/api/v1/trends` | `trends.py` | Filing trend data | Mixed |
| `/api/v1/content` | `content.py` | Content generation (LinkedIn posts) | Admin |
| `/api/v1/usage-signals` | `usage_signals.py` | Commercial usage signals | Mixed |
| `/api/v1/subscriptions` | `subscriptions.py` | Email subscription management | Mixed |
| `/api/v1/billing` | `billing.py` | Stripe billing (checkout, portal, webhook) | Auth |
| `/api/v1/exports` | `exports.py` | CSV/PDF export | Auth |
| `/api/v1/account` | `account.py` | User account, usage, delete, persona | Auth |
| `/api/v1/account` | `api_keys.py` | API key CRUD | Auth |
| `/api/v1/onboarding` | `onboarding.py` | Onboarding wizard data | Auth |
| `/api/v1/chat` | `chat.py` | SSE streaming chatbot | Auth |
| `/api/v1/admin` | `admin.py` | Admin endpoints (triggers, health, analytics) | Admin |
| `/api/v1/ai-runs` | `ai_runs.py` | AI artifact monitoring | Admin |
| `/api/v1/webhooks/resend` | `webhooks.py` | Resend email webhooks (open/click/bounce) | Public (HMAC) |
| — | `share.py` | Share card PNGs, sitemap, robots.txt | Public |
| — | `blog.py` | Blog CRUD (admin) + public read | Mixed |
| `/api/v1/reports` | `reports.py` | PDF patent reports | Auth |

### 3.2 Database Models

| Model | Table | Purpose |
|-------|-------|---------|
| `PatentPublication` | `patent_publications` | Core patent record (64K+ rows) |
| `AIArtifact` | `ai_artifacts` | Cached LLM output (summaries, tags, narratives) |
| `UserModel` | `users` | User accounts (magic-link auth) |
| `Theme` | `themes` | Technology themes (CPC categories) |
| `UserTopic` | `user_topics` | User's followed themes |
| `SavedPatent` | `saved_patents` | User's bookmarked patents |
| `Watchlist` | `watchlists` | User's followed entities |
| `Subscription` | `subscriptions` | Email subscription prefs |
| `BillingSubscription` | `billing_subscriptions` | Stripe subscription records |
| `UsageRecord` | `usage_records` | Feature usage tracking |
| `AlertConfig` | `alert_configs` | Webhook alert configs |
| `AlertHistory` | `alert_histories` | Alert delivery log |
| `BlogPost` | `blog_posts` | Blog content |
| `SupplierNormalized` | `supplier_normalized` | Normalized company/assignee names |
| `CitationRecord` | `citation_records` | Patent citations |
| `EmailDelivery` | `email_deliveries` | Email delivery tracking |
| `ApiKey` | `api_keys` | User API keys |

### 3.3 Key Services Layer

| Service | Purpose |
|---------|---------|
| `services/briefing.py` | Daily briefing assembly (persona-weighted) |
| `services/chat_memory.py` | Redis-backed conversation memory (30-min TTL) |
| `services/chat_retrieval.py` | RAG retrieval for chatbot |
| `services/chat_tools.py` | Tool calls (search_patents, open_patent, compare_companies) |
| `services/chat_citations.py` | Citation extraction and soft enforcement |
| `services/persona_weights.py` | Persona-based weighting for briefings |
| `services/recommendations.py` | For-you recommendations via pgvector |
| `services/follow_company.py` | Company follow/unfollow logic |
| `services/company_suggestions.py` | Company name autocomplete |
| `services/industry_cpc_map.py` | Industry → CPC code mapping |

### 3.4 AI Modules

| Module | Purpose |
|--------|---------|
| `ai/summarizer.py` | Patent claims/mechanism summarization |
| `ai/scorer.py` | Interest score (CPC relevance, assignee, claims) |
| `ai/tagger.py` | Patent technology tagging |
| `ai/why_now.py` | Why-now narrative generation |
| `ai/opportunity_scorer.py` | Opportunity scoring (expiry, market signals) |
| `ai/opportunity_narrative.py` | Opportunity narrative generation |
| `ai/assignee_intelligence.py` | Assignee strategy/portfolio analysis |
| `ai/trend_snapshot.py` | Trend snapshot generation |
| `ai/trend_narrative.py` | Trend narrative generation |
| `ai/usage_narrative.py` | Usage signal narrative |
| `ai/weekly_digest.py` | Weekly digest content generation |
| `ai/content_generator.py` | LinkedIn/social content generation |
| `ai/embedder.py` | Text embedding generation (DeepSeek/OpenAI) |
| `ai/llm_client.py` | LLM client abstraction (request/retry/cache) |
| `ai/anthropic_client.py` | Anthropic-specific client |

### 3.5 Celery Task Workers

| Queue | Tasks |
|-------|-------|
| `ingestion` | `ingest_grants`, `ingest_applications`, `ingest_epo`, `ingest_wipo`, `ingest_wipo_bigquery`, `bigquery_backfill`, `patentsview_backfill`, `citation_fetch`, `backfill_citations`, `backfill_forward_citations`, `backfill_figures` |
| `summarization` | `summarize`, `tag`, `why_now`, `opportunity_narrative`, `trend_snapshot`, `assignee_intelligence`, `embeddings`, `enrich_abstracts` |
| `maintenance` | `expiry_assessments`, `expiry_watch`, `compute_trends`, `compute_cliffs`, `compute_convergence`, `run_aggregates`, `backup`, `alerts`, `send_weekly_digest`, `send_instant_alert`, `news_ingestion`, `backfill_usage_signals`, `theme_matcher` |

Celery beat drives scheduled tasks (ingest runs, alert scans, weekly digests).

### 3.6 Ingestion Sources

| Source | Module | Format |
|--------|--------|--------|
| USPTO | `uspto_client.py` | Bulk XML, weekly grants/applications |
| EPO OPS | `epo_client.py` / `epo_ops_provider.py` | REST API (authenticated) |
| WIPO | `wipo_client.py` / `wipo_provider.py` | REST API + BigQuery |
| Google Patents | `google_patents_client.py` / `google_patents_provider.py` | Web scraping (figure links) |
| PatentsView | `patentsview_client.py` | REST API (USPTO assignee data) |
| ScrapeGraph | `scrapegraph_provider.py` | Web scraping proxy |
| BigQuery | `bigquery_client.py` | Google Patents Public Datasets |

### 3.7 Middleware & Infrastructure

| Component | Purpose |
|-----------|---------|
| `middleware/rate_limit.py` | SlowAPI rate limiting (60 req/min global) |
| `middleware/request_id.py` | Request ID tracking for logging |
| `observability/sentry.py` | Sentry error monitoring |
| `logging_config.py` | Structlog structured logging |
| `quotas/limits.py` | Feature quota limits (Free 5/day chat, etc.) |
| `billing/stripe_client.py` | Stripe integration |
| `email/sender.py` | Resend email delivery |
| `email/weekly_briefing.py` | Weekly briefing generation + A/B subjects |
| `reports/pdf_generator.py` | PDF report generation (WeasyPrint) |
| `patent_sources/registry.py` | Provider registry for multi-source patent data |

---

## 4. Deployment Architecture

### Production (Hetzner VPS)

```
┌─────────────────────────────────────┐
│  Hetzner VPS (188.245.85.248)       │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  Caddy (reverse proxy)        │  │
│  │  TLS termination              │  │
│  └───────────────────────────────┘  │
│           │                         │
│    ┌──────┴──────┐                  │
│    ▼             ▼                  │
│  frontend     backend               │
│  :3000        :8000 (internal)      │
│    │             │                  │
│    │    ┌────────┼────────┐         │
│    │    ▼        ▼        ▼         │
│    │  worker    beat   redis:6379   │
│    │  celery    celery              │
│    │             │                  │
│    └─────────────┤                  │
│                  ▼                  │
│            postgres:5432            │
└─────────────────────────────────────┘
```

### CI/CD Pipeline (.github/workflows/ci.yml)

```
Push to main
  ├── backend-lint (ruff check)
  ├── backend-test (pytest, Postgres 16 + Redis 7)
  ├── frontend-build (npm run build)
  └── deploy
        ├── SSH to Hetzner
        ├── docker compose up -d --build
        ├── Health check (curl /health, 30 attempts × 3s)
        ├── Smoke test (./scripts/smoke-test.sh)
        ├── Auto-rollback on failure
        └── Success notification (email via Resend)
```

---

## 5. Screen → API → Database Dependency Map

| Screen | API Endpoints | DB Tables |
|--------|--------------|-----------|
| Landing | None (static) | None |
| Login | `POST /auth/request-link`, `GET /auth/verify` | `users` |
| Onboarding | `PUT /account/persona`, `GET /themes` | `users`, `themes` |
| Today | `GET /today/briefing`, `GET /today/for-you` | `patents`, `user_topics`, `themes` |
| Patents list | `GET /patents`, `GET /search` | `patents`, `ai_artifacts` |
| Patent detail | `GET /patents/{id}`, various AI panels | `patents`, `ai_artifacts`, `citations` |
| Search | `POST /semantic/query`, `GET /search` | `patents` |
| Companies | `GET /suppliers`, `GET /suppliers/summary` | `supplier_normalized`, `patents` |
| Company detail | `GET /suppliers/{name}`, `GET /companies/{name}` | `suppliers`, `patents` |
| Expiry Radar | `GET /expiry`, `GET /expiry/{id}` | `patents` |
| Themes | `GET /themes`, `GET /themes/{id}` | `themes` |
| Trends | `GET /trends`, `GET /trends/{surface}/{key}` | `patents` |
| Opportunity | `GET /opportunity` | `patents`, `ai_artifacts` |
| Watchlist | `GET /watchlist`, `POST /watchlist` | `watchlists`, `saved_patents` |
| Chat | `POST /chat/stream` (SSE) | `patents`, Redis |
| Account | `GET /account`, `GET /account/usage` | `users`, `billing`, `usage` |
| Billing | Stipe Checkout redirect, `POST /billing/webhook` | `billing_subscriptions` |
| Admin | `GET /admin/*`, various triggers | All |
| Blog | `GET /blog`, `GET /blog/{slug}` | `blog_posts` |

---

## 6. Current State Summary

### What's Working
- Full CI/CD pipeline with auto-deploy and rollback
- Frontend builds successfully (Next.js 15, compiled in ~6.5s)
- Backend API router loads all 25+ route modules
- 53 frontend tests (1 failure — timezone issue, 7 suites)
- Backend test suite exists (80+ test files across ai/api/auth/services/tasks/ingestion/expiry)
- Docker Compose works for full stack (5 services)
- Stripe billing wired (TEST mode)
- Magic-link auth end-to-end
- Chatbot with SSE streaming, tool calls, citations, quota
- Weekly briefing pipeline with A/B subjects
- Public SEO pages (companies, themes, blog)
- Sitemap + robots.txt + JSON-LD structured data

### What's Known-Broken / Flaky
- Companies page "0 of 0" coverage bars (country/entity metadata not populating)
- Expiry Radar — unknown state, needs dynamic verification
- Figure thumbnails: only ~5K/64K have images
- Blog posts 3, 4, 5 use placeholder patent IDs
- Backend local venv is Python 3.9 (project requires 3.12) — Docker-based dev only
- Caddy container orphaned outside docker-compose
- `middleware.ts` has a `.disabled` variant (edge eval bug)
- Sentry config is V7-style (needs V8 `instrumentation.ts` pattern)
- Redis `maxmemory-policy` not configured
