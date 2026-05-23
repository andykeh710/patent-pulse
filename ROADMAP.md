# Patent Pulse — Development Roadmap

Revised 2026-05-22. Priority order: expiry intelligence → trend
intelligence → usage discovery → engagement → SaaS → content.

## Completed

### Phase 0 — Foundation
- Patent ingestion (USPTO grants, EPO)
- AI summarization pipeline
- Interesting/opportunity scoring
- Basic search and patent detail

### Phase 1 — Patent Credibility
- Legal status, expiry estimation, family data, citations
- Opportunity tabs, scoring breakdowns, tags

### Phase 2 — Navigation & Today Page
- Navigation rebuild, Today page with freshness and priority watch

### Phase 3 — User-Created Topics
- Topic CRUD, keyword matching, 6 default topic packs

### Phase 4.1 — Content Generation (MVP)
- LinkedIn post generation from patents (shipped as downstream feature)

---

## Upcoming

### Sprint 1 — Repo & Agent Alignment ✅ Done

Goal: Hermes and project docs reflect the new product direction.

- [x] Update Hermes memory with new priority order
- [x] Create `PRODUCT_STRATEGY.md`
- [x] Create `ROADMAP.md`
- [x] Create `AGENTS.md` with repo-level development rules
- [x] Add Product Pillars, Surface Map, and Pricing Tiers to strategy doc (2026-05-22 revision)
- [x] Verified Hermes prioritizes expiry/trend/usage over content generation

Acceptance: Hermes stops treating LinkedIn/content as default priority.
Future code work is judged against expiry/trend/usage value.

---

### Sprint 2 — Expiry Radar 2.0 🔄 In progress

Status (2026-05-22): Sprint 2A ✅, Sprint 2B ✅ (178 tests pass),
Sprint 2C in active development.

Goal: Turn `/expiry` from a table of estimated dates into a credible
product surface for expired and expiring opportunities.

User question: "Which patents are expiring or expired soon, which ones
matter, and what can I do with that information?"

Delivered in three slices — do not attempt all at once.

#### Sprint 2A — Assessment Foundation

Goal: Create the data layer and deterministic assessment logic.

- [ ] `expiry_assessments` migration: id, patent_publication_id,
  estimated_expiry_date, expiry_status, expiry_status_confidence,
  maintenance_status, maintenance_status_source, active_family_risk,
  active_family_risk_reason, terminal_disclaimer_flag,
  patent_term_adjustment_days, legal_caveats, assessment_json,
  computed_at, source_updated_at
- [ ] Indexes on: patent_publication_id, expiry_status,
  expiry_status_confidence, estimated_expiry_date, active_family_risk
- [ ] ORM model `ExpiryAssessment`
- [ ] Deterministic assessment engine in `backend/app/expiry/assessment.py`:
  `compute_expiry_assessment(patent, family_members, as_of_date)`
- [ ] Idempotent backfill task: `backend/app/tasks/expiry_assessments.py`
- [ ] Backend tests for all assessment rules
- [ ] No UI changes yet

Allowed expiry_status values: `active_estimated`, `expiring_soon`,
`expired_estimated`, `lapsed_possible`, `lapsed_confirmed`,
`expired_confirmed`, `unknown`.

Allowed confidence values: `low`, `medium`, `high`, `confirmed`.

Guardrails:
- No invented maintenance-fee data — use `unknown` when unavailable
- No "free to use" or "public domain" language
- Always distinguish estimated from confirmed
- Missing dates → `unknown` status

#### Sprint 2B — API + Scoring

Goal: Make expiry intelligence queryable.

- [ ] `expiry_opportunity_score` on `expiry_assessments` (separate from
  general opportunity_score)
- [ ] Upgraded `/api/v1/expiry` with filters: expiry_status, confidence,
  maintenance_status, active_family_risk, expiry_window, cpc, assignee,
  industry, min_expiry_opportunity_score
- [ ] `GET /api/v1/expiry/opportunities` — high-value candidates
- [ ] `GET /api/v1/expiry/clusters` — patent cliffs
- [ ] `GET /api/v1/expiry/summary` — dashboard cards
- [ ] Backend tests for all filters and sorts
- [ ] Old `/expiry` UI must not break

#### Sprint 2C — Expiry Radar UI

Goal: Turn `/expiry` into the core product surface.

- [ ] Rename page label to "Expiry Radar" (keep route `/expiry`)
- [ ] Sections: Expiring Soon, Recently Expired, Likely Lapsed,
  Revival Candidates, Patent Cliffs, High-Opportunity Expirations,
  Needs Legal Verification
- [ ] Every card shows: expiry date, status, confidence, active family
  risk, opportunity scores, trend linkage, usage signal count
- [ ] "Verify with official registers" caveat on every card
- [ ] Empty states explain legal uncertainty
- [ ] CSV export using current filters (URL-state backed if possible)
- [ ] No "free to use" or "public domain" language anywhere

Guardrails (apply across all slices):
- No patent labeled "free to use"
- Expiry status explicitly estimated vs confirmed
- Active family risk always visible
- Empty states explain why a patent is not safe to treat as expired

---

### Sprint 3 — Patent Detail Credibility

Goal: A patent-literate user can assess a patent without leaving.

- [ ] Claims tab: independent/dependent claims, plain-English summary,
  key mechanisms, broadness indicators
- [ ] Family tab: family members, jurisdictions, dates, active/expired
  members, relationship type, active family risk
- [ ] External links: USPTO, Google Patents, Espacenet, WIPO
- [ ] Similar patents panel (using existing semantic search)
- [ ] Citation indicators (forward/backward, if available)
- [ ] Assignee clickable → company profile page
- [ ] Inventor names displayed

---

### Sprint 4 — Trend Intelligence Drilldowns

Goal: Trends become explainable and actionable, not just counts.

- [ ] Trend cards clickable → drilldown page
- [ ] Show patents driving each trend
- [ ] Show assignees driving each trend
- [ ] Show change over time
- [ ] Link trends to expiring patents (same CPC/tag area)
- [ ] Trend narratives for top trends (AI-generated, artifact-cached)
- [ ] "Why this trend matters" summaries

---

### Sprint 4.5 — Patent Figure Ingestion (link-only)

Goal: Make patent figures visible across the product. Required before
Sprint 6 ships a visual News Feed.

Approach: **Link-only**. Store first-figure URLs pointing to official
patent office endpoints (USPTO PDF/TIFF, Google Patents thumbnail). No
local image hosting, no re-publication. Zero storage cost, no licensing
review needed.

- [ ] Add `figure_url` (string, nullable) and `figure_count` (int) to
  `patent_publications` via migration
- [ ] During ingestion, compute USPTO/Google Patents figure URL from
  `publication_number` (e.g.
  `https://patents.google.com/patent/{pub_number}/thumbnails`)
- [ ] Backfill task for existing ~50k patents
- [ ] Patent detail page: render first figure as a thumbnail when present
- [ ] Patent card: optional small figure thumbnail when available
- [ ] Empty state when figure URL is null (no broken image icons)
- [ ] Backend tests: figure_url populated on ingest, backfill task is
  idempotent

Guardrails:
- Never host or re-serve figure images — embed via remote `<img src>` only
- Display "Image © patent office — verify at source" attribution on hover

---

### Sprint 5 — Commercial Usage Signals MVP

Goal: For an expired/expiring patent, show whether newer patents or
market-adjacent technology suggest current relevance. Never overclaim.

#### Data Model

- [ ] `usage_evidence` table: source_type (forward_citation, newer_patent,
  company_product_page, press_release, technical_article, marketplace_listing,
  standard_document, open_source_repo), source_name, source_url, snippet,
  evidence_text, matched_terms, confidence, retrieved_at
- [ ] `patent_usage_signals` table: score, confidence, summary,
  market_categories, companies, products, evidence_count,
  strongest_evidence_ids, limitations

#### Implementation (MVP scope)

- [ ] Forward citations as evidence
- [ ] Semantically similar newer patents as evidence
- [ ] Usage signal score computation
- [ ] Patent detail panel: "Commercial Usage Signals" with evidence list,
  score, confidence, limitations, source links
- [ ] Expiry Radar filter: `has_usage_signals`, `usage_signal_score >= X`
- [ ] Usage signal narrative (AI artifact)

#### Language Rules

- Never: "this patent is used in Product X"
- Prefer: "appears related to," "shows technical overlap with,"
  "suggests market relevance," "may indicate commercial usage"
- Always show evidence tier and source links
- Always include limitations

---

### Sprint 6 — Topics, Patent News Feed, Highlights, Newsletters

Goal: Users discover new patent activity through a daily/weekly feed and
subscribe to topics for ongoing intelligence. Phase 3 already shipped
basic topic CRUD; this sprint adds the content engine on top.

#### 6A — Highlights data layer

`highlight_cards` table is the curation layer that feeds Today, News
Feed, and the Newsletter from one source.

- [ ] `highlight_cards` table: id, type, source_type, source_id,
  title, summary, score, reasons, computed_at, expires_at
- [ ] Highlight types: `top_opportunity`, `filing_spike`,
  `expiring_cluster`, `assignee_move`, `weird_patent`,
  `cross_industry_idea`, `revival_candidate`
- [ ] Daily generation job that rebuilds highlights from real data
  (no LLM invention)
- [ ] `GET /api/v1/highlights` with type filter
- [ ] Backend tests for each highlight type

#### 6B — Patent News Feed

A visual feed of new filings/grants worth knowing about. Patent-focused,
not generic news.

- [ ] `/news` page with card grid
- [ ] Each card: patent figure thumbnail (from Sprint 4.5), title,
  assignee, "why this matters" line (1-sentence AI summary), CPC tag,
  link to detail page
- [ ] Filter by topic (uses Phase 3 user topics)
- [ ] Default sort: newest filings with highest interesting_score
- [ ] Patent-of-the-day pick (one curated highlight per day)
- [ ] "Verify at patent office" link on every card

**Editorial guardrail:** the "why this matters" line is generated from
patent abstract + tags + opportunity_score — never invented. If no
abstract, no line shown.

#### 6C — Topics enhancement (alerts + matching)

Build on Phase 3 topic CRUD with active monitoring.

- [ ] Topic matching against newly ingested patents (currently manual)
- [ ] Alert types: patent expiring soon, newly expired, usage signal
  found, new filing spike, assignee starts filing, convergence signal,
  high-opportunity patent
- [ ] Topic detail page: latest matches, related trends, related expiry
- [ ] Saved searches

#### 6D — Newsletter delivery

- [ ] Weekly topic-scoped newsletter rendered from highlight cards
- [ ] Sections: top trends, new filings in your topics, expiring
  opportunities, usage signals, companies moving, patent of the week
- [ ] Email delivery (no auth required yet — uses anonymous user_id;
  full multi-tenancy lands in Sprint 7)
- [ ] Unsubscribe handling
- [ ] Plaintext + HTML versions

---

### Sprint 7 — SaaS Foundation

Goal: Product can safely charge users.

- [ ] Authentication: signup, login, password reset, email verification
- [ ] Multi-tenancy: user-owned topics, watchlists, alerts, newsletters
- [ ] Stripe billing: checkout, annual plan, subscription status
- [ ] Quotas: AI credits, saved topics, watchlist size, exports
- [ ] Account page: subscription, billing portal, usage, preferences
- [ ] Export: Markdown, CSV for lists, saved patent export

---

### Sprint 8 — Commercial API & Exports

Goal: Enable Pro / Team pricing tiers via programmatic access.

#### Commercial API

- [ ] API key issuance (user-scoped) per Pro+ account
- [ ] Rate-limited routes under `/api/commercial/v1/`:
  patents, search, trends, opportunities, expiry, topics, highlights
- [ ] Per-key usage tracking (calls, tokens, exports)
- [ ] Quota enforcement aligned with pricing tier
- [ ] Webhook delivery for alerts (new filings in topic, expiry events,
  usage signals, assignee moves)
- [ ] OpenAPI docs auto-published at `/api/commercial/v1/docs`

#### Exports

- [ ] CSV export for patents, opportunities, expiry, watchlist (Pro+)
- [ ] JSON export for the same surfaces (Pro+)
- [ ] Markdown export for patent detail + AI artifacts (Creator+)
- [ ] PDF report generation (Pro+, post-MVP)
- [ ] Background job queue for large exports with email-when-ready

#### Integrations

- [ ] Slack alert integration via webhooks (post-MVP)
- [ ] Zapier/Make connectors (post-MVP, requires public API stability)

---

### Later — Content Studio (Downstream)

LinkedIn 4.1 already shipped. Future additions:

- [ ] Multi-patent roundups (one post summarizing 3-5 related patents)
- [ ] X/Twitter thread generator
- [ ] Newsletter paragraph generator (fits into Sprint 6 newsletter)
- [ ] Founder idea memo generator
- [ ] Investor angle memo generator
- [ ] Custom report generation (PDF, branded)
- [ ] Content scheduling

All Content Studio outputs **must consume** Patent Intelligence (Pillar
1), Trend Intelligence (Pillar 2), or Opportunity Intelligence (Pillar
3) — never invent claims.

---

## Sprint Sequencing Rationale

Sprints 1-5 build the differentiated core: expiry intelligence (Sprint
2), patent understanding (Sprint 3), trend explanations (Sprint 4),
patent figure plumbing (Sprint 4.5), and commercial usage discovery
(Sprint 5). Without these, the product is a generic patent viewer.

Sprint 4.5 (Patent Figure Ingestion) is a short bridge sprint that
unlocks visual cards in Sprint 6's Patent News Feed. Link-only approach
keeps it small (~1 day of work).

Sprint 6 expands from the original "topics/newsletter" scope to include
the **Patent News Feed and Highlights data layer** — the engagement
surfaces from the broader product vision (`PRODUCT_STRATEGY.md` Surface
Map sections #2 and #3). One unified sprint because all three surfaces
(Today, News Feed, Newsletter) consume the same `highlight_cards` table.

Sprint 7 (SaaS Foundation — auth, billing, quotas, multi-tenancy) is
required before launching paid tiers. Revenue target is 12 months out
(mid-2027), so Sprint 7 can land after Sprints 2-6 prove product value.

Sprint 8 (Commercial API & Exports) maps directly to the **Pro** and
**Team** pricing tiers and depends on Sprint 7's auth/quotas. Comes last
in the core roadmap because it monetizes a proven product surface.

### Sequencing alternatives

If revenue timing changes (need to charge within 3-6 months), reorder:
1. Finish Sprint 2 (Expiry Radar)
2. Jump to Sprint 7 (SaaS Foundation — auth + billing only, defer
   quotas)
3. Resume Sprints 3-6
4. Land Sprint 8 after pricing tiers stabilize

Auth-only-first is a 2-week sprint if scoped tightly to signup/login +
Stripe Checkout. Quotas, multi-tenancy refinement, and team features
can defer.
