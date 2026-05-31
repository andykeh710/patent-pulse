     1|# Invention Index 8 — Development Roadmap
     2|
     3|Revised 2026-05-22. Priority order: expiry intelligence → trend
     4|intelligence → usage discovery → engagement → SaaS → content.
     5|
     6|## Completed
     7|
     8|### Phase 0 — Foundation
     9|- Patent ingestion (USPTO grants, EPO)
    10|- AI summarization pipeline
    11|- Interesting/opportunity scoring
    12|- Basic search and patent detail
    13|
    14|### Phase 1 — Patent Credibility
    15|- Legal status, expiry estimation, family data, citations
    16|- Opportunity tabs, scoring breakdowns, tags
    17|
    18|### Phase 2 — Navigation & Today Page
    19|- Navigation rebuild, Today page with freshness and priority watch
    20|
    21|### Phase 3 — User-Created Topics
    22|- Topic CRUD, keyword matching, 6 default topic packs
    23|
    24|### Phase 4.1 — Content Generation (MVP)
    25|- LinkedIn post generation from patents (shipped as downstream feature)
    26|
    27|---
    28|
    29|## Upcoming
    30|
    31|### Sprint 1 — Repo & Agent Alignment ✅ Done
    32|
    33|Goal: Hermes and project docs reflect the new product direction.
    34|
    35|- [x] Update Hermes memory with new priority order
    36|- [x] Create `PRODUCT_STRATEGY.md`
    37|- [x] Create `ROADMAP.md`
    38|- [x] Create `AGENTS.md` with repo-level development rules
    39|- [x] Add Product Pillars, Surface Map, and Pricing Tiers to strategy doc (2026-05-22 revision)
    40|- [x] Verified Hermes prioritizes expiry/trend/usage over content generation
    41|
    42|Acceptance: Hermes stops treating LinkedIn/content as default priority.
    43|Future code work is judged against expiry/trend/usage value.
    44|
    45|---
    46|
    47|### Sprint 2 — Expiry Radar 2.0 🔄 In progress
    48|
    49|Status (2026-05-22): Sprint 2A ✅, Sprint 2B ✅ (178 tests pass),
    50|Sprint 2C in active development.
    51|
    52|Goal: Turn `/expiry` from a table of estimated dates into a credible
    53|product surface for expired and expiring opportunities.
    54|
    55|User question: "Which patents are expiring or expired soon, which ones
    56|matter, and what can I do with that information?"
    57|
    58|Delivered in three slices — do not attempt all at once.
    59|
    60|#### Sprint 2A — Assessment Foundation
    61|
    62|Goal: Create the data layer and deterministic assessment logic.
    63|
    64|- [ ] `expiry_assessments` migration: id, patent_publication_id,
    65|  estimated_expiry_date, expiry_status, expiry_status_confidence,
    66|  maintenance_status, maintenance_status_source, active_family_risk,
    67|  active_family_risk_reason, terminal_disclaimer_flag,
    68|  patent_term_adjustment_days, legal_caveats, assessment_json,
    69|  computed_at, source_updated_at
    70|- [ ] Indexes on: patent_publication_id, expiry_status,
    71|  expiry_status_confidence, estimated_expiry_date, active_family_risk
    72|- [ ] ORM model `ExpiryAssessment`
    73|- [ ] Deterministic assessment engine in `backend/app/expiry/assessment.py`:
    74|  `compute_expiry_assessment(patent, family_members, as_of_date)`
    75|- [ ] Idempotent backfill task: `backend/app/tasks/expiry_assessments.py`
    76|- [ ] Backend tests for all assessment rules
    77|- [ ] No UI changes yet
    78|
    79|Allowed expiry_status values: `active_estimated`, `expiring_soon`,
    80|`expired_estimated`, `lapsed_possible`, `lapsed_confirmed`,
    81|`expired_confirmed`, `unknown`.
    82|
    83|Allowed confidence values: `low`, `medium`, `high`, `confirmed`.
    84|
    85|Guardrails:
    86|- No invented maintenance-fee data — use `unknown` when unavailable
    87|- No "free to use" or "public domain" language
    88|- Always distinguish estimated from confirmed
    89|- Missing dates → `unknown` status
    90|
    91|#### Sprint 2B — API + Scoring
    92|
    93|Goal: Make expiry intelligence queryable.
    94|
    95|- [ ] `expiry_opportunity_score` on `expiry_assessments` (separate from
    96|  general opportunity_score)
    97|- [ ] Upgraded `/api/v1/expiry` with filters: expiry_status, confidence,
    98|  maintenance_status, active_family_risk, expiry_window, cpc, assignee,
    99|  industry, min_expiry_opportunity_score
   100|- [ ] `GET /api/v1/expiry/opportunities` — high-value candidates
   101|- [ ] `GET /api/v1/expiry/clusters` — patent cliffs
   102|- [ ] `GET /api/v1/expiry/summary` — dashboard cards
   103|- [ ] Backend tests for all filters and sorts
   104|- [ ] Old `/expiry` UI must not break
   105|
   106|#### Sprint 2C — Expiry Radar UI
   107|
   108|Goal: Turn `/expiry` into the core product surface.
   109|
   110|- [ ] Rename page label to "Expiry Radar" (keep route `/expiry`)
   111|- [ ] Sections: Expiring Soon, Recently Expired, Likely Lapsed,
   112|  Revival Candidates, Patent Cliffs, High-Opportunity Expirations,
   113|  Needs Legal Verification
   114|- [ ] Every card shows: expiry date, status, confidence, active family
   115|  risk, opportunity scores, trend linkage, usage signal count
   116|- [ ] "Verify with official registers" caveat on every card
   117|- [ ] Empty states explain legal uncertainty
   118|- [ ] CSV export using current filters (URL-state backed if possible)
   119|- [ ] No "free to use" or "public domain" language anywhere
   120|
   121|Guardrails (apply across all slices):
   122|- No patent labeled "free to use"
   123|- Expiry status explicitly estimated vs confirmed
   124|- Active family risk always visible
   125|- Empty states explain why a patent is not safe to treat as expired
   126|
   127|---
   128|
   129|### Sprint 3 — Patent Detail Credibility
   130|
   131|Goal: A patent-literate user can assess a patent without leaving.
   132|
   133|- [ ] Claims tab: independent/dependent claims, plain-English summary,
   134|  key mechanisms, broadness indicators
   135|- [ ] Family tab: family members, jurisdictions, dates, active/expired
   136|  members, relationship type, active family risk
   137|- [ ] External links: USPTO, Google Patents, Espacenet, WIPO
   138|- [ ] Similar patents panel (using existing semantic search)
   139|- [ ] Citation indicators (forward/backward, if available)
   140|- [ ] Assignee clickable → company profile page
   141|- [ ] Inventor names displayed
   142|
   143|---
   144|
   145|### Sprint 4 — Trend Intelligence Drilldowns
   146|
   147|Goal: Trends become explainable and actionable, not just counts.
   148|
   149|- [ ] Trend cards clickable → drilldown page
   150|- [ ] Show patents driving each trend
   151|- [ ] Show assignees driving each trend
   152|- [ ] Show change over time
   153|- [ ] Link trends to expiring patents (same CPC/tag area)
   154|- [ ] Trend narratives for top trends (AI-generated, artifact-cached)
   155|- [ ] "Why this trend matters" summaries
   156|
   157|---
   158|
   159|### Sprint 4.5 — Patent Figure Ingestion (link-only)
   160|
   161|Goal: Make patent figures visible across the product. Required before
   162|Sprint 6 ships a visual News Feed.
   163|
   164|Approach: **Link-only**. Store first-figure URLs pointing to official
   165|patent office endpoints (USPTO PDF/TIFF, Google Patents thumbnail). No
   166|local image hosting, no re-publication. Zero storage cost, no licensing
   167|review needed.
   168|
   169|- [ ] Add `figure_url` (string, nullable) and `figure_count` (int) to
   170|  `patent_publications` via migration
   171|- [ ] During ingestion, compute USPTO/Google Patents figure URL from
   172|  `publication_number` (e.g.
   173|  `https://patents.google.com/patent/{pub_number}/thumbnails`)
   174|- [ ] Backfill task for existing ~50k patents
   175|- [ ] Patent detail page: render first figure as a thumbnail when present
   176|- [ ] Patent card: optional small figure thumbnail when available
   177|- [ ] Empty state when figure URL is null (no broken image icons)
   178|- [ ] Backend tests: figure_url populated on ingest, backfill task is
   179|  idempotent
   180|
   181|Guardrails:
   182|- Never host or re-serve figure images — embed via remote `<img src>` only
   183|- Display "Image © patent office — verify at source" attribution on hover
   184|
   185|---
   186|
   187|### Sprint 5 — Commercial Usage Signals MVP
   188|
   189|Goal: For an expired/expiring patent, show whether newer patents or
   190|market-adjacent technology suggest current relevance. Never overclaim.
   191|
   192|#### Data Model
   193|
   194|- [ ] `usage_evidence` table: source_type (forward_citation, newer_patent,
   195|  company_product_page, press_release, technical_article, marketplace_listing,
   196|  standard_document, open_source_repo), source_name, source_url, snippet,
   197|  evidence_text, matched_terms, confidence, retrieved_at
   198|- [ ] `patent_usage_signals` table: score, confidence, summary,
   199|  market_categories, companies, products, evidence_count,
   200|  strongest_evidence_ids, limitations
   201|
   202|#### Implementation (MVP scope)
   203|
   204|- [ ] Forward citations as evidence
   205|- [ ] Semantically similar newer patents as evidence
   206|- [ ] Usage signal score computation
   207|- [ ] Patent detail panel: "Commercial Usage Signals" with evidence list,
   208|  score, confidence, limitations, source links
   209|- [ ] Expiry Radar filter: `has_usage_signals`, `usage_signal_score >= X`
   210|- [ ] Usage signal narrative (AI artifact)
   211|
   212|#### Language Rules
   213|
   214|- Never: "this patent is used in Product X"
   215|- Prefer: "appears related to," "shows technical overlap with,"
   216|  "suggests market relevance," "may indicate commercial usage"
   217|- Always show evidence tier and source links
   218|- Always include limitations
   219|
   220|---
   221|
   222|### Sprint 6 — Topics, Patent News Feed, Highlights, Newsletters
   223|
   224|Goal: Users discover new patent activity through a daily/weekly feed and
   225|subscribe to topics for ongoing intelligence. Phase 3 already shipped
   226|basic topic CRUD; this sprint adds the content engine on top.
   227|
   228|#### 6A — Highlights data layer
   229|
   230|`highlight_cards` table is the curation layer that feeds Today, News
   231|Feed, and the Newsletter from one source.
   232|
   233|- [ ] `highlight_cards` table: id, type, source_type, source_id,
   234|  title, summary, score, reasons, computed_at, expires_at
   235|- [ ] Highlight types: `top_opportunity`, `filing_spike`,
   236|  `expiring_cluster`, `assignee_move`, `weird_patent`,
   237|  `cross_industry_idea`, `revival_candidate`
   238|- [ ] Daily generation job that rebuilds highlights from real data
   239|  (no LLM invention)
   240|- [ ] `GET /api/v1/highlights` with type filter
   241|- [ ] Backend tests for each highlight type
   242|
   243|#### 6B — Patent News Feed
   244|
   245|A visual feed of new filings/grants worth knowing about. Patent-focused,
   246|not generic news.
   247|
   248|- [ ] `/news` page with card grid
   249|- [ ] Each card: patent figure thumbnail (from Sprint 4.5), title,
   250|  assignee, "why this matters" line (1-sentence AI summary), CPC tag,
   251|  link to detail page
   252|- [ ] Filter by topic (uses Phase 3 user topics)
   253|- [ ] Default sort: newest filings with highest interesting_score
   254|- [ ] Patent-of-the-day pick (one curated highlight per day)
   255|- [ ] "Verify at patent office" link on every card
   256|
   257|**Editorial guardrail:** the "why this matters" line is generated from
   258|patent abstract + tags + opportunity_score — never invented. If no
   259|abstract, no line shown.
   260|
   261|#### 6C — Topics enhancement (alerts + matching)
   262|
   263|Build on Phase 3 topic CRUD with active monitoring.
   264|
   265|- [ ] Topic matching against newly ingested patents (currently manual)
   266|- [ ] Alert types: patent expiring soon, newly expired, usage signal
   267|  found, new filing spike, assignee starts filing, convergence signal,
   268|  high-opportunity patent
   269|- [ ] Topic detail page: latest matches, related trends, related expiry
   270|- [ ] Saved searches
   271|
   272|#### 6D — Newsletter delivery
   273|
   274|- [ ] Weekly topic-scoped newsletter rendered from highlight cards
   275|- [ ] Sections: top trends, new filings in your topics, expiring
   276|  opportunities, usage signals, companies moving, patent of the week
   277|- [ ] Email delivery (no auth required yet — uses anonymous user_id;
   278|  full multi-tenancy lands in Sprint 7)
   279|- [ ] Unsubscribe handling
   280|- [ ] Plaintext + HTML versions
   281|
   282|---
   283|
   284|### Sprint 7 — SaaS Foundation
   285|
   286|Goal: Product can safely charge users.
   287|
   288|- [ ] Authentication: signup, login, password reset, email verification
   289|- [ ] Multi-tenancy: user-owned topics, watchlists, alerts, newsletters
   290|- [ ] Stripe billing: checkout, annual plan, subscription status
   291|- [ ] Quotas: AI credits, saved topics, watchlist size, exports
   292|- [ ] Account page: subscription, billing portal, usage, preferences
   293|- [ ] Export: Markdown, CSV for lists, saved patent export
   294|
   295|---
   296|
   297|### Sprint 8 — Commercial API & Exports
   298|
   299|Goal: Enable Pro / Team pricing tiers via programmatic access.
   300|
   301|#### Commercial API
   302|
   303|- [ ] API key issuance (user-scoped) per Pro+ account
   304|- [ ] Rate-limited routes under `/api/commercial/v1/`:
   305|  patents, search, trends, opportunities, expiry, topics, highlights
   306|- [ ] Per-key usage tracking (calls, tokens, exports)
   307|- [ ] Quota enforcement aligned with pricing tier
   308|- [ ] Webhook delivery for alerts (new filings in topic, expiry events,
   309|  usage signals, assignee moves)
   310|- [ ] OpenAPI docs auto-published at `/api/commercial/v1/docs`
   311|
   312|#### Exports
   313|
   314|- [ ] CSV export for patents, opportunities, expiry, watchlist (Pro+)
   315|- [ ] JSON export for the same surfaces (Pro+)
   316|- [ ] Markdown export for patent detail + AI artifacts (Creator+)
   317|- [ ] PDF report generation (Pro+, post-MVP)
   318|- [ ] Background job queue for large exports with email-when-ready
   319|
   320|#### Integrations
   321|
   322|- [ ] Slack alert integration via webhooks (post-MVP)
   323|- [ ] Zapier/Make connectors (post-MVP, requires public API stability)
   324|
   325|---
   326|
   327|### Later — Content Studio (Downstream)
   328|
   329|LinkedIn 4.1 already shipped. Future additions:
   330|
   331|- [ ] Multi-patent roundups (one post summarizing 3-5 related patents)
   332|- [ ] X/Twitter thread generator
   333|- [ ] Newsletter paragraph generator (fits into Sprint 6 newsletter)
   334|- [ ] Founder idea memo generator
   335|- [ ] Investor angle memo generator
   336|- [ ] Custom report generation (PDF, branded)
   337|- [ ] Content scheduling
   338|
   339|All Content Studio outputs **must consume** Patent Intelligence (Pillar
   340|1), Trend Intelligence (Pillar 2), or Opportunity Intelligence (Pillar
   341|3) — never invent claims.
   342|
   343|---
   344|
   345|## Sprint Sequencing Rationale
   346|
   347|Sprints 1-5 build the differentiated core: expiry intelligence (Sprint
   348|2), patent understanding (Sprint 3), trend explanations (Sprint 4),
   349|patent figure plumbing (Sprint 4.5), and commercial usage discovery
   350|(Sprint 5). Without these, the product is a generic patent viewer.
   351|
   352|Sprint 4.5 (Patent Figure Ingestion) is a short bridge sprint that
   353|unlocks visual cards in Sprint 6's Patent News Feed. Link-only approach
   354|keeps it small (~1 day of work).
   355|
   356|Sprint 6 expands from the original "topics/newsletter" scope to include
   357|the **Patent News Feed and Highlights data layer** — the engagement
   358|surfaces from the broader product vision (`PRODUCT_STRATEGY.md` Surface
   359|Map sections #2 and #3). One unified sprint because all three surfaces
   360|(Today, News Feed, Newsletter) consume the same `highlight_cards` table.
   361|
   362|Sprint 7 (SaaS Foundation — auth, billing, quotas, multi-tenancy) is
   363|required before launching paid tiers. Revenue target is 12 months out
   364|(mid-2027), so Sprint 7 can land after Sprints 2-6 prove product value.
   365|
   366|Sprint 8 (Commercial API & Exports) maps directly to the **Pro** and
   367|**Team** pricing tiers and depends on Sprint 7's auth/quotas. Comes last
   368|in the core roadmap because it monetizes a proven product surface.
   369|
   370|### Sequencing alternatives
   371|
   372|If revenue timing changes (need to charge within 3-6 months), reorder:
   373|1. Finish Sprint 2 (Expiry Radar)
   374|2. Jump to Sprint 7 (SaaS Foundation — auth + billing only, defer
   375|   quotas)
   376|3. Resume Sprints 3-6
   377|4. Land Sprint 8 after pricing tiers stabilize
   378|
   379|Auth-only-first is a 2-week sprint if scoped tightly to signup/login +
   380|Stripe Checkout. Quotas, multi-tenancy refinement, and team features
   381|can defer.
   382|