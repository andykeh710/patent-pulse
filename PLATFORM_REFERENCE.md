     1|# Invention Index 8 V1 — Complete Platform Functionality Reference
     2|
     3|> Generated 2026-05-17 for agent review of functionality, layout, UX/UI, and data structure.
     4|
     5|---
     6|
     7|## 1. Architecture Overview
     8|
     9|```
    10|┌──────────────────────────────────────────────────────────┐
    11|│                    Docker Compose Stack                    │
    12|│                                                           │
    13|│  frontend (Next.js 15 / React 19) :3000                   │
    14|│       │ rewrite /api/* → backend:8000                     │
    15|│       ▼                                                  │
    16|│  backend (FastAPI / Python 3.12) :8000 → host :8080       │
    17|│       │                                                   │
    18|│       ├── db (PostgreSQL 16 + pgvector) :5432             │
    19|│       ├── redis (7-alpine) :6379                          │
    20|│       ├── worker (Celery)                                 │
    21|│       └── beat (Celery schedule)                          │
    22|│                                                           │
    23|│  External: Anthropic Claude API, USPTO API, EPO API       │
    24|└──────────────────────────────────────────────────────────┘
    25|```
    26|
    27|### Tech Stack
    28|
    29|| Layer | Technology | Notes |
    30||-------|-----------|-------|
    31|| Frontend | Next.js 15.5, React 19, TypeScript, Tailwind CSS 3.4, SWR 2.2 | SSR + client-side data fetching |
    32|| Backend | FastAPI 0.115, SQLAlchemy 2.0 async, Pydantic 2.1 | Async throughout |
    33|| Database | PostgreSQL 16, pgvector 0.3, TSVECTOR | Full-text + vector search |
    34|| Queue | Celery 5.6, Redis 7 | 3 queues: ingestion, summarization, maintenance |
    35|| AI | Anthropic SDK 0.40, patent-client 5.0 | Claude Sonnet + Haiku |
    36|| Auth | Single-user mode (local-user) | No auth layer yet |
    37|
    38|---
    39|
    40|## 2. Database Schema
    41|
    42|### 2.1 Core Tables
    43|
    44|#### `patent_publications` (56,211 rows)
    45|The central table. Every patent from any source lands here.
    46|
    47|| Column | Type | Notes |
    48||--------|------|-------|
    49|| id | UUID PK | |
    50|| doc_id | VARCHAR(64) UNIQUE | e.g. "USPTO:12628214" |
    51|| family_id | VARCHAR(64) | EPO family grouping |
    52|| office | VARCHAR(8) | USPTO, EPO, WIPO |
    53|| publication_number | VARCHAR(32) | Display number |
    54|| application_number | VARCHAR(32) | |
    55|| kind_code | VARCHAR(4) | B1/B2=Grant, A1=Application |
    56|| filing_date, priority_date, publication_date, grant_date | DATE | |
    57|| assignees, inventors | JSONB[] | Array of strings |
    58|| cpc, ipc | JSONB[] | Classification codes |
    59|| title, abstract, claims_text, description_text | TEXT | |
    60|| legal_status | VARCHAR(32) | GRANTED, PUBLISHED |
    61|| estimated_expiry_date | DATE | Computed from filing+20yr |
    62|| legal_status_confidence | VARCHAR(16) | "estimated" (default) or "confirmed" |
    63|| summary | JSON | AI-generated summary (what_it_is, problem_solved, how_it_works, etc.) |
    64|| tags | JSONB | AI-generated tags (industries, risk_flags, opportunity_tags, etc.) |
    65|| interesting_score | FLOAT | Rules-based interest score (0-1) |
    66|| opportunity_score | FLOAT | Rules-based opportunity score (0-100) |
    67|| opportunity_breakdown | JSON | Component scores with weights |
    68|| why_now_text | TEXT | AI-generated "Why Now" narrative |
    69|| presentation_rank_score | FLOAT | For future LLM re-rank |
    70|| embedding | VECTOR(1536) | For semantic search |
    71|| search_vector | TSVECTOR | For full-text search |
    72|
    73|**Indexes**: doc_id, publication_number, publication_date, estimated_expiry_date, GIN on cpc/assignees/tags/search_vector, B-tree on opportunity_score
    74|
    75|#### `ai_artifacts` (4,457 rows)
    76|Every AI-generated output is stored as a durable artifact.
    77|
    78|| Column | Type | Notes |
    79||--------|------|-------|
    80|| id | UUID PK | |
    81|| patent_publication_id | UUID FK | Nullable for non-patent artifacts |
    82|| run_id | UUID FK | Links to ai_runs |
    83|| artifact_type | VARCHAR(32) | summary, tags, why_now, opportunity_narrative, etc. |
    84|| prompt_name, prompt_version, prompt_hash | | Content-addressed cache key |
    85|| input_hash | VARCHAR(64) | Deterministic hash of input payload |
    86|| content_json | JSONB | The actual AI output |
    87|| content_text | TEXT | Denormalized text |
    88|| model | VARCHAR(64) | e.g. claude-sonnet-4-20250514 |
    89|| input_tokens, output_tokens, actual_cost_usd | | Cost tracking |
    90|| status | VARCHAR(16) | pending, complete, failed |
    91|
    92|**Artifact types**: summary, tags, why_now, opportunity_narrative, opportunity_score, interesting_score, trend_narrative, assignee_narrative, score_rerank, trend_snapshot, assignee_intelligence
    93|
    94|#### `ai_runs`
    95|Records of batch AI operations initiated from Admin UI.
    96|
    97|| Column | Type |
    98||--------|------|
    99|| id | UUID PK |
   100|| task_type | VARCHAR(32) |
   101|| run_mode | VARCHAR(16) — dev_fixture, sample, cohort, full_batch |
   102|| cohort_filter | JSONB |
   103|| cohort_size, cached_count, uncached_count | INT |
   104|| est_cost_usd, actual_cost_usd | FLOAT |
   105|| status | VARCHAR(16) — pending, running, succeeded, failed, cancelled |
   106|
   107|### 2.2 Supporting Tables
   108|
   109|| Table | Rows | Purpose |
   110||-------|------|---------|
   111|| `themes` | — | Named theme groups with CPC/assignee/keyword filters |
   112|| `theme_matches` | — | Patent-to-theme match records |
   113|| `watchlist_items` | — | User-saved patents |
   114|| `users` | 1 | Single-user scaffold (local-user) |
   115|| `assignees` | — | Normalized assignee entities |
   116|| `trend_snapshots` | 2,414 | Weekly trend data by surface (cpc, tag, assignee) |
   117|| `convergence_signals` | 415 | CPC-pair joint filing growth rates |
   118|| `patent_cliff_clusters` | 407 | Groups of expiring patents by CPC/tag/assignee |
   119|| `cross_industry_snapshots` | — | kNN neighbor pairs across industries |
   120|| `sleeping_giant_clusters` | — | Old high-interest patents linked to trends |
   121|
   122|---
   123|
   124|## 3. API Endpoints (Complete Catalog)
   125|
   126|### 3.1 Health
   127|```
   128|GET /health → { status: "ok"|"degraded", database: "healthy"|"unhealthy" }
   129|```
   130|
   131|### 3.2 Patents (`/api/v1/patents`)
   132|
   133|| Method | Path | Description | Query Params |
   134||--------|------|-------------|-------------|
   135|| GET | `/` | List patents | office, kind_code, cpc_prefix, assignee, date_from/to, min_score, sort_by, sort_order, page, page_size |
   136|| GET | `/stats` | Dashboard stats | — |
   137|| GET | `/expiry-summary` | Expiry buckets | — |
   138|| GET | `/trend` | Filing trend | — |
   139|| GET | `/priority-watch` | Priority watch list | bucket (expiring_soon/recent/all) |
   140|| GET | `/{id}` | Patent detail | — |
   141|| GET | `/{id}/summary` | AI summary | — |
   142|| POST | `/{id}/why-now` | Generate Why Now | — (cache-first) |
   143|| POST | `/{id}/opportunity-narrative` | Generate Opp Narrative | — (cache-first) |
   144|| POST | `/{id}/trend-snapshot` | Generate Trend Snapshot | — (rules-based) |
   145|| POST | `/{id}/assignee-intelligence` | Generate Assignee Intel | — (rules-based) |
   146|
   147|**Response shapes**:
   148|- `PatentListItem`: id, doc_id, publication_number, title, assignees, cpc, dates, legal_status, scores, tags, summary_what_it_is, estimated_expiry_date, days_until_expiry
   149|- `PatentDetail`: All fields including abstract, claims_text, summary, score_breakdown, opportunity_breakdown, why_now_text, family_members, citations, embeddings
   150|- `StatsResponse`: total_patents, total_grants, total_applications, summarized_count, patents_this_week, top_cpc_sections, top_assignees
   151|
   152|### 3.3 Search (`/api/v1/search`)
   153|```
   154|GET / → PaginatedResponse<PatentListItem>
   155|  Params: q (required, min 3 chars), cpc, assignee, date_from/to, page, page_size
   156|```
   157|
   158|### 3.4 Semantic Search (`/api/v1/semantic`)
   159|```
   160|POST /query → { results: [{ patent, similarity, distance }], query, total }
   161|  Body: { query: string, limit?: int }
   162|GET /similar/{id} → list of similar patents by embedding distance
   163|```
   164|
   165|### 3.5 Expiry (`/api/v1/expiry`)
   166|```
   167|GET / → PaginatedResponse<ExpiryItem>
   168|  Params: days_ahead, office, industry, time_horizon, sort_by, sort_order, page, page_size
   169|```
   170|
   171|### 3.6 Opportunity (`/api/v1/opportunity`)
   172|```
   173|GET / → PaginatedResponse<OpportunityItem>
   174|  Params: tab (top/expired/revival/cross_industry/startup/enterprise/sustainability/legal_review),
   175|          industry, time_horizon, risk_flag, opportunity_tag, legal_confidence,
   176|          cpc_prefix, assignee_keyword, expiry_within_days, min_score, max_score,
   177|          sort, page, page_size
   178|GET /tab-counts → { top, expired, revival, cross_industry, startup, enterprise, sustainability, legal_review }
   179|```
   180|
   181|### 3.7 Trends (`/api/v1/trends`)
   182|```
   183|GET /summary → TrendsSummary
   184|GET /hot → TrendListResponse (z_score desc, limit=20)
   185|  Params: surface (cpc/tag/assignee), limit
   186|GET /growing → TrendListResponse (growth_pct desc, limit=20)
   187|GET /convergence → ConvergenceItem[] (limit=30)
   188|GET /cliffs → CliffListResponse
   189|  Params: window_months, min_patents, limit
   190|```
   191|
   192|### 3.8 Themes (`/api/v1/themes`)
   193|```
   194|GET / → Theme[]
   195|GET /{id} → Theme
   196|GET /{id}/patents → PaginatedResponse<PatentListItem>
   197|GET /{id}/stats → ThemeStats
   198|POST / → ThemeResponse (create)
   199|PATCH /{id} → ThemeResponse (update)
   200|DELETE /{id} → DeleteResponse
   201|```
   202|
   203|### 3.9 Watchlist (`/api/v1/watchlist`)
   204|```
   205|GET / → WatchlistItemResponse[]
   206|POST / → WatchlistItemResponse (body: { patent_id, note? })
   207|DELETE /{id} → { deleted: bool }
   208|GET /check/{patent_id} → { in_watchlist, watchlist_item_id }
   209|```
   210|
   211|### 3.10 Suppliers (`/api/v1/suppliers`)
   212|```
   213|GET /summary → SupplierSummary
   214|GET / → SupplierListResponse
   215|  Params: country, sort_by, min_patent_count, page, page_size
   216|GET /map → SupplierMapCountry[] (country-level aggregation)
   217|```
   218|
   219|### 3.11 Admin (`/api/v1/admin`)
   220|```
   221|POST /trigger-summarize?limit=N → { task_id, status }
   222|POST /trigger-expiry-backfill → { task_id, status }
   223|POST /seed-themes → { created, skipped }
   224|POST /trigger-match-themes → { task_id, status }
   225|```
   226|
   227|### 3.12 AI Runs (`/api/v1/ai-runs`)
   228|```
   229|POST /estimate → EstimateResponse
   230|  Body: { task_type, run_mode, cohort, tier? }
   231|POST / → RunSummary (create + optionally enqueue)
   232|GET / → RunListResponse (limit, task_type filter)
   233|GET /{id} → RunSummary
   234|GET /{id}/artifacts → ArtifactListResponse (limit, offset)
   235|GET /meta/options → RunMetadata (task_types, run_modes, thresholds)
   236|```
   237|
   238|### 3.13 Families (`/api/v1/families`)
   239|```
   240|GET / → list of patent families
   241|GET /{family_id} → family detail with members
   242|```
   243|
   244|---
   245|
   246|## 4. Frontend Pages (14 routes)
   247|
   248|### 4.1 Layout (`layout.tsx`)
   249|- Fixed sidebar navigation (w-64, not responsive)
   250|- Active link highlighting via `pathname.startsWith()`
   251|- No auth protection, no user context
   252|
   253|### 4.2 `/` → redirects to `/dashboard`
   254|
   255|### 4.3 `/dashboard` (Dashboard)
   256|**Data hooks**: usePatentStats, usePatents, useExpirySummary, usePatentTrend, usePriorityWatch
   257|**Components**:
   258|- Summary cards: Total Patents, Grants, Applications
   259|- AI Summaries progress bar (N / M summarized)
   260|- Patent Activity Trend (line chart)
   261|- Top CPC Sections (bar chart)
   262|- Top Assignees list
   263|- Priority Watch list (12 items, expiring_soon bucket)
   264|**States**: loading ✅, error ✅, empty handled
   265|
   266|### 4.4 `/patents` (Patent List)
   267|**Data hook**: usePatents with filter params
   268|**Components**:
   269|- Filter bar: CPC prefix, Assignee, Office dropdown, Score min/max, Clear button
   270|- Sort dropdown (publication_date/interesting_score/created_at)
   271|- Paginated list of PatentCards
   272|- Each card shows: title, assignee, CPC codes, interesting score, publication date
   273|**States**: loading ✅, error ✅, empty ✅
   274|
   275|### 4.5 `/patents/[id]` (Patent Detail)
   276|**Data hooks**: usePatent(id), usePatentSummary(id), useWatchlist.check
   277|**Components**:
   278|- Patent header: number, title, assignees, dates, legal status
   279|- Score section: interesting_score, opportunity_score, breakdown
   280|- TagsPanel: industries, technology_method, time_horizon, risk_flags, opportunity_tags
   281|- AISummaryPanel: what_it_is, problem_solved, how_it_works, commercial_significance
   282|- WhyNowPanel: Generate button → headline, summary, signals, confidence, limitations
   283|- OpportunityNarrativePanel: Generate button → opportunity_type, plain_english_opportunity, possible_products, target_customers, difficulty, timing, risks
   284|- TrendSnapshotPanel: Generate button → trend_score with components
   285|- AssigneeIntelligencePanel: Generate button → assignee_intelligence_score with components
   286|- Watchlist toggle button
   287|**States**: loading ✅, error ✅, patent not found, generation in-progress
   288|
   289|### 4.6 `/opportunity` (Opportunity Feed)
   290|**Data hooks**: useOpportunityList, useOpportunityTabCounts
   291|**Components**:
   292|- 8 tabs: Top, Expired, Revival, Cross-Industry, Startup, Enterprise, Sustainability, Legal Review
   293|- Each tab shows count badge
   294|- Filter bar: industry, time_horizon, risk_flag, opportunity_tag, legal_confidence, cpc_prefix, assignee
   295|- Sort dropdown: 6 sort options
   296|- Paginated list of opportunity cards showing score, tags, risk flags, legal confidence
   297|**States**: loading ✅, error ✅, empty ✅
   298|
   299|### 4.7 `/expiry` (Patent Expiry)
   300|**Data hooks**: useExpiry, useCliffs(12mo), useCliffs(24mo)
   301|**Components**:
   302|- Patent Cliff cards: groups of expiring patents by technology area
   303|- Expiry table: publication_number, title, assignee, expiry_date, days_left, opportunity_score
   304|- Filter bar: days_ahead, office, industry, time_horizon
   305|- Sort: expiry_urgency, expiry_date, opportunity_score
   306|**States**: loading ✅, error ✅
   307|
   308|### 4.8 `/trends` (Technology Trends)
   309|**Data hooks**: useTrendsSummary, useHotTrends, useGrowingTrends, useConvergence, useCliffs
   310|**Components**:
   311|- Summary cards: Trending Topics count, CPC Trends, Convergence Signals, Patent Cliffs
   312|- Surface filter buttons: Technology (CPC), Tags, Assignees
   313|- Hot Trends list (by z-score) — 20 items
   314|- Growing Trends list (by growth %) — 20 items
   315|- Convergence Signals: CPC_A + CPC_B pairs
   316|- Patent Cliffs by window
   317|- Each trend card: surface, key, counts (4w/12w/baseline), z_score, growth_pct, diversity
   318|**States**: loading ✅, error ✅
   319|
   320|### 4.9 `/themes` (Theme Management)
   321|**Data hooks**: useThemes, useThemePatents
   322|**Components**:
   323|- Theme list cards: name, description, cpc_prefixes, active/inactive badge
   324|- Click to expand → paginated patent list for that theme
   325|- Theme stats: total_matches, avg_score, top_assignees
   326|**States**: loading ✅, error ✅, empty ✅
   327|
   328|### 4.10 `/search` (Patent Search)
   329|**Data hooks**: usePatentSearch (fulltext), useSWR (semantic)
   330|**Components**:
   331|- Search input with mode toggle (Keyword / Semantic)
   332|- Fulltext results: paginated PatentCard list
   333|- Semantic results: PatentCard + similarity badge
   334|**States**: loading ✅, error ✅, empty ✅
   335|
   336|### 4.11 `/watchlist` (Saved Patents)
   337|**Data hook**: useWatchlist
   338|**Components**:
   339|- Paginated list of saved patents (12 per page)
   340|- Each item: patent card + note + remove button
   341|- Remove with optimistic UI update
   342|**States**: loading ✅, error ✅, empty ✅
   343|
   344|### 4.12 `/suppliers` (Supplier Intelligence)
   345|**Data hooks**: useSupplierSummary, useSuppliers, useSupplierMap
   346|**Components**:
   347|- Summary card: total suppliers, avg patents, countries
   348|- Filter bar: country, sort, min patent count
   349|- Supplier table: name, patent count, active count, score
   350|- Geography visualization (bubble chart, no actual map)
   351|**States**: loading ✅, error ✅
   352|
   353|### 4.13 `/admin/ai-runs` (Admin Console)
   354|**Data hooks**: useRunMetadata, useRunHistory, useRunArtifacts
   355|**Components**:
   356|- Task selector dropdown with all supported task types
   357|- Mode selector: Dev Fixture, Sample, Cohort, Full Batch
   358|- Cohort filters: patent_ids, cpc_prefix, grant years, expiry window, has_summary/tags/score
   359|- Estimate button → cost preview with cached/uncached counts
   360|- Create Run button → enqueues Celery tasks
   361|- Run history table: status, task_type, progress, cost
   362|- Run detail accordion: artifacts with JSON preview
   363|**States**: loading ✅, error ✅
   364|
   365|---
   366|
   367|## 5. AI Pipeline
   368|
   369|### 5.1 Task Types and Models
   370|
   371|| Task | Type | Model | Cost |
   372||------|------|-------|------|
   373|| summary | LLM | Sonnet | ~$0.003/patent |
   374|| tags | LLM | Haiku | ~$0.001/patent |
   375|| why_now | LLM | Sonnet (narrative tier) | ~$0.005/patent |
   376|| opportunity_narrative | LLM | Sonnet (narrative tier) | ~$0.005/patent |
   377|| opportunity_score | Rules | rules:v1 | $0 |
   378|| interesting_score | Rules | rules:v1 | $0 |
   379|| trend_snapshot | Rules | rules:v1 | $0 |
   380|| assignee_intelligence | Rules | rules:v1 | $0 |
   381|
   382|### 5.2 Cache Architecture
   383|- Every LLM call is content-addressed: `(prompt_hash, input_hash, artifact_type)`
   384|- Cache mode: `record` (API on miss, write to cache)
   385|- Repeated calls return cached artifact with zero API cost
   386|- Rules-based artifacts also cached for audit trail
   387|
   388|### 5.3 Prompts (5 templates)
   389|| File | Lines | Purpose |
   390||------|-------|---------|
   391|| `summarize_v1.md` | 45 | Patent summary (what_it_is, problem_solved, how_it_works, etc.) |
   392|| `tag_patent_v1.md` | 94 | Structured tags (industries, risk_flags, opportunity_tags, etc.) |
   393|| `why_now_v1.md` | 59 | Timing signals (expiry_window, technology_momentum, etc.) |
   394|| `opportunity_narrative_v1.md` | 61 | Commercial opportunity (products, customers, difficulty, timing) |
   395|| `claims_extraction_v1.md` | 10 | Extract independent claims from text |
   396|
   397|---
   398|
   399|## 6. Ingestion Pipeline
   400|
   401|### 6.1 Sources
   402|| Source | Client File | Schedule |
   403||--------|------------|----------|
   404|| USPTO Grants | `uspto_client.py` | Tuesdays 10am ET |
   405|| USPTO Applications | `uspto_client.py` | Thursdays 10am ET |
   406|| EPO Publications | `epo_client.py` | Wednesdays 12pm ET |
   407|| WIPO PCT | `wipo_client.py` | Thursdays 2pm ET |
   408|| EPO Family Resolution | `family_resolver.py` | Fridays 6am ET |
   409|| Google Patents Enrichment | `google_patents_client.py` | Saturdays 8pm ET |
   410|| BigQuery Historical | `bigquery_client.py` | Manual only |
   411|
   412|### 6.2 Ingestion Flow
   413|```
   414|USPTO API → fetch_grants_by_date() → normalize_grant() → score_dict() → upsert_patent() → summarize_patent()
   415|                                                                                         (only if abstract present)
   416|```
   417|
   418|### 6.3 Celery Beat Schedule (Sundays)
   419|| Time | Task |
   420||------|------|
   421|| 2am | Batch summarize pending |
   422|| 4am | Batch generate embeddings |
   423|| 5am | Re-summarize enriched patents |
   424|| 7am | Compute weekly trends |
   425|| 7:30am | Compute cliff clusters |
   426|| 8am | Compute convergence signals |
   427|
   428|---
   429|
   430|## 7. Current Data State
   431|
   432|| Metric | Count |
   433||--------|-------|
   434|| Total patents | 56,211 |
   435|| Grants | 41,004 |
   436|| Applications | 15,200 |
   437|| With abstracts | 7,273 |
   438|| AI summaries | 31,915 |
   439|| AI artifacts | 4,457 |
   440|| Unique assignees | 16,449 |
   441|| Expiring 2026-2029 | 2,456 |
   442|| Expiring 2030-2031 | 5,775 |
   443|| Trend snapshots | 2,414 |
   444|| Convergence signals | 415 |
   445|| Cliff clusters | 407 |
   446|| why_now artifacts | 8 (6 patents) |
   447|| opportunity_narrative artifacts | 6 (6 patents) |
   448|| opportunity_score artifacts | 47 |
   449|
   450|---
   451|
   452|## 8. Security & Error Handling (Current State)
   453|
   454|### 8.1 Backend
   455|- **Global exception handlers**: SQLAlchemyError → 500, ValueError → 422, Exception → 500 (all with structured logging)
   456|- **Input validation**: CPC prefix validated against `^[A-H]\d{2}[A-Z](/[0-9]+)?$` regex
   457|- **Industry filter**: validated against `^[a-zA-Z][a-zA-Z0-9_-]{0,63}$` regex
   458|- **Type safety**: All Pydantic models use proper types (UUID not str)
   459|
   460|### 8.2 Frontend
   461|- **Error states**: All 12 pages consume SWR `error` with retry buttons
   462|- **Error boundaries**: Global `error.tsx` + per-route boundaries
   463|- **Loading states**: Root `loading.tsx` with skeleton components
   464|- **Empty states**: Handled on all pages
   465|
   466|### 8.3 Known Gaps
   467|- No authentication (single-user mode)
   468|- No CSRF protection
   469|- No rate limiting
   470|- No HTTPS enforcement
   471|- No responsive/mobile design
   472|- No toast/notification system
   473|- `API_BASE = ""` in frontend (assumes Next.js proxy always works)
   474|- Patent detail: generate buttons not disabled during loading (possible double-clicks)
   475|
   476|---
   477|
   478|## 9. File Inventory
   479|
   480|### Backend (`backend/`) — 55 Python files
   481|```
   482|app/
   483|├── main.py                    # FastAPI app, CORS, exception handlers
   484|├── config.py                  # pydantic-settings from .env
   485|├── database.py                # async SQLAlchemy engine + session
   486|├── core/
   487|│   ├── models.py              # PatentPublication (56K rows, 40 columns)
   488|│   ├── ai_models.py           # AIRun, AIArtifact, TrendSnapshot, etc.
   489|│   ├── theme_models.py        # Theme, ThemeMatch, WatchlistItem
   490|│   ├── schemas.py             # PatentListItem, PatentDetail, StatsResponse, etc.
   491|│   ├── enums.py               # LegalStatus enum
   492|│   ├── exceptions.py          # InventionIndex8Error hierarchy
   493|│   ├── validators.py          # validate_cpc_prefix(), validate_industry()
   494|│   └── helpers.py             # model_from_row() utility
   495|├── api/
   496|│   ├── deps.py                # DbSession, AppSettings dependencies
   497|│   ├── health.py              # GET /health
   498|│   └── v1/
   499|│       ├── router.py          # Route aggregation
   500|│       ├── patents.py         # 13 endpoints (list, stats, detail, AI generation)
   501|