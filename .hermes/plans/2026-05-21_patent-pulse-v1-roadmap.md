# Patent Pulse V1 Roadmap

## Goal

Transform Patent Pulse from an internal/demo analyst tool into a polished, useful, sellable patent intelligence product. Defer auth/billing infrastructure for now. Focus on making the application genuinely valuable before gating it.

## Current State

**What exists and works:**
- 13 database tables (patent_publications, users, assignees, ai_runs, ai_artifacts, themes, theme_matches, watchlist_items, trend/cliff/convergence/sleeping_giant snapshots, cross_industry_snapshots)
- ~42k patents, ~3k AI artifacts, ~2.4k trend snapshots (from bundled dump)
- 11 frontend pages: dashboard, patents, patent detail, opportunity (8 tabs), expiry, trends, suppliers, themes, search (keyword+semantic), watchlist, admin AI runs
- Full AI pipeline: summarize, tag, score, opportunity score, why now, opportunity narrative, trend snapshot, assignee intelligence, embeddings
- Celery beat schedule: weekly ingestion (USPTO/EPO/WIPO), weekly summarization, weekly trend computation
- Docker Compose: Postgres+pgvector, Redis, FastAPI, Celery worker+beat, Next.js

**What is missing or weak:**
- No auth, billing, or multi-tenancy (expected, deferred)
- No user-created topics (themes are admin-only)
- No newsletter system
- No content studio / LinkedIn Radar
- No exports (CSV, Markdown, PDF, JSON)
- No alerts
- No claims display on patent detail (claims_text exists in DB)
- No external patent-office links on detail page
- No citation display (citations_backward exists in DB)
- No family viewer on frontend (family API exists but no frontend page/tab)
- No similar patents on detail page (semantic similar API exists)
- Suppliers page should be "Companies / Assignees"
- No URL-state syncing for filters (not shareable/bookmarkable)
- No freshness indicators on pages
- No V1 limitations / legal caveats page
- Generate buttons lack duplicate-click protection
- Search lacks date/assignee/CPC/status filters
- Patent list has only sort, no filters
- Dashboard is stats-heavy, not editorial

## Strategic Decision

You said: ignore commercials for now, focus on a super polished, meaningful application.

That means the priority order is:

1. **Harden and polish the existing product** (Phase 0)
2. **Add patent credibility features** that make the product trustworthy (claims, family, citations, external links, similar patents, company pages)
3. **Rebuild navigation and Today page** into an editorial product experience
4. **Add user-created topics** as the core retention mechanic
5. **Add Content Studio / LinkedIn Radar** as the personal value driver
6. **Add newsletter preview** (rendering, not email delivery yet)
7. **Add exports** (Markdown first, then CSV/JSON)
8. **Add search and filtering depth**

Auth, billing, quotas, email delivery, alerts, team features, and reports come after V1 polish is done.

---

## Phase 0 — Harden Current Product

**Goal:** Make every existing page reliable, honest, and polished.

### 0.1 Generate button duplicate-click protection
- Every generate button (Why Now, Opportunity Narrative, Trend Snapshot, Assignee Intelligence) must disable on click, show loading state, and prevent re-submission
- Files: `frontend/src/components/patents/WhyNowPanel.tsx`, `OpportunityNarrativePanel.tsx`, `TrendSnapshotPanel.tsx`, `AssigneeIntelligencePanel.tsx`
- Also: AI Runs page create/estimate buttons

### 0.2 Freshness indicators
- Add "Data last updated" timestamps to: dashboard, opportunity, expiry, trends, patent detail
- Backend: add endpoint or extend existing endpoints to return last_ingest_at, last_trend_compute_at, last_ai_run_at
- Frontend: subtle footer or badge on each major page showing freshness
- Files: new backend endpoint or extend `/patents/stats`, frontend page updates

### 0.3 External patent-office links on patent detail
- Add links to: USPTO, Google Patents, Espacenet
- USPTO: `https://patents.google.com/patent/US{publication_number}`
- Google Patents: `https://patents.google.com/patent/{doc_id}`
- Espacenet: `https://worldwide.espacenet.com/patent/search?q=pn%3D{publication_number}`
- Files: `frontend/src/app/patents/[id]/page.tsx`

### 0.4 Claims section on patent detail
- If `claims_text` exists, render it in a collapsible section below abstract
- Parse independent vs dependent claims (independent claims don't reference other claims)
- Show claim count
- Files: `frontend/src/app/patents/[id]/page.tsx`, new `ClaimsPanel.tsx` component

### 0.5 URL state for filters
- Opportunity page: sync all filters (tab, tag, risk, confidence, industry, cpc, min_score, sort) to URL params
- Expiry page: sync filters to URL
- Patents page: sync sort to URL
- Search page: sync query, mode to URL
- Trends page: sync active tab, surface filter to URL
- Use `useSearchParams` / `useRouter` in Next.js App Router
- Files: all filterable page components

### 0.6 Rename Suppliers to Companies / Assignees
- Rename nav item, page title, API references in frontend
- Backend endpoint can stay `/suppliers` for now (alias later)
- Files: `NavSidebar.tsx`, `suppliers/page.tsx`, hooks, types

### 0.7 Error and empty states
- Audit every page for: missing loading states, missing error boundaries, unhelpful empty states
- Add "No results" messages with guidance
- Add error retry buttons where fetch fails
- Files: all page components

### 0.8 V1 Limitations page
- Static page at `/about` or `/limitations`
- Content: Patent Pulse provides informational patent intelligence only. Expiry dates are estimates. Legal status is not confirmed. Not legal advice. Data may be incomplete. Sources: USPTO, EPO, WIPO.
- Add link in footer/nav
- Files: new page, layout update

### Verification
- `make test` passes
- Frontend builds without errors (`npm run build`)
- Manual click-through of all pages
- All generate buttons tested for double-click
- URL state tested for shareability

---

## Phase 1 — Patent Credibility Features

**Goal:** Make patent detail trustworthy for serious users.

### 1.1 Patent detail page tabs
- Restructure patent detail from single long page into tabbed layout:
  - Overview (current content)
  - Claims (new)
  - Family (new)
  - Citations (new)
  - Similar (new)
  - Opportunity (move existing panels)
  - Legal / Expiry (new, consolidate expiry/legal info)
- Files: `frontend/src/app/patents/[id]/page.tsx`, new tab components

### 1.2 Family viewer tab
- Frontend consumes existing `/api/v1/families/by-patent/{patent_id}` endpoint
- Show: family members, jurisdictions, active vs expired, family risk indicator
- Files: new `FamilyTab.tsx` component

### 1.3 Citations tab
- Display `citations_backward` from patent data
- Show citing patent count, link to cited patents
- Files: new `CitationsTab.tsx` component

### 1.4 Similar patents tab
- Use existing `/api/v1/semantic/similar/{patent_id}` endpoint
- Show: similar patents with similarity score, different-industry matches highlighted
- Files: new `SimilarTab.tsx` component

### 1.5 Legal / Expiry tab
- Consolidate: estimated_expiry_date, legal_status, legal_status_confidence, maintenance_status
- Add caveats: "This is an estimate. Verify with official registers."
- Show maintenance fee timeline if data exists
- Files: new `LegalExpiryTab.tsx` component

### 1.6 Company / Assignee pages
- New route: `/companies/[name]` (URL-encoded normalized name)
- Backend endpoint: extend or add `/api/v1/suppliers/{name}` or new `/api/v1/companies/{name}`
- Content: filing velocity chart, top CPCs, recent patents, expiring patents, patent count, entity type
- Clickable assignee names everywhere should link to company page
- Files: new page, new API endpoint, update PatentCard/detail to link assignees

### 1.7 Source confidence badges
- On patent detail: show data source (USPTO/EPO/WIPO), last enriched date, confidence level
- On AI panels: show "Generated on [date] using [model]" footer
- Files: patent detail page, AI panel components

### Verification
- Patent detail tabs render correctly for patents with/without claims, family, citations
- Family viewer shows real family data
- Similar patents returns real results
- Company pages render for top assignees
- All new tabs handle empty state gracefully

---

## Phase 2 — Navigation Rebuild and Today Page

**Goal:** Transform nav and landing page from stats dashboard to editorial product experience.

### 2.1 New navigation structure
- Reorganize sidebar:
  1. Today (new, replaces dashboard)
  2. Opportunities
  3. Trends
  4. Expiring Patents
  5. Topics (new, replaces themes)
  6. Companies (renamed from suppliers)
  7. Search
  8. Watchlist
  9. Content Studio (new, placeholder initially)
  10. ---separator---
  11. Admin (AI Runs) — will be hidden behind auth later
- Files: `NavSidebar.tsx`

### 2.2 Today page (editorial dashboard)
- Replace current stats dashboard with editorial layout:
  - **Your Patent Pulse**: saved topic updates, new matches (placeholder until topics built)
  - **Top Opportunities**: top 5 scored patents with Why Now snippets
  - **Emerging Trends**: top 5 hot trends with context
  - **Expiring Opportunities**: top 5 expiring with revival potential
  - **Companies Moving**: top 5 assignees by recent activity
  - **System Freshness**: last ingest, last computation, next scheduled
- Each section links deeper into the relevant page
- Files: new `/today/page.tsx` or refactored `/dashboard/page.tsx`

### 2.3 Responsive polish
- Ensure all pages work on tablet/mobile widths
- Collapsible sidebar on small screens
- Card layouts reflow properly
- Files: layout.tsx, NavSidebar.tsx, all page components

### Verification
- Navigation flows naturally through product story
- Today page renders with real data
- Mobile/tablet breakpoints tested

---

## Phase 3 — User-Created Topics

**Goal:** Let users create and manage their own topics (the core retention mechanic).

### 3.1 Topic data model
- Extend or replace themes system:
  - `topics` table: id, name, description, keywords (JSONB), cpc_prefixes (JSONB), assignees (JSONB), opportunity_tags (JSONB), min_opportunity_score, is_active, user_id (nullable for now), created_at, updated_at
  - `topic_matches` table: topic_id, patent_id, match_score, match_reasons, matched_at
- Migration: 0005_user_topics
- Files: new migration, new/updated models

### 3.2 Topic CRUD API
- Endpoints: create, list, get, update, delete topics
- Endpoint: get topic matches (paginated, filterable)
- Endpoint: get topic stats
- Files: new `api/v1/topics.py` or extend `themes.py`

### 3.3 Topic matching job
- Celery task: match patents to topics based on keywords, CPC prefixes, assignees, score thresholds
- Run weekly after ingestion, or on-demand when topic created/updated
- Files: new or updated `tasks/theme_matcher.py`

### 3.4 Topic frontend
- `/topics` list page: show user's topics with match counts, last match date
- `/topics/[id]` detail page: new matches, top opportunities, expiring patents, trend signals, companies
- Topic create/edit modal or page: keyword editor, CPC picker, assignee picker, score threshold slider
- Default topic packs: offer starter topics (AI/Agents, Robotics, Climate Tech, Batteries, Biotech, etc.)
- Files: refactor `themes/page.tsx` into `topics/page.tsx`, new detail page, new create/edit components

### Verification
- Can create a topic with keywords + CPC prefixes
- Topic matching runs and produces real matches
- Topic detail page shows matched patents
- Default packs can be one-click added
- Empty topics show honest "no matches yet" state

---

## Phase 4 — Content Studio / LinkedIn Radar

**Goal:** Make Patent Pulse personally valuable for content creation.

### 4.1 Content Studio route
- New page: `/content` or `/studio`
- Sections:
  - **LinkedIn Radar**: 10 post ideas this week from trends + opportunities + expiring patents
  - **Content Ideas**: generated hooks from patents, trends, company moves
  - **Drafts**: saved content drafts

### 4.2 Content generation
- Backend endpoints for generating:
  - LinkedIn post from a patent
  - LinkedIn post from a trend
  - Content hook ideas from a topic
- Use AI artifacts system for caching
- Prompt templates for: analytical, contrarian, curiosity hook, founder insight
- Files: new `ai/content_generator.py`, new API endpoints, new prompts

### 4.3 Draft management
- `content_drafts` table: id, user_id, source_type, source_id, content_type, content_text, status (draft/used), created_at, updated_at
- CRUD API for drafts
- Frontend: save, edit, mark as used, delete
- Files: new migration, new model, new API, new frontend components

### 4.4 Content safety guardrails
- All generated content includes patent source citations
- Never claims freedom to operate
- Labels speculative use cases as speculative
- Includes limitations footer on every generated piece

### 4.5 Markdown export for content
- "Copy as Markdown" button on any generated content
- "Export draft as Markdown" on saved drafts
- Files: frontend utility, content components

### Verification
- Can generate a LinkedIn post from a real patent
- Post includes source citation and caveats
- Can save draft, retrieve it, mark as used
- Markdown export produces clean output

---

## Phase 5 — Exports

**Goal:** Let users get data out of the product.

### 5.1 Markdown export on patent detail
- "Export as Markdown" button on patent detail page
- Includes: title, abstract, claims summary, opportunity narrative, dates, links
- Client-side generation, no backend needed
- Files: patent detail page, new export utility

### 5.2 CSV/JSON export on list pages
- Add export button to: opportunity, expiry, patents, search results, watchlist, topic matches
- Backend: add `?format=csv` or `?format=json` query param to list endpoints, or new `/export` endpoints
- Respect reasonable row limits (500 rows for V1)
- Files: list API endpoints, frontend export buttons

### 5.3 Markdown export for trend and company pages
- "Export as Markdown" on trend detail and company profile
- Files: trend/company page components

### Verification
- CSV downloads open correctly in Excel/Numbers
- JSON export is valid JSON
- Markdown export is clean and readable
- Large exports don't crash or timeout

---

## Phase 6 — Search and Filtering Depth

**Goal:** Make search and discovery powerful enough for serious use.

### 6.1 Patent list filters
- Add to `/patents` page: keyword, assignee, CPC prefix, date range, legal status, has summary, score range
- Sync all to URL state
- Files: `patents/page.tsx`, update `patentsApi.list` params

### 6.2 Search enhancements
- Add to search: date range, assignee filter, CPC filter, legal status filter
- Add autocomplete/suggestions for assignees and CPC codes
- Files: `search/page.tsx`, backend search endpoints

### 6.3 Saved searches (lightweight)
- Store searches in localStorage for now (no backend needed)
- "Recent searches" section on search page
- "Save this search" button that stores URL + label
- Files: search page, new localStorage utility

### Verification
- Filters narrow results correctly
- URL state works for all filter combinations
- Saved searches persist across page reloads

---

## Phase 7 — Newsletter Preview (No Email Delivery Yet)

**Goal:** Build the newsletter rendering system without email infrastructure.

### 7.1 Newsletter content generator
- Backend: assemble weekly digest from: top opportunities, expiring patents, trending topics, company moves, content ideas
- Scope to user's topics if they have any
- Store as `newsletter_issues` with sections
- Files: new model, new Celery task, new API endpoint

### 7.2 Newsletter preview page
- `/newsletter` page showing the latest generated digest
- Rendered as a readable article with sections
- "This is a preview of your weekly newsletter" header
- Files: new frontend page

### 7.3 Newsletter from topics
- Each topic can generate a topic-specific digest preview
- Shown on topic detail page as "Newsletter Preview" tab
- Files: topic detail page update

### Verification
- Newsletter preview renders with real patent data
- Sections are coherent and well-formatted
- Topic-scoped newsletters show relevant content only

---

## Files Likely Changed (Summary)

**Backend new files:**
- `alembic/versions/0005_user_topics.py`
- `alembic/versions/0006_content_drafts.py`
- `alembic/versions/0007_newsletter_issues.py`
- `app/api/v1/topics.py`
- `app/api/v1/companies.py`
- `app/api/v1/content.py`
- `app/api/v1/newsletter.py`
- `app/api/v1/exports.py`
- `app/ai/content_generator.py`
- `app/ai/prompts/content_linkedin.md`
- `app/tasks/newsletter.py`
- `app/core/topic_models.py` (or extend theme_models)
- `app/core/content_models.py`
- `app/core/newsletter_models.py`

**Backend modified files:**
- `app/api/v1/router.py` (new route registrations)
- `app/api/v1/patents.py` (freshness data, export params)
- `app/api/v1/suppliers.py` (company profile endpoint)
- `app/api/v1/search.py` (additional filters)
- `app/tasks/theme_matcher.py` (topic matching)
- `app/core/models.py` (if adding fields)

**Frontend new files:**
- `app/today/page.tsx` (or refactored dashboard)
- `app/topics/page.tsx`
- `app/topics/[id]/page.tsx`
- `app/topics/create/page.tsx`
- `app/companies/[name]/page.tsx`
- `app/content/page.tsx`
- `app/newsletter/page.tsx`
- `app/limitations/page.tsx`
- `components/patents/ClaimsPanel.tsx`
- `components/patents/FamilyTab.tsx`
- `components/patents/CitationsTab.tsx`
- `components/patents/SimilarTab.tsx`
- `components/patents/LegalExpiryTab.tsx`
- `components/patents/PatentDetailTabs.tsx`
- `components/content/LinkedInRadar.tsx`
- `components/content/ContentDraft.tsx`
- `components/export/ExportButton.tsx`
- `lib/export.ts`

**Frontend modified files:**
- `app/NavSidebar.tsx` (new nav structure)
- `app/patents/[id]/page.tsx` (tabs, claims, links)
- `app/opportunity/page.tsx` (URL state)
- `app/expiry/page.tsx` (URL state)
- `app/patents/page.tsx` (filters, URL state)
- `app/search/page.tsx` (filters, URL state)
- `app/trends/page.tsx` (URL state)
- `app/suppliers/page.tsx` -> rename
- `app/themes/page.tsx` -> refactor to topics
- `lib/api.ts` (new API functions)
- `lib/types.ts` (new types)
- All AI panel components (double-click protection)

---

## Risks and Open Questions

1. **Data quality**: Claims text may not be populated for all patents. Family data coverage is unknown. Need to audit data before building features that depend on it.

2. **Topic matching performance**: If topic matching runs against 42k patents with complex filters, it needs to be efficient. May need indexes on tags JSONB fields.

3. **Content generation cost**: LinkedIn Radar generating 10 ideas/week per user could get expensive. Must use caching aggressively and precompute weekly.

4. **Themes → Topics migration**: The existing themes system (admin-only, CPC-based) needs to either evolve into user topics or coexist. Cleanest path: keep themes as "system topics" and add user topics alongside.

5. **Family data completeness**: The family resolver depends on EPO INPADOC. Coverage for non-European patents may be spotty.

6. **Newsletter without email**: Building newsletter rendering without delivery is useful for preview but won't demonstrate retention value until email works. This is fine for V1 polish.

7. **Single-user mode**: All of this is built in single-user mode. User_id fields should exist from the start so multi-tenancy migration is painless later.

---

## Execution Order

Start Phase 0. Complete and verify it fully before moving to Phase 1. Each phase builds on the previous. Phases are not parallelizable — they should be done sequentially to keep the product coherent.

Estimated timeline if working steadily:
- Phase 0: 3-5 days
- Phase 1: 5-7 days
- Phase 2: 3-4 days
- Phase 3: 5-7 days
- Phase 4: 5-7 days
- Phase 5: 3-4 days
- Phase 6: 3-4 days
- Phase 7: 3-4 days

Total: ~30-42 working days for a polished V1 product.

After V1 polish: add auth, billing, quotas, email delivery, alerts, team features, reports (the commercial SaaS layer from your vision document).
