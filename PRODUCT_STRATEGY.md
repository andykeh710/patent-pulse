     1|# Invention Index 8 — Product Strategy
     2|
     3|Revised 2026-05-22. Replaces the earlier "dashboard + content generation" framing.
     4|
     5|## Core Product Promise
     6|
     7|Invention Index 8 helps users discover **valuable expired and expiring patent
     8|knowledge**, understand **where technology is moving**, and identify
     9|**real-world commercial opportunities from patent disclosures**.
    10|
    11|## What Invention Index 8 Is
    12|
    13|An evidence-first patent intelligence system. Every insight is sourced
    14|from real patent data, citations, trends, and market signals — never
    15|invented or hallucinated.
    16|
    17|## What Invention Index 8 Is Not
    18|
    19|- A generic AI content generator (LinkedIn posts are an output format,
    20|  not the product).
    21|- A legal opinion service. We never claim a patent is "free to use" or
    22|  that a product definitively uses a patent.
    23|- A patent filing or prosecution tool.
    24|
    25|## Primary Users
    26|
    27|### 1. Founder / Builder
    28|
    29|Wants to know: what expired patents could inspire products? What
    30|problems did old inventions solve? Are these ideas resurfacing in
    31|modern markets? What could I build from this?
    32|
    33|### 2. Investor / Analyst
    34|
    35|Wants to know: what technology categories are heating up? Which
    36|companies are filing in new areas? Where are old patent cliffs
    37|creating opportunity? Which patent clusters suggest market shifts?
    38|
    39|### 3. R&D / Innovation Scout
    40|
    41|Wants to know: what are competitors filing? What expired inventions
    42|are relevant to current product lines? What technical mechanisms are
    43|reusable? What spaces are crowded or underexplored?
    44|
    45|### 4. Patent-Literate User
    46|
    47|Wants to know: what exactly do the claims say? Is this patent actually
    48|expired or just estimated? Is there active family risk? Who owns it?
    49|What related patents cite it?
    50|
    51|## Core Workflow
    52|
    53|```
    54|Find expired/expiring patent
    55|  → understand what it actually covers (claims, family, citations)
    56|  → check active family / legal risk
    57|  → see whether the idea appears in current markets (evidence-backed)
    58|  → save / track / alert / newsletter
    59|  → optionally generate content or report
    60|```
    61|
    62|## Feature Priority
    63|
    64|In descending order of importance:
    65|
    66|### Tier 1 — Core Differentiators
    67|1. **Expiry Radar**: comprehensive expiring/expired patent tracking with
    68|   confidence labels, active-family-risk awareness, maintenance-fee
    69|   awareness, and expiry-opportunity scoring.
    70|2. **Trend Intelligence**: filing trends with drilldowns into patents,
    71|   assignees, and expiry intersections — not just counts but explanations.
    72|3. **Commercial Usage Signals**: evidence-backed discovery of where
    73|   expired/expiring patent ideas appear in current products, companies,
    74|   markets, or newer patents. Confidence-tiered and caveated. Never
    75|   overclaims.
    76|
    77|### Tier 2 — Engagement & Retention
    78|4. **Patent Understanding**: claims display, family viewer, citations,
    79|   assignee profiles, external patent-office links, similar patents.
    80|5. **Topics, Alerts, Newsletters**: user-created topic subscriptions
    81|   delivering expiry, trend, and usage-signal intelligence automatically.
    82|
    83|### Tier 3 — Commercial Foundation
    84|6. **SaaS Readiness**: authentication, multi-tenancy, Stripe billing,
    85|   quotas, exports, account management.
    86|
    87|### Tier 4 — Downstream Packaging
    88|7. **Content Generation**: LinkedIn posts, reports, newsletters — all
    89|   consuming the intelligence layers above, not replacing them.
    90|
    91|## Language and Evidence Rules
    92|
    93|These apply to all product surfaces — UI, API responses, AI-generated
    94|narratives, and marketing.
    95|
    96|Invention Index 8 should produce evidence-backed opportunity hypotheses, not
    97|legal determinations or infringement/use conclusions.
    98|
    99|For expired or expiring patents, the product should help users
   100|prioritize what to investigate, not decide whether they can legally use
   101|an invention.
   102|
   103|### Expiry Claims
   104|- Always distinguish **estimated** from **confirmed** expiry status.
   105|- Always show active family risk when present.
   106|- Never label any patent "free to use" or "public domain."
   107|- Always include "verify with official registers" caveats.
   108|
   109|### Commercial Usage Claims
   110|- Never say "this patent is used in Product X."
   111|- Prefer: "appears related to," "shows technical overlap with,"
   112|  "suggests market relevance," "may indicate commercial usage."
   113|- Always show evidence tier (strong / medium / weak) and source links.
   114|- Always include limitations.
   115|
   116|### AI-Generated Content
   117|- All AI output is labeled as AI-generated.
   118|- Source citations and evidence IDs included where available.
   119|- Confidence levels shown.
   120|
   121|## What Is Deferred
   122|
   123|- Patent filing / prosecution workflows
   124|- Legal opinions or freedom-to-operate analysis
   125|- Real-time patent monitoring (batch refresh only for V1)
   126|- Multi-language support beyond English
   127|- Mobile native apps (web-first)
   128|
   129|## Competitive Positioning
   130|
   131|Most patent tools target attorneys and large IP departments. Patent
   132|Pulse targets **builders, investors, and scouts** who want to
   133|understand what patent knowledge is available and actionable — without
   134|needing a law degree.
   135|
   136|The differentiation is:
   137|- **Expiry-first**: most tools treat expiry as a filter; we treat it as
   138|  the primary lens.
   139|- **Evidence-backed, not invented**: every signal has a source.
   140|- **Commercial relevance, not legal advice**: we help users discover
   141|  opportunities, not make legal determinations.
   142|
   143|## Product Pillars
   144|
   145|The product organizes into four conceptual pillars. The Feature Priority
   146|list above is the implementation order. The pillars are how we describe
   147|the product externally (marketing, sales, docs).
   148|
   149|### Pillar 1 — Patent Intelligence
   150|Understanding any single patent quickly: claims, family, citations,
   151|assignees, legal status, similar patents. Powers every other pillar.
   152|
   153|### Pillar 2 — Trend Intelligence
   154|What is happening across patent activity: filing velocity, CPC heat,
   155|assignee movement, convergence signals, patent cliffs.
   156|
   157|### Pillar 3 — Opportunity Intelligence
   158|What can a user do with patent knowledge: expiring patents worth
   159|investigating, revival candidates, cross-industry applications,
   160|commercial usage signals.
   161|
   162|### Pillar 4 — Distribution & Commercialization
   163|How intelligence reaches the user: Today dashboard, Patent News Feed,
   164|Highlights, Topics, Newsletters, Content Studio, Commercial API,
   165|Exports.
   166|
   167|## Product Surface Map
   168|
   169|Ten user-facing sections compose the product. Status reflects shipped vs
   170|planned; sprint number references `ROADMAP.md`.
   171|
   172|| # | Section | Scope | Status |
   173||---|---|---|---|
   174|| 1 | **Today** | Editorial homepage: top opportunities, emerging trends, expiring soon, companies moving | Shipped (Phase 2) |
   175|| 2 | **Patent News Feed** | Visual cards of new filings/grants in user-interesting areas, with patent figures and external links | Planned (Sprint 6) |
   176|| 3 | **Highlights** | Curated cards: top opportunity, weird patent, assignee move, cross-industry idea, etc. | Planned (Sprint 6) |
   177|| 4 | **Trends** | Hot, Growing, Convergence, Patent Cliffs — with drilldowns | Partial (Sprint 4 deepens) |
   178|| 5 | **Opportunities** | Tabbed feed: Top, Startup, Enterprise, Cross-industry, Revival, Sustainability, Legal review | Shipped (Phase 1), enhanced by Sprint 5 |
   179|| 6 | **Expiry Radar** | Expiring Soon, Recently Expired, Likely Lapsed, Revival Candidates, Patent Cliffs, High-Opportunity, Needs Verification | In progress (Sprint 2C) |
   180|| 7 | **Topics** | User-created tracked areas with keyword + CPC + opportunity filters | Shipped (Phase 3) |
   181|| 8 | **Newsletter** | Weekly digest scoped to user topics: filings, expiry, trends, usage signals | Planned (Sprint 6) |
   182|| 9 | **Content Studio** | Generate LinkedIn posts, X threads, newsletter blurbs, article outlines from real patent intelligence | Partial (LinkedIn 4.1 shipped) |
   183|| 10 | **Commercial API & Exports** | REST API, webhooks, CSV/JSON/Markdown exports for Pro/Team tiers | Planned (Sprint 8) |
   184|
   185|## Pricing Tiers
   186|
   187|These are **target** pricing — not committed launch numbers. Final
   188|pricing requires a cost-model verification (AI compute per user, storage,
   189|egress) which has not yet been done.
   190|
   191|| Tier | Price (target) | Audience | Includes |
   192||---|---|---|---|
   193|| **Free** | $0 | Acquisition | Public highlights, limited search/trends, 1 topic, newsletter preview, no exports, no AI generation |
   194|| **Lite** | $10/yr | Casual consumer | Today, weekly newsletter, 3 topics, 25 watchlist items, precomputed AI summaries, limited content idea browsing, no API |
   195|| **Creator** | $49/yr or $5/mo | Content creator (you) | Lite + 25 topics, Content Studio, LinkedIn/X/newsletter generation, saved drafts, Markdown export, topic-specific newsletters |
   196|| **Pro** | $199/yr or $19/mo | Analyst / scout | Creator + advanced search, full Expiry Radar, CSV exports, alerts, assignee profiles, usage signals, light API access |
   197|| **Team** | Custom | Companies | Pro + team seats, full API, webhooks, large exports, private topics, shared watchlists, custom quotas |
   198|
   199|**Cost-model risk:** $10/yr Lite may not cover AI compute even at heavy
   200|precomputation. Before launching paid tiers we need: per-user compute
   201|attribution, AI credit accounting, and a margin check at each tier.
   202|Tracked in Sprint 7 (SaaS Foundation).
   203|
   204|**What "unlimited content" means:** Unlimited *idea feed* (precomputed
   205|trends, highlights, patent picks). AI *drafting* is credit-based per
   206|tier. This protects margins.
   207|