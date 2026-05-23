# Patent Pulse — Product Strategy

Revised 2026-05-22. Replaces the earlier "dashboard + content generation" framing.

## Core Product Promise

Patent Pulse helps users discover **valuable expired and expiring patent
knowledge**, understand **where technology is moving**, and identify
**real-world commercial opportunities from patent disclosures**.

## What Patent Pulse Is

An evidence-first patent intelligence system. Every insight is sourced
from real patent data, citations, trends, and market signals — never
invented or hallucinated.

## What Patent Pulse Is Not

- A generic AI content generator (LinkedIn posts are an output format,
  not the product).
- A legal opinion service. We never claim a patent is "free to use" or
  that a product definitively uses a patent.
- A patent filing or prosecution tool.

## Primary Users

### 1. Founder / Builder

Wants to know: what expired patents could inspire products? What
problems did old inventions solve? Are these ideas resurfacing in
modern markets? What could I build from this?

### 2. Investor / Analyst

Wants to know: what technology categories are heating up? Which
companies are filing in new areas? Where are old patent cliffs
creating opportunity? Which patent clusters suggest market shifts?

### 3. R&D / Innovation Scout

Wants to know: what are competitors filing? What expired inventions
are relevant to current product lines? What technical mechanisms are
reusable? What spaces are crowded or underexplored?

### 4. Patent-Literate User

Wants to know: what exactly do the claims say? Is this patent actually
expired or just estimated? Is there active family risk? Who owns it?
What related patents cite it?

## Core Workflow

```
Find expired/expiring patent
  → understand what it actually covers (claims, family, citations)
  → check active family / legal risk
  → see whether the idea appears in current markets (evidence-backed)
  → save / track / alert / newsletter
  → optionally generate content or report
```

## Feature Priority

In descending order of importance:

### Tier 1 — Core Differentiators
1. **Expiry Radar**: comprehensive expiring/expired patent tracking with
   confidence labels, active-family-risk awareness, maintenance-fee
   awareness, and expiry-opportunity scoring.
2. **Trend Intelligence**: filing trends with drilldowns into patents,
   assignees, and expiry intersections — not just counts but explanations.
3. **Commercial Usage Signals**: evidence-backed discovery of where
   expired/expiring patent ideas appear in current products, companies,
   markets, or newer patents. Confidence-tiered and caveated. Never
   overclaims.

### Tier 2 — Engagement & Retention
4. **Patent Understanding**: claims display, family viewer, citations,
   assignee profiles, external patent-office links, similar patents.
5. **Topics, Alerts, Newsletters**: user-created topic subscriptions
   delivering expiry, trend, and usage-signal intelligence automatically.

### Tier 3 — Commercial Foundation
6. **SaaS Readiness**: authentication, multi-tenancy, Stripe billing,
   quotas, exports, account management.

### Tier 4 — Downstream Packaging
7. **Content Generation**: LinkedIn posts, reports, newsletters — all
   consuming the intelligence layers above, not replacing them.

## Language and Evidence Rules

These apply to all product surfaces — UI, API responses, AI-generated
narratives, and marketing.

Patent Pulse should produce evidence-backed opportunity hypotheses, not
legal determinations or infringement/use conclusions.

For expired or expiring patents, the product should help users
prioritize what to investigate, not decide whether they can legally use
an invention.

### Expiry Claims
- Always distinguish **estimated** from **confirmed** expiry status.
- Always show active family risk when present.
- Never label any patent "free to use" or "public domain."
- Always include "verify with official registers" caveats.

### Commercial Usage Claims
- Never say "this patent is used in Product X."
- Prefer: "appears related to," "shows technical overlap with,"
  "suggests market relevance," "may indicate commercial usage."
- Always show evidence tier (strong / medium / weak) and source links.
- Always include limitations.

### AI-Generated Content
- All AI output is labeled as AI-generated.
- Source citations and evidence IDs included where available.
- Confidence levels shown.

## What Is Deferred

- Patent filing / prosecution workflows
- Legal opinions or freedom-to-operate analysis
- Real-time patent monitoring (batch refresh only for V1)
- Multi-language support beyond English
- Mobile native apps (web-first)

## Competitive Positioning

Most patent tools target attorneys and large IP departments. Patent
Pulse targets **builders, investors, and scouts** who want to
understand what patent knowledge is available and actionable — without
needing a law degree.

The differentiation is:
- **Expiry-first**: most tools treat expiry as a filter; we treat it as
  the primary lens.
- **Evidence-backed, not invented**: every signal has a source.
- **Commercial relevance, not legal advice**: we help users discover
  opportunities, not make legal determinations.

## Product Pillars

The product organizes into four conceptual pillars. The Feature Priority
list above is the implementation order. The pillars are how we describe
the product externally (marketing, sales, docs).

### Pillar 1 — Patent Intelligence
Understanding any single patent quickly: claims, family, citations,
assignees, legal status, similar patents. Powers every other pillar.

### Pillar 2 — Trend Intelligence
What is happening across patent activity: filing velocity, CPC heat,
assignee movement, convergence signals, patent cliffs.

### Pillar 3 — Opportunity Intelligence
What can a user do with patent knowledge: expiring patents worth
investigating, revival candidates, cross-industry applications,
commercial usage signals.

### Pillar 4 — Distribution & Commercialization
How intelligence reaches the user: Today dashboard, Patent News Feed,
Highlights, Topics, Newsletters, Content Studio, Commercial API,
Exports.

## Product Surface Map

Ten user-facing sections compose the product. Status reflects shipped vs
planned; sprint number references `ROADMAP.md`.

| # | Section | Scope | Status |
|---|---|---|---|
| 1 | **Today** | Editorial homepage: top opportunities, emerging trends, expiring soon, companies moving | Shipped (Phase 2) |
| 2 | **Patent News Feed** | Visual cards of new filings/grants in user-interesting areas, with patent figures and external links | Planned (Sprint 6) |
| 3 | **Highlights** | Curated cards: top opportunity, weird patent, assignee move, cross-industry idea, etc. | Planned (Sprint 6) |
| 4 | **Trends** | Hot, Growing, Convergence, Patent Cliffs — with drilldowns | Partial (Sprint 4 deepens) |
| 5 | **Opportunities** | Tabbed feed: Top, Startup, Enterprise, Cross-industry, Revival, Sustainability, Legal review | Shipped (Phase 1), enhanced by Sprint 5 |
| 6 | **Expiry Radar** | Expiring Soon, Recently Expired, Likely Lapsed, Revival Candidates, Patent Cliffs, High-Opportunity, Needs Verification | In progress (Sprint 2C) |
| 7 | **Topics** | User-created tracked areas with keyword + CPC + opportunity filters | Shipped (Phase 3) |
| 8 | **Newsletter** | Weekly digest scoped to user topics: filings, expiry, trends, usage signals | Planned (Sprint 6) |
| 9 | **Content Studio** | Generate LinkedIn posts, X threads, newsletter blurbs, article outlines from real patent intelligence | Partial (LinkedIn 4.1 shipped) |
| 10 | **Commercial API & Exports** | REST API, webhooks, CSV/JSON/Markdown exports for Pro/Team tiers | Planned (Sprint 8) |

## Pricing Tiers

These are **target** pricing — not committed launch numbers. Final
pricing requires a cost-model verification (AI compute per user, storage,
egress) which has not yet been done.

| Tier | Price (target) | Audience | Includes |
|---|---|---|---|
| **Free** | $0 | Acquisition | Public highlights, limited search/trends, 1 topic, newsletter preview, no exports, no AI generation |
| **Lite** | $10/yr | Casual consumer | Today, weekly newsletter, 3 topics, 25 watchlist items, precomputed AI summaries, limited content idea browsing, no API |
| **Creator** | $49/yr or $5/mo | Content creator (you) | Lite + 25 topics, Content Studio, LinkedIn/X/newsletter generation, saved drafts, Markdown export, topic-specific newsletters |
| **Pro** | $199/yr or $19/mo | Analyst / scout | Creator + advanced search, full Expiry Radar, CSV exports, alerts, assignee profiles, usage signals, light API access |
| **Team** | Custom | Companies | Pro + team seats, full API, webhooks, large exports, private topics, shared watchlists, custom quotas |

**Cost-model risk:** $10/yr Lite may not cover AI compute even at heavy
precomputation. Before launching paid tiers we need: per-user compute
attribution, AI credit accounting, and a margin check at each tier.
Tracked in Sprint 7 (SaaS Foundation).

**What "unlimited content" means:** Unlimited *idea feed* (precomputed
trends, highlights, patent picks). AI *drafting* is credit-based per
tier. This protects margins.
