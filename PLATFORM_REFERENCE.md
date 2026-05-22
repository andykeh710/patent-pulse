# Patent Pulse V1 — Complete Platform Functionality Reference

> Generated 2026-05-17 for agent review of functionality, layout, UX/UI, and data structure.

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                    │
│                                                           │
│  frontend (Next.js 15 / React 19) :3000                   │
│       │ rewrite /api/* → backend:8000                     │
│       ▼                                                  │
│  backend (FastAPI / Python 3.12) :8000 → host :8080       │
│       │                                                   │
│       ├── db (PostgreSQL 16 + pgvector) :5432             │
│       ├── redis (7-alpine) :6379                          │
│       ├── worker (Celery)                                 │
│       └── beat (Celery schedule)                          │
│                                                           │
│  External: Anthropic Claude API, USPTO API, EPO API       │
└──────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 15.5, React 19, TypeScript, Tailwind CSS 3.4, SWR 2.2 | SSR + client-side data fetching |
| Backend | FastAPI 0.115, SQLAlchemy 2.0 async, Pydantic 2.1 | Async throughout |
| Database | PostgreSQL 16, pgvector 0.3, TSVECTOR | Full-text + vector search |
| Queue | Celery 5.6, Redis 7 | 3 queues: ingestion, summarization, maintenance |
| AI | Anthropic SDK 0.40, patent-client 5.0 | Claude Sonnet + Haiku |
| Auth | Single-user mode (local-user) | No auth layer yet |

---

## 2. Database Schema

### 2.1 Core Tables

#### `patent_publications` (56,211 rows)
The central table. Every patent from any source lands here.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| doc_id | VARCHAR(64) UNIQUE | e.g. "USPTO:12628214" |
| family_id | VARCHAR(64) | EPO family grouping |
| office | VARCHAR(8) | USPTO, EPO, WIPO |
| publication_number | VARCHAR(32) | Display number |
| application_number | VARCHAR(32) | |
| kind_code | VARCHAR(4) | B1/B2=Grant, A1=Application |
| filing_date, priority_date, publication_date, grant_date | DATE | |
| assignees, inventors | JSONB[] | Array of strings |
| cpc, ipc | JSONB[] | Classification codes |
| title, abstract, claims_text, description_text | TEXT | |
| legal_status | VARCHAR(32) | GRANTED, PUBLISHED |
| estimated_expiry_date | DATE | Computed from filing+20yr |
| legal_status_confidence | VARCHAR(16) | "estimated" (default) or "confirmed" |
| summary | JSON | AI-generated summary (what_it_is, problem_solved, how_it_works, etc.) |
| tags | JSONB | AI-generated tags (industries, risk_flags, opportunity_tags, etc.) |
| interesting_score | FLOAT | Rules-based interest score (0-1) |
| opportunity_score | FLOAT | Rules-based opportunity score (0-100) |
| opportunity_breakdown | JSON | Component scores with weights |
| why_now_text | TEXT | AI-generated "Why Now" narrative |
| presentation_rank_score | FLOAT | For future LLM re-rank |
| embedding | VECTOR(1536) | For semantic search |
| search_vector | TSVECTOR | For full-text search |

**Indexes**: doc_id, publication_number, publication_date, estimated_expiry_date, GIN on cpc/assignees/tags/search_vector, B-tree on opportunity_score

#### `ai_artifacts` (4,457 rows)
Every AI-generated output is stored as a durable artifact.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| patent_publication_id | UUID FK | Nullable for non-patent artifacts |
| run_id | UUID FK | Links to ai_runs |
| artifact_type | VARCHAR(32) | summary, tags, why_now, opportunity_narrative, etc. |
| prompt_name, prompt_version, prompt_hash | | Content-addressed cache key |
| input_hash | VARCHAR(64) | Deterministic hash of input payload |
| content_json | JSONB | The actual AI output |
| content_text | TEXT | Denormalized text |
| model | VARCHAR(64) | e.g. claude-sonnet-4-20250514 |
| input_tokens, output_tokens, actual_cost_usd | | Cost tracking |
| status | VARCHAR(16) | pending, complete, failed |

**Artifact types**: summary, tags, why_now, opportunity_narrative, opportunity_score, interesting_score, trend_narrative, assignee_narrative, score_rerank, trend_snapshot, assignee_intelligence

#### `ai_runs`
Records of batch AI operations initiated from Admin UI.

| Column | Type |
|--------|------|
| id | UUID PK |
| task_type | VARCHAR(32) |
| run_mode | VARCHAR(16) — dev_fixture, sample, cohort, full_batch |
| cohort_filter | JSONB |
| cohort_size, cached_count, uncached_count | INT |
| est_cost_usd, actual_cost_usd | FLOAT |
| status | VARCHAR(16) — pending, running, succeeded, failed, cancelled |

### 2.2 Supporting Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `themes` | — | Named theme groups with CPC/assignee/keyword filters |
| `theme_matches` | — | Patent-to-theme match records |
| `watchlist_items` | — | User-saved patents |
| `users` | 1 | Single-user scaffold (local-user) |
| `assignees` | — | Normalized assignee entities |
| `trend_snapshots` | 2,414 | Weekly trend data by surface (cpc, tag, assignee) |
| `convergence_signals` | 415 | CPC-pair joint filing growth rates |
| `patent_cliff_clusters` | 407 | Groups of expiring patents by CPC/tag/assignee |
| `cross_industry_snapshots` | — | kNN neighbor pairs across industries |
| `sleeping_giant_clusters` | — | Old high-interest patents linked to trends |

---

## 3. API Endpoints (Complete Catalog)

### 3.1 Health
```
GET /health → { status: "ok"|"degraded", database: "healthy"|"unhealthy" }
```

### 3.2 Patents (`/api/v1/patents`)

| Method | Path | Description | Query Params |
|--------|------|-------------|-------------|
| GET | `/` | List patents | office, kind_code, cpc_prefix, assignee, date_from/to, min_score, sort_by, sort_order, page, page_size |
| GET | `/stats` | Dashboard stats | — |
| GET | `/expiry-summary` | Expiry buckets | — |
| GET | `/trend` | Filing trend | — |
| GET | `/priority-watch` | Priority watch list | bucket (expiring_soon/recent/all) |
| GET | `/{id}` | Patent detail | — |
| GET | `/{id}/summary` | AI summary | — |
| POST | `/{id}/why-now` | Generate Why Now | — (cache-first) |
| POST | `/{id}/opportunity-narrative` | Generate Opp Narrative | — (cache-first) |
| POST | `/{id}/trend-snapshot` | Generate Trend Snapshot | — (rules-based) |
| POST | `/{id}/assignee-intelligence` | Generate Assignee Intel | — (rules-based) |

**Response shapes**:
- `PatentListItem`: id, doc_id, publication_number, title, assignees, cpc, dates, legal_status, scores, tags, summary_what_it_is, estimated_expiry_date, days_until_expiry
- `PatentDetail`: All fields including abstract, claims_text, summary, score_breakdown, opportunity_breakdown, why_now_text, family_members, citations, embeddings
- `StatsResponse`: total_patents, total_grants, total_applications, summarized_count, patents_this_week, top_cpc_sections, top_assignees

### 3.3 Search (`/api/v1/search`)
```
GET / → PaginatedResponse<PatentListItem>
  Params: q (required, min 3 chars), cpc, assignee, date_from/to, page, page_size
```

### 3.4 Semantic Search (`/api/v1/semantic`)
```
POST /query → { results: [{ patent, similarity, distance }], query, total }
  Body: { query: string, limit?: int }
GET /similar/{id} → list of similar patents by embedding distance
```

### 3.5 Expiry (`/api/v1/expiry`)
```
GET / → PaginatedResponse<ExpiryItem>
  Params: days_ahead, office, industry, time_horizon, sort_by, sort_order, page, page_size
```

### 3.6 Opportunity (`/api/v1/opportunity`)
```
GET / → PaginatedResponse<OpportunityItem>
  Params: tab (top/expired/revival/cross_industry/startup/enterprise/sustainability/legal_review),
          industry, time_horizon, risk_flag, opportunity_tag, legal_confidence,
          cpc_prefix, assignee_keyword, expiry_within_days, min_score, max_score,
          sort, page, page_size
GET /tab-counts → { top, expired, revival, cross_industry, startup, enterprise, sustainability, legal_review }
```

### 3.7 Trends (`/api/v1/trends`)
```
GET /summary → TrendsSummary
GET /hot → TrendListResponse (z_score desc, limit=20)
  Params: surface (cpc/tag/assignee), limit
GET /growing → TrendListResponse (growth_pct desc, limit=20)
GET /convergence → ConvergenceItem[] (limit=30)
GET /cliffs → CliffListResponse
  Params: window_months, min_patents, limit
```

### 3.8 Themes (`/api/v1/themes`)
```
GET / → Theme[]
GET /{id} → Theme
GET /{id}/patents → PaginatedResponse<PatentListItem>
GET /{id}/stats → ThemeStats
POST / → ThemeResponse (create)
PATCH /{id} → ThemeResponse (update)
DELETE /{id} → DeleteResponse
```

### 3.9 Watchlist (`/api/v1/watchlist`)
```
GET / → WatchlistItemResponse[]
POST / → WatchlistItemResponse (body: { patent_id, note? })
DELETE /{id} → { deleted: bool }
GET /check/{patent_id} → { in_watchlist, watchlist_item_id }
```

### 3.10 Suppliers (`/api/v1/suppliers`)
```
GET /summary → SupplierSummary
GET / → SupplierListResponse
  Params: country, sort_by, min_patent_count, page, page_size
GET /map → SupplierMapCountry[] (country-level aggregation)
```

### 3.11 Admin (`/api/v1/admin`)
```
POST /trigger-summarize?limit=N → { task_id, status }
POST /trigger-expiry-backfill → { task_id, status }
POST /seed-themes → { created, skipped }
POST /trigger-match-themes → { task_id, status }
```

### 3.12 AI Runs (`/api/v1/ai-runs`)
```
POST /estimate → EstimateResponse
  Body: { task_type, run_mode, cohort, tier? }
POST / → RunSummary (create + optionally enqueue)
GET / → RunListResponse (limit, task_type filter)
GET /{id} → RunSummary
GET /{id}/artifacts → ArtifactListResponse (limit, offset)
GET /meta/options → RunMetadata (task_types, run_modes, thresholds)
```

### 3.13 Families (`/api/v1/families`)
```
GET / → list of patent families
GET /{family_id} → family detail with members
```

---

## 4. Frontend Pages (14 routes)

### 4.1 Layout (`layout.tsx`)
- Fixed sidebar navigation (w-64, not responsive)
- Active link highlighting via `pathname.startsWith()`
- No auth protection, no user context

### 4.2 `/` → redirects to `/dashboard`

### 4.3 `/dashboard` (Dashboard)
**Data hooks**: usePatentStats, usePatents, useExpirySummary, usePatentTrend, usePriorityWatch
**Components**:
- Summary cards: Total Patents, Grants, Applications
- AI Summaries progress bar (N / M summarized)
- Patent Activity Trend (line chart)
- Top CPC Sections (bar chart)
- Top Assignees list
- Priority Watch list (12 items, expiring_soon bucket)
**States**: loading ✅, error ✅, empty handled

### 4.4 `/patents` (Patent List)
**Data hook**: usePatents with filter params
**Components**:
- Filter bar: CPC prefix, Assignee, Office dropdown, Score min/max, Clear button
- Sort dropdown (publication_date/interesting_score/created_at)
- Paginated list of PatentCards
- Each card shows: title, assignee, CPC codes, interesting score, publication date
**States**: loading ✅, error ✅, empty ✅

### 4.5 `/patents/[id]` (Patent Detail)
**Data hooks**: usePatent(id), usePatentSummary(id), useWatchlist.check
**Components**:
- Patent header: number, title, assignees, dates, legal status
- Score section: interesting_score, opportunity_score, breakdown
- TagsPanel: industries, technology_method, time_horizon, risk_flags, opportunity_tags
- AISummaryPanel: what_it_is, problem_solved, how_it_works, commercial_significance
- WhyNowPanel: Generate button → headline, summary, signals, confidence, limitations
- OpportunityNarrativePanel: Generate button → opportunity_type, plain_english_opportunity, possible_products, target_customers, difficulty, timing, risks
- TrendSnapshotPanel: Generate button → trend_score with components
- AssigneeIntelligencePanel: Generate button → assignee_intelligence_score with components
- Watchlist toggle button
**States**: loading ✅, error ✅, patent not found, generation in-progress

### 4.6 `/opportunity` (Opportunity Feed)
**Data hooks**: useOpportunityList, useOpportunityTabCounts
**Components**:
- 8 tabs: Top, Expired, Revival, Cross-Industry, Startup, Enterprise, Sustainability, Legal Review
- Each tab shows count badge
- Filter bar: industry, time_horizon, risk_flag, opportunity_tag, legal_confidence, cpc_prefix, assignee
- Sort dropdown: 6 sort options
- Paginated list of opportunity cards showing score, tags, risk flags, legal confidence
**States**: loading ✅, error ✅, empty ✅

### 4.7 `/expiry` (Patent Expiry)
**Data hooks**: useExpiry, useCliffs(12mo), useCliffs(24mo)
**Components**:
- Patent Cliff cards: groups of expiring patents by technology area
- Expiry table: publication_number, title, assignee, expiry_date, days_left, opportunity_score
- Filter bar: days_ahead, office, industry, time_horizon
- Sort: expiry_urgency, expiry_date, opportunity_score
**States**: loading ✅, error ✅

### 4.8 `/trends` (Technology Trends)
**Data hooks**: useTrendsSummary, useHotTrends, useGrowingTrends, useConvergence, useCliffs
**Components**:
- Summary cards: Trending Topics count, CPC Trends, Convergence Signals, Patent Cliffs
- Surface filter buttons: Technology (CPC), Tags, Assignees
- Hot Trends list (by z-score) — 20 items
- Growing Trends list (by growth %) — 20 items
- Convergence Signals: CPC_A + CPC_B pairs
- Patent Cliffs by window
- Each trend card: surface, key, counts (4w/12w/baseline), z_score, growth_pct, diversity
**States**: loading ✅, error ✅

### 4.9 `/themes` (Theme Management)
**Data hooks**: useThemes, useThemePatents
**Components**:
- Theme list cards: name, description, cpc_prefixes, active/inactive badge
- Click to expand → paginated patent list for that theme
- Theme stats: total_matches, avg_score, top_assignees
**States**: loading ✅, error ✅, empty ✅

### 4.10 `/search` (Patent Search)
**Data hooks**: usePatentSearch (fulltext), useSWR (semantic)
**Components**:
- Search input with mode toggle (Keyword / Semantic)
- Fulltext results: paginated PatentCard list
- Semantic results: PatentCard + similarity badge
**States**: loading ✅, error ✅, empty ✅

### 4.11 `/watchlist` (Saved Patents)
**Data hook**: useWatchlist
**Components**:
- Paginated list of saved patents (12 per page)
- Each item: patent card + note + remove button
- Remove with optimistic UI update
**States**: loading ✅, error ✅, empty ✅

### 4.12 `/suppliers` (Supplier Intelligence)
**Data hooks**: useSupplierSummary, useSuppliers, useSupplierMap
**Components**:
- Summary card: total suppliers, avg patents, countries
- Filter bar: country, sort, min patent count
- Supplier table: name, patent count, active count, score
- Geography visualization (bubble chart, no actual map)
**States**: loading ✅, error ✅

### 4.13 `/admin/ai-runs` (Admin Console)
**Data hooks**: useRunMetadata, useRunHistory, useRunArtifacts
**Components**:
- Task selector dropdown with all supported task types
- Mode selector: Dev Fixture, Sample, Cohort, Full Batch
- Cohort filters: patent_ids, cpc_prefix, grant years, expiry window, has_summary/tags/score
- Estimate button → cost preview with cached/uncached counts
- Create Run button → enqueues Celery tasks
- Run history table: status, task_type, progress, cost
- Run detail accordion: artifacts with JSON preview
**States**: loading ✅, error ✅

---

## 5. AI Pipeline

### 5.1 Task Types and Models

| Task | Type | Model | Cost |
|------|------|-------|------|
| summary | LLM | Sonnet | ~$0.003/patent |
| tags | LLM | Haiku | ~$0.001/patent |
| why_now | LLM | Sonnet (narrative tier) | ~$0.005/patent |
| opportunity_narrative | LLM | Sonnet (narrative tier) | ~$0.005/patent |
| opportunity_score | Rules | rules:v1 | $0 |
| interesting_score | Rules | rules:v1 | $0 |
| trend_snapshot | Rules | rules:v1 | $0 |
| assignee_intelligence | Rules | rules:v1 | $0 |

### 5.2 Cache Architecture
- Every LLM call is content-addressed: `(prompt_hash, input_hash, artifact_type)`
- Cache mode: `record` (API on miss, write to cache)
- Repeated calls return cached artifact with zero API cost
- Rules-based artifacts also cached for audit trail

### 5.3 Prompts (5 templates)
| File | Lines | Purpose |
|------|-------|---------|
| `summarize_v1.md` | 45 | Patent summary (what_it_is, problem_solved, how_it_works, etc.) |
| `tag_patent_v1.md` | 94 | Structured tags (industries, risk_flags, opportunity_tags, etc.) |
| `why_now_v1.md` | 59 | Timing signals (expiry_window, technology_momentum, etc.) |
| `opportunity_narrative_v1.md` | 61 | Commercial opportunity (products, customers, difficulty, timing) |
| `claims_extraction_v1.md` | 10 | Extract independent claims from text |

---

## 6. Ingestion Pipeline

### 6.1 Sources
| Source | Client File | Schedule |
|--------|------------|----------|
| USPTO Grants | `uspto_client.py` | Tuesdays 10am ET |
| USPTO Applications | `uspto_client.py` | Thursdays 10am ET |
| EPO Publications | `epo_client.py` | Wednesdays 12pm ET |
| WIPO PCT | `wipo_client.py` | Thursdays 2pm ET |
| EPO Family Resolution | `family_resolver.py` | Fridays 6am ET |
| Google Patents Enrichment | `google_patents_client.py` | Saturdays 8pm ET |
| BigQuery Historical | `bigquery_client.py` | Manual only |

### 6.2 Ingestion Flow
```
USPTO API → fetch_grants_by_date() → normalize_grant() → score_dict() → upsert_patent() → summarize_patent()
                                                                                         (only if abstract present)
```

### 6.3 Celery Beat Schedule (Sundays)
| Time | Task |
|------|------|
| 2am | Batch summarize pending |
| 4am | Batch generate embeddings |
| 5am | Re-summarize enriched patents |
| 7am | Compute weekly trends |
| 7:30am | Compute cliff clusters |
| 8am | Compute convergence signals |

---

## 7. Current Data State

| Metric | Count |
|--------|-------|
| Total patents | 56,211 |
| Grants | 41,004 |
| Applications | 15,200 |
| With abstracts | 7,273 |
| AI summaries | 31,915 |
| AI artifacts | 4,457 |
| Unique assignees | 16,449 |
| Expiring 2026-2029 | 2,456 |
| Expiring 2030-2031 | 5,775 |
| Trend snapshots | 2,414 |
| Convergence signals | 415 |
| Cliff clusters | 407 |
| why_now artifacts | 8 (6 patents) |
| opportunity_narrative artifacts | 6 (6 patents) |
| opportunity_score artifacts | 47 |

---

## 8. Security & Error Handling (Current State)

### 8.1 Backend
- **Global exception handlers**: SQLAlchemyError → 500, ValueError → 422, Exception → 500 (all with structured logging)
- **Input validation**: CPC prefix validated against `^[A-H]\d{2}[A-Z](/[0-9]+)?$` regex
- **Industry filter**: validated against `^[a-zA-Z][a-zA-Z0-9_-]{0,63}$` regex
- **Type safety**: All Pydantic models use proper types (UUID not str)

### 8.2 Frontend
- **Error states**: All 12 pages consume SWR `error` with retry buttons
- **Error boundaries**: Global `error.tsx` + per-route boundaries
- **Loading states**: Root `loading.tsx` with skeleton components
- **Empty states**: Handled on all pages

### 8.3 Known Gaps
- No authentication (single-user mode)
- No CSRF protection
- No rate limiting
- No HTTPS enforcement
- No responsive/mobile design
- No toast/notification system
- `API_BASE = ""` in frontend (assumes Next.js proxy always works)
- Patent detail: generate buttons not disabled during loading (possible double-clicks)

---

## 9. File Inventory

### Backend (`backend/`) — 55 Python files
```
app/
├── main.py                    # FastAPI app, CORS, exception handlers
├── config.py                  # pydantic-settings from .env
├── database.py                # async SQLAlchemy engine + session
├── core/
│   ├── models.py              # PatentPublication (56K rows, 40 columns)
│   ├── ai_models.py           # AIRun, AIArtifact, TrendSnapshot, etc.
│   ├── theme_models.py        # Theme, ThemeMatch, WatchlistItem
│   ├── schemas.py             # PatentListItem, PatentDetail, StatsResponse, etc.
│   ├── enums.py               # LegalStatus enum
│   ├── exceptions.py          # PatentPulseError hierarchy
│   ├── validators.py          # validate_cpc_prefix(), validate_industry()
│   └── helpers.py             # model_from_row() utility
├── api/
│   ├── deps.py                # DbSession, AppSettings dependencies
│   ├── health.py              # GET /health
│   └── v1/
│       ├── router.py          # Route aggregation
│       ├── patents.py         # 13 endpoints (list, stats, detail, AI generation)
│       ├── search.py          # Full-text search
│       ├── semantic_search.py # Vector similarity search
│       ├── expiry.py          # Expiring patents list
│       ├── opportunity.py     # 8-tab opportunity feed
│       ├── trends.py          # Hot/growing trends, convergence, cliffs
│       ├── themes.py          # CRUD themes + patent matching
│       ├── watchlist.py       # User watchlist CRUD
│       ├── suppliers.py       # Supplier aggregation
│       ├── admin.py           # Trigger tasks (summarize, backfill, seed)
│       ├── ai_runs.py         # Estimate + create AI runs
│       └── families.py        # Patent family groups
├── ai/
│   ├── llm_client.py          # Unified cache-first LLM client (652 lines)
│   ├── summarizer.py          # Summary generation + validation
│   ├── tagger.py              # Tag generation + validation
│   ├── scorer.py              # Interest score (rules-based)
│   ├── opportunity_scorer.py  # Opportunity score (rules, 0-100)
│   ├── why_now.py             # Why Now narrative (cached)
│   ├── opportunity_narrative.py # Opportunity narrative (cached)
│   ├── trend_snapshot.py      # Trend snapshot (rules)
│   ├── assignee_intelligence.py # Assignee intelligence (rules)
│   ├── embedder.py            # Embedding generation
│   └── prompts/               # 5 markdown prompt templates
├── ingestion/
│   ├── uspto_client.py        # USPTO API via patent-client
│   ├── epo_client.py          # EPO OPS API
│   ├── wipo_client.py         # WIPO PatentScope
│   ├── google_patents_client.py # Supplementary full text
│   ├── bigquery_client.py     # Historical backfill
│   ├── normalizer.py          # USPTO data normalization
│   ├── epo_normalizer.py      # EPO/WIPO normalization
│   ├── dedup.py               # Upsert logic
│   └── family_resolver.py     # Patent family grouping
└── tasks/
    ├── celery_app.py           # Celery config + beat schedule (16 tasks)
    ├── ingest_grants.py        # Weekly + range + expiry window ingestion
    ├── ingest_applications.py  # Weekly application ingestion
    ├── ingest_epo.py           # EPO weekly ingestion
    ├── ingest_wipo.py          # WIPO weekly ingestion
    ├── summarize.py            # Batch summarization
    ├── tag.py                  # Batch tagging
    ├── opportunity.py          # Batch opportunity scoring
    ├── why_now.py              # Batch Why Now
    ├── opportunity_narrative.py # Batch Opportunity Narrative
    ├── trend_snapshot.py       # Batch trend snapshots
    ├── assignee_intelligence.py # Batch assignee intelligence
    ├── embeddings.py           # Batch embeddings
    ├── enrich_abstracts.py     # Google Patents enrichment
    ├── theme_matcher.py        # Theme matching
    ├── expiry_watch.py         # Daily expiry flag updates
    ├── compute_trends.py       # Weekly trend computation
    ├── compute_cliffs.py       # Cliff cluster computation
    ├── compute_convergence.py  # Convergence signal computation
    └── run_aggregates.py       # AIRun aggregate updates

tests/ — 136 tests across 9 modules
alembic/ — 4 migrations (0001→0004)
```

### Frontend (`frontend/`) — 47 TypeScript files
```
src/
├── app/
│   ├── layout.tsx             # Root layout + NavSidebar
│   ├── page.tsx               # Redirect → /dashboard
│   ├── loading.tsx            # Global loading skeleton
│   ├── error.tsx              # Global error boundary
│   ├── globals.css            # Tailwind imports
│   ├── NavSidebar.tsx         # Fixed sidebar navigation
│   ├── dashboard/page.tsx     # Dashboard with 5 SWR hooks
│   ├── patents/
│   │   ├── page.tsx           # List with filters + pagination
│   │   └── [id]/page.tsx      # Detail with AI generation panels
│   ├── opportunity/
│   │   ├── page.tsx           # 8-tab feed with filters
│   │   └── _filters.tsx       # Filter controls
│   ├── expiry/page.tsx        # Expiry table + cliff cards
│   ├── trends/page.tsx        # Hot/growing trends + convergence
│   ├── themes/page.tsx        # Theme list + patents
│   ├── search/page.tsx        # Fulltext + semantic search
│   ├── watchlist/page.tsx     # Saved patents with pagination
│   ├── suppliers/page.tsx     # Supplier table + geo viz
│   └── admin/ai-runs/page.tsx # Admin console
├── components/
│   ├── ErrorBoundary.tsx      # Class-based error boundary
│   ├── ErrorDisplay.tsx       # Reusable error display with retry
│   ├── ui/                    # Button, Badge, Skeleton, Spinner
│   └── patents/               # 15 patent-specific components
│       ├── PatentCard.tsx     # List card
│       ├── ScoreBadge.tsx     # Score display
│       ├── AISummaryPanel.tsx
│       ├── WhyNowPanel.tsx
│       ├── OpportunityNarrativePanel.tsx
│       ├── TrendSnapshotPanel.tsx
│       ├── AssigneeIntelligencePanel.tsx
│       ├── TagsPanel.tsx
│       ├── RiskFlagsBadge.tsx
│       ├── LegalConfidenceBadge.tsx
│       └── OpportunityScoreBadge.tsx
├── hooks/                     # 8 SWR hooks
│   ├── usePatents.ts          # + usePatent, usePatentSummary
│   ├── useExpiry.ts           # + useCliffs
│   ├── useOpportunity.ts
│   ├── useTrends.ts
│   ├── useThemes.ts
│   ├── useWatchlist.ts
│   ├── useSuppliers.ts
│   └── useAIRuns.ts
└── lib/
    ├── api.ts                 # All API client functions (247 lines)
    ├── types.ts               # All TypeScript interfaces (562 lines)
    └── utils.ts               # formatDate, truncate, pluralize, etc.
```

---

## 10. Verification State

| Check | Result |
|-------|--------|
| Backend tests | 136/136 pass |
| ruff lint (entire codebase) | 0 errors |
| Frontend tsc | 0 errors |
| Frontend build | 14 pages, 0 ESLint warnings |
| Frontend Jest | 31/31 pass |
| Docker services | All healthy |
| API health | `{ status: "ok", database: "healthy" }` |
| Live data | 56,211 patents, 4,457 artifacts, stats endpoint returns real counts |
