     1|# Invention Index 8 V1 — Readiness Audit Matrix
     2|
     3|## Legend
     4|- ✅ Complete — works end-to-end with real data
     5|- ⚠️ Partial — works but has gaps
     6|- ❌ Missing — not implemented
     7|- 🔍 Needs verification — quick check required
     8|- ➖ Not V1-critical — defer to V1.1
     9|
    10|---
    11|
    12|| # | Feature | Status | Relevant Files | API Endpoints | Current Data | Blocker / Gap | Next Action |
    13||---|---------|--------|---------------|---------------|-------------|---------------|-------------|
    14|| 1 | Dashboard | ⚠️ Partial | `dashboard/page.tsx`, `usePatents.ts` | `/stats`, `/priority-watch`, `/trend`, `/expiry-summary` | Stats real (56K), Priority Watch real | Stats-only dashboard. Missing: opportunity feed, why-now, trend cards, assignee moves, AI run status | Step 8: Upgrade to executive snapshot |
    15|| 2 | Patents list | ✅ Complete | `patents/page.tsx`, `PatentCard.tsx` | `GET /patents` with filters | 56K patents, all scored | — | — |
    16|| 3 | Patent detail | ⚠️ Partial | `patents/[id]/page.tsx`, 5 AI panels | `GET /patents/{id}`, POST why-now/opp-narrative/trend/assignee | Real patent data, AI panels working | Generate buttons not disabled during loading; double-click risk | Step 3: Fix button UX |
    17|| 4 | Opportunity feed | ⚠️ Partial | `opportunity/page.tsx`, `_filters.tsx` | `GET /opportunity`, `/tab-counts` | 47 scored patents (from dump). Tabs: top=23, expired=0, revival=1, cross_industry=0, startup=1, enterprise=16, sustainability=6, legal_review=42 | Only 0.08% of patents scored. Most tabs near-empty. Newly ingested 13K patents have no AI enrichment | Run opportunity_score batch on unsummarized patents with abstracts |
    18|| 5 | Expiry | ✅ Complete | `expiry/page.tsx` | `GET /expiry` with filters | 8,257 expiring 2026-2031, 2,456 expiring 2026-2029 | — | — |
    19|| 6 | Trends | ✅ Complete | `trends/page.tsx`, `useTrends.ts` | `/trends/summary`, `/hot`, `/growing`, `/convergence`, `/cliffs` | 2,414 trend rows (assignee=1,918, cpc=461, tag=35), 415 convergence, 407 cliffs | No trend narratives generated (trend_narrative in ARTIFACT_TYPES but not implemented) | Defer trend narratives to V1.1. Metrics alone provide value. |
    20|| 7 | Themes | ✅ Complete | `themes/page.tsx`, `useThemes.ts` | `GET/POST/PATCH/DELETE /themes` | Working | — | — |
    21|| 8 | Search | ✅ Complete | `search/page.tsx` | `GET /search`, `POST /semantic/query` | Working (fulltext + semantic) | — | — |
    22|| 9 | Watchlist | ✅ Complete | `watchlist/page.tsx`, `useWatchlist.ts` | `GET/POST/DELETE /watchlist`, `/check/{id}` | Working with pagination | — | — |
    23|| 10 | Suppliers | ⚠️ Partial | `suppliers/page.tsx`, `useSuppliers.ts`, `suppliers.py` | `GET /suppliers/summary`, `/`, `/map` | 17,420 aggregated assignees (0 with country/entity_type) | Named "Suppliers" but IS assignee intelligence. Navigation label misleading. Normalization table empty. | Step 4: Rename to Assignees or build proper assignee page |
    24|| 11 | Admin AI Runs | ✅ Complete | `admin/ai-runs/page.tsx`, `useAIRuns.ts` | `POST /estimate`, `POST /`, `GET /`, `/meta/options` | 9 task types registered, estimate works | — | — |
    25|| 12 | Why Now artifacts | ⚠️ Partial | `why_now.py`, `tasks/why_now.py`, `WhyNowPanel.tsx` | `POST /patents/{id}/why-now` | 8 artifacts across 6 patents. Cache verified. | Only 6 of 47 scored patents have why_now | Generate for remaining scored patents (max 41 more) |
    26|| 13 | Opp Narrative artifacts | ⚠️ Partial | `opportunity_narrative.py`, `tasks/opportunity_narrative.py`, `OpportunityNarrativePanel.tsx` | `POST /patents/{id}/opportunity-narrative` | 6 artifacts across 6 patents. Empty opportunity text (missing claims) | Empty output fields — prompt needs more patent context | Minor: update prompt to work with abstract-only patents |
    27|| 14 | Trend Snapshot | ❌ Missing | `trend_snapshot.py`, `tasks/trend_snapshot.py`, `TrendSnapshotPanel.tsx` | `POST /patents/{id}/trend-snapshot` | 1 artifact (from dump) | Trend snapshot task exists but never run. Registered in ARTIFACT_TYPES. Frontend panel exists but not wired. | Defer to V1.1 (not V1-critical given existing trend data) |
    28|| 15 | Assignee Intelligence | ⚠️ Partial | `assignee_intelligence.py`, `tasks/assignee_intelligence.py`, `AssigneeIntelligencePanel.tsx`, `suppliers.py` | `POST /patents/{id}/assignee-intelligence`, `/suppliers/*` | Per-patent panel has 1 artifact. Suppliers page has 17K aggregated but 0 normalized | Per-patent works. Aggregated assignee page is "Suppliers" — needs rename + normalization | Step 4: Rename Suppliers → Assignees |
    29|| 16 | Score Re-rank | ❌ Missing | `ai_models.py` (ARTIFACT_TYPES only) | None | 0 artifacts | Only registered as artifact type. No implementation: no task, no endpoint, no frontend. `presentation_rank_score` field exists on DB but unused. | Step 6: Defer to V1.1. Current scoring works for V1. |
    30|| 17 | Weekly Digest | ❌ Missing | `ai_models.py`, `llm_client.py` (references only) | None | 0 artifacts, no route | No frontend route, no API endpoint, no task. Only referenced in artifact types. | Step 7: Defer to V1.1 (dashboard can tell the weekly story) |
    31|| 18 | Navigation | ⚠️ Partial | `NavSidebar.tsx` | — | All routes present | Unordered. "Suppliers" should be "Assignees". No dashboard prominence. | Step 9: Reorder + rename |
    32|| 19 | Security/UX | ⚠️ Partial | `main.py` (handlers), `error.tsx`, `ErrorDisplay.tsx` | — | Error states on all pages. Exception handlers active. | No auth, no CSRF, no rate limiting, no HTTPS. Generate buttons not disabled. No toast system. No mobile. | Steps 3 + 10 |
    33|| 20 | Data quality | ⚠️ Partial | All ingestion + AI files | — | 56K patents, 33K summarized, 4.5K artifacts, 47 scored | 99.9% of patents have no AI enrichment beyond summary. Only 47 have tags+scores. New 13K patents have 0 AI enrichment. | Run opportunity_score + tags batch on summarized patents |
    34|
    35|---
    36|
    37|## Summary Counts
    38|
    39|| Status | Count | Items |
    40||--------|-------|-------|
    41|| ✅ Complete | 7 | Patents list, Expiry, Trends, Themes, Search, Watchlist, Admin AI Runs |
    42|| ⚠️ Partial | 10 | Dashboard, Patent Detail, Opportunity, Suppliers, Why Now, Opp Narrative, Assignee Intel, Navigation, Security/UX, Data Quality |
    43|| ❌ Missing | 3 | Trend Snapshot, Score Re-rank, Weekly Digest |
    44|