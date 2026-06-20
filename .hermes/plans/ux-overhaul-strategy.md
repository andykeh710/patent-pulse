# Invention Index 8 — UX/UI Overhaul Strategy

**Discovery & Strategy Document**
Prepared: 2026-06-19
Status: Draft — pending product owner review
Scope: V3 stabilization → V4 Community Intelligence Layer

---

## Part 1 — Product Understanding

### What Invention Index 8 Is

Invention Index 8 is an evidence-first patent intelligence system. It ingests real patent
data from USPTO, EPO, and WIPO; computes deterministic assessments (expiry estimates,
opportunity scores, trend signals, commercial usage evidence); and presents that intelligence
through a web application that helps users understand what patent knowledge exists, where
technology is moving, and what opportunities are emerging — without inventing data, claiming
legal authority, or pretending to be a law firm.

**The job it performs better than ordinary patent search:**

1. **Expiry-first lens.** Most tools treat expiry as a filter column. II8 treats it as the
   primary organizing principle — confidence-labeled, family-risk-aware, opportunity-scored.

2. **Evidence-backed, not hallucinated.** Every signal has provenance: a patent record, a
   filing date, a citation chain, a CPC code. AI narratives summarize evidence but never
   create it.

3. **Commercial relevance without overclaiming.** The product says "this idea appears in
   newer patents" and shows the citations — never "this patent is used in Product X."

4. **Personalized intelligence.** Today learns from saved patents, followed companies, and
   subscribed topics. The feed explains *why* each signal was shown.

### What It Is Not

- Not a generic patent database or search engine
- Not a legal opinion service
- Not a patent filing tool
- Not a social network (yet — V4 adds community *on top* of intelligence)
- Not an AI content generator (content is downstream packaging)

### Who It Serves

Six user types with different needs and trust expectations:

| User | Primary Need | Trust Requirement | Current UX Gap |
|------|-------------|-------------------|----------------|
| Founder/Inventor | Is this idea space crowded? What's expiring? | Clarity, not legalese. Warning before public disclosure. | Too much patent jargon. No disclosure warning. |
| Investor/Analyst | Trend signals, company movement, expiry opportunity | Speed, credibility, signal quality | Too slow to scan. No summary-first view. |
| Engineer/Researcher | Technical depth, prior art, evidence | Source-grounded, verifiable | Patent detail is strong. But tabs hide signal. |
| Patent Professional | Accurate dates, caveats, family risk, legal status | Must be able to verify everything | Expiry and legal tabs are good but buried in 6 tabs. |
| Corporate Innovation | Company landscapes, competitors, expiry exposure | Portfolio-level accuracy | Company page is data-heavy, not insight-first. |
| Community Contributor (V4) | Identity, reputation, public sharing | Source-grounded, moderation | No surfaces exist yet. |

---

## Part 2 — Current UX Map

### Today

**Purpose:** Daily briefing — personalized intelligence feed for returning users.

**Current strengths:**
- Evidence-backed insight cards with type, confidence, why-it-matters
- V3.2 personalized For You feed with why-shown reasoning
- First-time welcome with starter topics
- Data state awareness (comparison_label shows last visit window)

**Current weaknesses:**
- **Two separate "For You" sections** — InsightCard-based one at top, ForYouCard-based one
  below. Same header label, different card styles. Confusing.
- **Sections compete for attention** — For You, More Signals, Your Topics, Expiring
  Opportunities, Companies Moving, Platform Overview, Recommended Actions = 7 sections
  on one page. Cognitive overload.
- **Platform Overview is corporate-speak** — "Platform Overview" vs meaningful label.
  Factual stats without narrative connection.
- **Recommended Actions are generic** — same 4 links every visit, regardless of user state.
- **No return-trigger** — nothing says "come back because X changed."
- **No visual entry point hierarchy** — everything is same-level.

**Redesign opportunity:** High. This is the home screen. Should be the strongest UX in the
product. Needs a clear visual narrative: "Here's what changed since you last looked, here's
why it matters, here's what you can do next."

---

### Search

**Purpose:** Find patents by keyword, semantic meaning, or hybrid.

**Current strengths:**
- Three search modes (keyword, semantic, hybrid)
- URL-state-driven filters (sort, legal status)
- Saved searches with naming
- Example query chips for empty state
- Clear result counts and pagination

**Current weaknesses:**
- **Mode toggles feel like settings, not discovery tools** — small pill buttons below
  the search bar. Users may not discover semantic search.
- **Saved searches are buried below the empty state** — only visible when no search is
  active.
- **No search suggestions or autocomplete.**
- **Search bar is generic input** — no rich query builder, no CPC suggestions, no
  assignee autocomplete.
- **Result cards are uniform** — same PatentCard component regardless of match quality,
  search mode, or relevance score.

**Redesign opportunity:** Medium. Core flow works. Improve discovery of modes, add search
history/suggestions, differentiate result presentation by match quality.

---

### Patent Detail

**Purpose:** Deep understanding of a single patent — claims, family, citations, expiry,
commercial signals, AI narratives.

**Current strengths:**
- Executive Summary above the fold with title, assignee, scores, actions
- Data Completeness Panel showing what fields are available/missing
- Six tabs with organized content (Overview, Commercial, Claims, Citations, Legal/Expiry, Similar)
- AI panels with loading states, artifact caching, generate-on-demand
- External patent links, figure panel, source attribution
- Watchlist toggle, copy link, ask AI actions

**Current weaknesses:**
- **Information overload.** ExecutiveSummary + FreshnessBanner + 6 tabs + DataCompleteness
  panel. A user with 10 seconds gets hit with 15+ visual elements.
- **Tabs hide signal.** Commercial tab contains 5 AI panels (Why Now, Opportunity Narrative,
  Trend Snapshot, Assignee Intelligence, Usage Signals). Each requires a "Generate" button.
  The most valuable intelligence is behind 2 clicks.
- **Claims tab is bare.** Just dumps raw claims text — no plain-English summary inside the
  tab, no broadness indicators, no mechanism highlighting.
- **Citations tab is a list.** No citation graph, no directional analysis, no "forward
  citation velocity."
- **Legal/Expiry tab is a panel.** Not broken out as a primary visual element — yet expiry
  is the core differentiator.
- **Two score badges (Opportunity + Interesting) compete visually** for the same space.

**Redesign opportunity:** Very high. This is the most data-rich page. Needs progressive
disclosure that works at 10-second, 2-minute, and deep-research depths.

---

### Company Intelligence

**Purpose:** Browse and understand patent assignees — portfolio strength, technology focus,
expiry exposure, geographic distribution.

**Current strengths:**
- Composite scoring (patent count + active grants + tech breadth + signal score + expiry exposure)
- Company ranking table with sortable columns
- Country-level distribution visualization
- Honest enrichment status ("Enrichment pending" when no external data)

**Current weaknesses:**
- **The main Companies page is a data table with 4 summary cards above it.** No visual
  narrative, no "why this company matters," no trend linkage to expiry.
- **Company detail is two-column but wastes the main column.** Recent patents are just a
  link list. No patent figures, no highlighted recent moves, no trend chart.
- **No time-series visualization.** "Are they filing more or fewer patents?" is answered
  only by numbers.
- **Technology Focus is a CPC code list with counts.** No visual map of patent landscape.
- **"Enrichment pending" is small text** — easy to miss.
- **Follow button and watchlist are on separate surfaces** — Watchlist page has "Followed
  Companies" tab but it's a flat link list.

**Redesign opportunity:** High. Company Intelligence should be a Bloomberg Terminal-style
profile — at-a-glance strength, movement, exposure, and drill-down.

---

### Expiry Radar

**Purpose:** Track patents approaching or past expiration with confidence labels and active
family risk awareness.

**Current strengths:**
- **7 sections** covering expiry lifecycle (Expiring Soon, Recently Expired, Likely Lapsed,
  Revival Candidates, Patent Cliffs, High-Opportunity, Needs Verification)
- **Legal caveat banner** prominently displayed
- **Confidence labels on every card** (expiry_status, expiry_confidence, active_family_risk)
- **Horizon tabs** for quick window switching
- **Rich filters** (status, confidence, family risk, score, sort)
- **CSV export** with current filter state
- **Honest empty states** explaining legal uncertainty

**Current weaknesses:**
- **7 sections is a lot of scrolling.** A user scanning quickly won't see Patent Cliffs or
  Needs Verification — they're below the fold.
- **Section layout is uniform** — all sections use the same ExpiryRadarSection component
  with the same visual weight. No differentiation between "high urgency" and "FYI."
- **Patent Cliffs are a separate visual style** (4-column grid of CliffCards) that breaks
  the pattern established by other sections.
- **Horizon tabs and FilterBar are separate controls** doing overlapping work. The "0-6 mo"
  horizon tab and the "days_ahead 180" filter dropdown are the same thing.
- **No "why this patent cliff matters" narrative.** Cliffs show counts — not opportunity
  context.

**Redesign opportunity:** Medium-high. The data infrastructure is strong. Layout needs
reorganization to surface urgency first and narrative second.

---

### Watchlist / Workspace

**Purpose:** Saved patents, followed companies, and saved searches — personal intelligence
space.

**Current strengths:**
- Three-tab organization (Saved Patents, Followed Companies, Saved Searches)
- Clean list design with metadata and actions
- Pagination for large watchlists
- Honest empty states with clear CTAs

**Current weaknesses:**
- **Tab labels are "Saved Patents" / "Followed Companies" / "Saved Searches"** — three
  different nouns. Not unified by a common concept.
- **Saved Patents list shows no delta** — "has this patent's expiry status changed since
  I saved it?" The watchlist should answer this.
- **No bulk actions** — can't export, can't create a collection, can't share a list.
- **No sort/filter** within saved patents — just chronological by save date.
- **"Your Workspace" title is too generic** — doesn't signal what value this page provides.

**Redesign opportunity:** Medium. Good foundation but needs to deliver on the "monitor"
promise — show what changed, not just what's saved.

---

### Topics / Themes

**Purpose:** User-created technology tracking with keyword and CPC matching.

**Current strengths:**
- CRUD with clear create form
- Starter topics for first-time users
- System themes vs user topics separation
- Follow/unfollow system themes
- Matched patents display when a topic is selected
- CPC prefix and keyword display on cards

**Current weaknesses:**
- **URL says /themes but label says "Topics."** Inconsistent naming.
- **Three sections on the same page** — Your Topics, System Themes, Following. No clear
  visual hierarchy.
- **Topic detail page (themes/[id]) is bare** — just name, description, CPC chips, and a
  patent list. No trend linkage, no expiry intersection, no alert configuration.
- **"System Themes" concept is confusing** — why are some topics "system" and others
  "yours"? The follow mechanic adds another layer.
- **Matched patents show in the same page** — pushes the topic list below the fold.

**Redesign opportunity:** High. Topics need their own dedicated detail page with
intelligence (trends, expiry, recent activity, alert config).

---

### Account / Preferences / Onboarding

**Purpose:** User identity, billing, subscriptions, preferences, and first-time setup.

**Current strengths:**
- Clean onboarding flow (5 steps: role, use_case, industry, interests, confirm)
- AI-suggested companies and themes on confirm step
- Subscription management with pause/resume/switch
- Danger zone with email confirmation

**Current weaknesses:**
- **Account page is two things at once** — Billing section and Subscriptions section.
  These are different mental models.
- **Onboarding is isolated** — once completed, can't revisit or update persona.
- **No explicit privacy/confidentiality warning** during onboarding. A founder typing
  "cancer drug delivery system" as an interest shouldn't be treated as a patent disclosure
  — but there's no messaging about this.
- **No "what will be public" preview** — important for V4 community features.
- **Account page linked from sidebar, not from main nav.** Low discoverability.

**Redesign opportunity:** Medium. Onboarding needs trust language. Account needs
reorganization before V4 profiles land.

---

### Freshness / Source Status

**Purpose:** Honest disclosure of data staleness, source unavailability, and ingestion
pipeline health.

**Current strengths:**
- FreshnessBanner appears on multiple pages (Today, Patent Detail, Trends, Opportunity)
- Four degradation levels: success/no-data (amber), partial failure (red), full failure
  (red), source lag (amber)
- Ingestion staleness warning after 7 days
- Trends staleness warning
- Clear language: "USPTO data APIs are currently unreachable"
- Always says "Verify against official patent registers"

**Current weaknesses:**
- **FreshnessBanner is mostly hidden** — only appears when there's an issue. Users don't
  know freshness monitoring exists until it breaks.
- **No proactive freshness indicator** — a subtle "data is current" indicator would build
  trust. Currently only negative states are shown.
- **UsageWarningBanner is a separate component** with different visual language — combines
  quota warnings with freshness in some contexts.
- **No historical freshness view** — "when was the last time data was truly current?"
- **Freshness information is per-page** — no unified system status page accessible from
  navigation.

**Redesign opportunity:** Low (current implementation is good). Add a subtle always-visible
freshness indicator in the footer or near the search bar. Add a /status or /health page.

---

### Trends

**Purpose:** Technology momentum, convergence signals, and patent cliff opportunities.

**Current strengths:**
- Four views: Hot Right Now, Fastest Growing, Convergence, Patent Cliffs
- Surface filters (CPC, tag, assignee)
- z-score and growth percentage displayed prominently
- Convergent technology pairs with growth ratio
- Cliff clusters with window selection

**Current weaknesses:**
- **Trend page is essentially a list** — no visualizations, no time-series charts, no sparklines.
- **CPC codes dominate the display but aren't human-readable without the CPC_LABELS map.**
- **Convergence is a different visual treatment** (pairs with arrows) that doesn't match
  other views.
- **No narrative context** — "G06N z-score 5.2" doesn't tell a story. The drilldown page
  (trends/[surface]/[key]) adds narrative but most users won't click.
- **Trends feel disconnected from Today** — the same trend signals should be sourceable
  from both surfaces.

**Redesign opportunity:** High. Needs visual data representation. Sparklines, mini bar
charts, or heat maps would make CPC velocity instantly scannable.

---

### Opportunity

**Purpose:** Patents ranked by opportunity score with tabbed filtering by opportunity type.

**Current strengths:**
- 8 tabs with clear helpers (Top, Expired, Revival, Cross-industry, Startup, Enterprise,
  Sustainability, Legal Review)
- Rich filter panel (tag, risk flag, legal confidence, industry, CPC, min score)
- Opportunity score badge and interesting score on each card
- Risk flags displayed prominently
- Source attribution on each result

**Current weaknesses:**
- **8 tabs is too many** — tab overflow on mobile, cognitive overload on desktop.
- **Tab helpers only appear on hover (title attribute)** — hidden from most users.
- **Filters are verbose** — 6 filter controls take 2-3 rows on desktop.
- **"Expired" vs "Revival" distinction is unclear** — both surface expired patents.
- **Opportunity score alone doesn't tell the story** — a patent with score 82 and one with
  score 78 look nearly identical. What makes the difference?
- **No save/share/compare actions** on individual results.

**Redesign opportunity:** Medium. Consolidate tabs, add action row, surface what drives
the score.

---

---

## Part 3 — User Journeys

### Journey 1: First-Time Founder/Inventor

**Entry point:** Marketing site → Sign up → Onboarding → Today

**Motivation:** "I have an idea for a product. Is someone else already patenting in this
space? Are there expired patents I can build on?"

**Current flow:**
1. Lands on marketing site, sees "Track the world's invention signals"
2. Signs up through login page
3. Enters 5-step onboarding (role: founder → use_case: build a product → industry:
   healthcare → interests: "drug delivery implant" → confirm)
4. Arrives at Today with starter topics but **no immediate answer to their question**
5. Today shows: "0 patents in your watchlist," empty For You feed, generic Platform Overview
6. They have to navigate to /search to actually answer their question
7. They type "drug delivery implant" into search — results appear
8. **Aha moment:** Seeing patent detail with claims, expiry status, similar patents
9. **Friction:** No warning that typing "drug delivery implant" as a search is public
   server-side, not a confidential disclosure — but also no warning about accidentally
   disclosing trade secrets if they type "my specific implant mechanism using X."

**Ideal journey:**
1. Sign up → Onboarding includes: "II8 uses your interests to find relevant patents.
   Your interests are private. Never share confidential invention details in public
   surfaces."
2. After onboarding, Today immediately shows: "3 patents matching your interest in
   drug delivery implants" with evidence-backed cards.
3. First card: "Patent US12345678 — Biodegradable implant with controlled release" +
   "Why this matches: contains drug delivery + implant" + "Expiry: estimated 2028."
4. **First action:** "View patent" — see Executive Summary with "Why it matters" and
   "Save to watchlist."
5. **Return trigger:** "We'll notify you when new patents match 'drug delivery implant.'"

### Journey 2: Returning Investor/Analyst

**Entry point:** Direct to /today (bookmarked)

**Motivation:** "What changed since last week? Any company making moves in battery tech?
Anything expiring in energy storage?"

**Current flow:**
1. Today loads with 7 sections
2. For You might show a followed company surge if they've set up follows
3. More Signals shows platform-wide trends — may or may not overlap with their interests
4. Scrolling reveals: Your Topics, Expiring Opportunities, Companies Moving, Platform
   Overview, Recommended Actions
5. **Aha moment:** "Company X +15 filing surge" card → click to company profile → see
   recent patents → pattern emerges
6. **Friction:** Must manually check Expiry Radar for energy storage if Today doesn't
   surface it. No cross-linking between sections.

**Ideal journey:**
1. Today loads. Top section: "Since your last visit (Tuesday):"
2. Card 1: "Tesla filed 7 new patents in battery thermal management" (followed company)
3. Card 2: "22 high-value patents expiring in energy storage within 90 days" (followed topic)
4. Card 3: "Solid-state electrolyte filings up 2.3x vs 4-week average" (topic trend)
5. Each card: [Save] [See all patents] [Add to watchlist]
6. Scroll down: "Your Watchlist — 3 patents changed status this week"
7. **Return trigger:** "Get weekly briefing on battery + energy storage" → subscribe.

### Journey 3: Engineer/Researcher Deep Patent Review

**Entry point:** From search results or Today insight → patent detail

**Motivation:** "I found a patent that looks relevant. Is it expired? What do the claims
actually cover? Are there similar patents? Has anyone cited it recently?"

**Current flow:**
1. Arrives at patent detail page
2. Sees Executive Summary (title, assignee, dates, scores, actions)
3. Sees Data Completeness (collapsed by default) — may not expand
4. Sees 6 tabs
5. Overview tab: Inventors, AI Summary, Tags, Abstract — good but no claims or expiry
   without switching tabs
6. **Aha moment:** Commercial tab → "Why Now" narrative explains commercial context.
   Usage Signals show where the idea appears in newer patents.
7. **Friction:** Claims are on a separate tab and are just raw text. Legal/Expiry is on
   another tab. Citations on another. To understand "what does this cover, is it expired,
   and has anyone built on it?" requires 3-4 tab switches.

**Ideal journey:**
1. Arrives at patent detail. Above fold (no scroll): title, assignee, **expiry badge**
   (expired_estimated / expiring_soon with confidence), opportunity score, **1-line
   plain-English summary** of what the patent covers.
2. Second section: "What this patent covers" — claims distilled to 3-5 bullet points
   in plain English (not raw claims text). "View full claims" link.
3. Third section: Legal & Expiry card — expiry date, confidence, active family risk,
   maintenance status. "Verify at USPTO" link.
4. Fourth section: Commercial context — usage signals, newer citations, why it matters.
5. **Action row** at every scroll depth: [Save] [Share] [Compare] [Export]
6. **No tab switching required for the core question.** Tabs for deep drill-down
   (Full Claims, Citation Graph, Similar Patents, AI Narratives).

### Journey 4: Corporate Strategy User

**Entry point:** Companies → find a competitor → company profile

**Motivation:** "What is Apple filing in health sensors? Are they building patent walls
around blood glucose monitoring? What's expiring in our space?"

**Current flow:**
1. Companies page: ranking table. Click an entry.
2. Company profile: name, score, stat cards, Recent Patents list, Technology Focus list
3. **Aha moment:** Expiry Exposure box — "12 active granted patents estimated to expire
   within 5 years" with link to Expiry Radar
4. **Friction:** No trend visualization. No side-by-side competitor comparison. No
   "technology areas they're entering vs exiting" signal.

**Ideal journey:**
1. Company profile: At top — composite score, trend direction (↑ or ↓), three most
   active CPC areas as visual bars.
2. "What they're filing" — mini sparkline of filing volume over 12 months.
3. "Technology focus" — radar or heat map of CPC areas (not just a list).
4. "Expiry exposure" — prominent if above threshold, with link to Expiry Radar filtered
   to this company.
5. "Recent moves" — most notable recent patents with why-they-matter summaries.
6. Actions: [Follow] [Compare with...] [Export CSV].

### Journey 5: Future Community Contributor (V4)

**Entry point:** From patent detail or topic page → public insight card

**Motivation:** "I've done research on this expired battery patent. I can add context
about why it matters for solid-state manufacturing."

**Ideal journey (speculative — for V4 readiness):**
1. On patent detail page: "Add insight" button (visible to signed-in users with
   contributor role).
2. Insight creation form: title, body, evidence links, confidence tier, disclosure
   warning.
3. Disclosure warning: "Do not share confidential invention details, trade secrets,
   or unpublished patent ideas. Your insight will be public."
4. Published insight appears on: patent detail page (Community Insights section),
   public share page, topic feed, contributor profile.
5. Other users see: insight card with contributor name, reputation badge, evidence
   links, "Report" link, "Helpful" feedback.
6. Author sees: view count, helpful count, reputation delta.

---

## Part 4 — Information Architecture Proposal

### Current IA

```
TopNav: Today | Patents | Expiry | Opportunities | Trends | Topics | Companies
Sidebar: Today | Search | Companies | Expiry Radar | Watchlist | All Patents |
         Opportunities | Trends | Topics
         ---
         Admin: AI Runs
         ---
         Account | Billing | Sign In
```

Problems:
- Two nav systems (TopNav + Sidebar) with overlapping items
- No clear "primary → secondary" hierarchy
- "Patents" and "All Patents" are the same thing
- "Opportunities" is separate from "Expiry Radar" — but heavily overlap
- "Watchlist" feels secondary but is a core engagement surface
- No Account in TopNav (only in sidebar)
- Admin section mixed with user nav

### Proposed IA

**Primary Navigation (TopNav — 5 items max):**

```
[Brand]  Today  Search  Explore ▼  Workspace ▼                  [🔍] [⚙] [👤]
```

- **Today** — home, briefing, personalized feed
- **Search** — patent search with autocomplete
- **Explore** (dropdown) — Companies, Expiry Radar, Trends, Topics/Themes
- **Workspace** (dropdown) — Watchlist, Saved Searches, Subscriptions
- **Search icon, Settings icon, Account dropdown** — right-aligned

**Secondary Navigation — Explore dropdown:**

```
Explore ▼
├── Companies / Assignees
├── Expiry Radar
├── Trends
├── Opportunities
├── Topics
├── Patent Figures Browser (Sprint 4.5+)
└── Data Health / Source Status
```

**Secondary Navigation — Workspace dropdown:**

```
Workspace ▼
├── Watchlist (saved patents)
├── Followed Companies
├── Saved Searches
├── Subscriptions & Alerts
└── Export Data
```

**Footer / Status Bar (always visible, subtle):**

```
Freshness: Patents updated 2h ago · 64,231 records · USPTO · EPO · WIPO
```

**Sidebar:** Retire the sidebar entirely. The TopNav + dropdown pattern scales better
to V4 community surfaces and works on mobile.

**V4 Surfaces in Navigation:**

When community features launch, add a top-level "Community" nav item (or integrate
into Explore/Workspace). Do NOT add it until the surfaces exist.

```
Community ▼ (V4)
├── Public Insights
├── Discussions
├── Topic Communities
├── Contributors
└── Your Profile
```

**Page Hierarchy:**

```
Level 1 (Primary)
  /today          — Home / Briefing
  /search         — Patent search

Level 2 (Core Intelligence)
  /patents/[id]   — Patent detail
  /companies      — Company index
  /companies/[name] — Company profile
  /expiry         — Expiry Radar
  /trends         — Trend intelligence
  /trends/[surface]/[key] — Trend drilldown
  /topics         — Topic management
  /topics/[id]    — Topic detail

Level 3 (Workspace)
  /workspace/watchlist    — Saved patents
  /workspace/companies    — Followed companies
  /workspace/searches     — Saved searches
  /workspace/alerts       — Subscriptions & alerts

Level 4 (Account)
  /account         — Profile & settings
  /account/billing — Billing
  /account/preferences — Preferences

Level 5 (V4 — Future)
  /insights/[id]         — Public insight card
  /share/[type]/[id]     — Public share page
  /community/topics/[id] — Topic community
  /profiles/[username]   — Public profile
  /discussions/[id]      — Object-specific discussion
```

### What Moves Where

| Current URL | Proposed URL | Rationale |
|-------------|-------------|-----------|
| `/watchlist` | `/workspace/watchlist` | Group under unified workspace |
| `/themes` | `/topics` | Consistent naming (label already says "Topics") |
| `/themes/[id]` | `/topics/[id]` | Same |
| `/account` | `/account` | Keep, restructure |
| `/account/billing` | `/account/billing` | Keep |
| `/account/preferences` | `/account/preferences` | Keep |
| `/opportunity` | Remove (merge into Expiry or Search) | 8-tab opportunity page is a search filter, not a distinct product surface. Merge opportunity scoring into Expiry Radar (for expiry-opportunity) and Search (for general opportunity ranking). |
| `/patents` (list) | Remove (redirect to /search) | "All Patents" without a query is an unbounded list. Search with empty query is more useful. |
| `/onboarding` | Keep at /onboarding | Keep as standalone flow |
| `/admin/ai-runs` | `/admin` (expand) | Group all admin under /admin |
| `/admin/data-health` | `/admin/data-health` | Keep |

---

## Part 5 — Visual Design Direction

### Direction A: "Terminal Intelligence" (Recommended)

**Design philosophy:** Data-dense, high-signal, typographic-first. Black backgrounds,
single accent color, monospace for data, sans-serif for prose. Like Bloomberg Terminal
meets Linear — serious, fast, precise.

**Mood:** "I am looking at live intelligence, not a marketing dashboard."

**Layout style:** 2-column asymmetric (main content 65-70%, sidebar 30-35%). Cards with
sharp corners (6px radius). Tight spacing. No glassmorphism.

**Typography direction:** Geist (already in use) for body/prose. Geist Mono for doc_ids,
dates, codes. Tabular numbers everywhere. Single weight scale: Regular (400), Medium (500),
Semibold (600).

**Color logic:**
- Base: `#08090D` (near-black, not pure black — prevents eye strain)
- Surface: `#111318` — subtle step, not a different color
- Elevated: `#161920` — for cards and panels
- Text primary: `#E2E6ED` — slightly warmer than current
- Text secondary: `#9AA0AE`
- Text muted: `#6B7280`
- Accent: `#5B8AF7` — slightly more vivid blue than current `#6B8CFF`, better contrast
  on dark
- Score high: `#10B981` (green — already correct)
- Score medium/warning: `#F59E0B` (amber — already correct)
- Expiry danger: `#EF4444` (red — already correct)
- Borders: `rgba(255,255,255,0.06)` — even more subtle than current `0.10`

**Density level:** High. Cards show 5-7 data points. Lists show 15-25 items per viewport.
Use compact spacing (py-2, not py-4). This is a professional tool — not a consumer app.

**Motion/interaction style:** Minimal. No page transitions. Subtle hover states
(border-color change, 0.5% background lighten). Fast 150ms transitions. No parallax,
no scroll-jacking, no entrance animations (Reveal component should be retired from app
pages — fine for marketing).

**Why it fits:** II8 is an intelligence tool for professionals. The aesthetic should
communicate precision, data density, and trust — not trend-chasing. Dark-by-default
matches the existing codebase and the "serious research tool" positioning.

---

### Direction B: "Research Canvas"

**Design philosophy:** Spacious, card-based, visual hierarchy through whitespace. Like
Notion meets Perplexity — readable, scannable, accessible. Good for mobile and tablet.

**Mood:** "I can spend time here and not feel overwhelmed."

**Layout style:** Single-column, centered (max-width: 960px). Cards with generous padding
(24px). Clear section breaks. White space as a design element.

**Typography:** Larger body text (15px base vs current 14px). More line-height (1.7 vs
current ~1.5). Clear heading hierarchy (h1: 28px, h2: 20px, h3: 16px).

**Color logic:** Lighter dark mode (`#15191F` base). More contrast between surfaces.
Border radius: 12-16px. Softer shadow (0 2px 8px).

**Density level:** Low-medium. Cards show 3-4 data points. Lists show 8-12 items per
viewport.

**Why it fits:** Better for mobile-first, better for users who are intimidated by
data-dense interfaces. But reduces information density, which is critical for the
core investor/analyst use case.

**Trade-off:** Less information per screen = more scrolling. Works against the "10-second
scan" UX principle. Better suited for a consumer-facing version of II8, not the
professional core.

---

### Direction C: "Precision Industrial" (Alternative)

**Design philosophy:** Technical, structured, grid-based. Like an engineering workstation
or scientific instrument interface. Tabular data, fixed-width columns, precision
typography. Reference: Bloomberg Terminal, VS Code, TablePlus.

**Mood:** "This is a precision instrument for patent analysis."

**Layout style:** Multi-column dashboard (3-4 columns on 1440px+). Grid-snapped layout.
Monospace for all data elements. Sans-serif only for narrative text.

**Typography:** Geist Mono as primary typeface. Geist Sans only for headings and
narrative. 13px base size. Tight leading (1.3).

**Color logic:** Same dark base as Direction A, but borders are more visible
(`rgba(255,255,255,0.12)`) to emphasize grid structure. Column dividers.

**Density level:** Maximum. Every pixel is used. This is for the user who wants to see
50 patents at once.

**Why it fits:** The ultimate professional tool. But the learning curve is high. Better
as a "Pro" layout toggle than the default.

**Trade-off:** Alienates casual users entirely. No onboarding ramp. Forces a specific
mental model that founders and investors may reject.

---

### Recommendation

**Direction A: "Terminal Intelligence"** is the recommended baseline. It balances data
density with readability, matches the existing codebase direction, and communicates
professional seriousness.

**Direction C** can be a future "Compact Mode" toggle for Pro users.

**Direction B** should influence the marketing site and onboarding flow, not the
core product.

---

## Part 6 — Recommended Design System

### Typography Scale

```
text-xs:    11px / 1.5    — metadata, timestamps, chip labels
text-sm:    13px / 1.5    — body, list items, card secondary text
text-base:  15px / 1.65   — card titles, section headings (h3)
text-lg:    18px / 1.4    — page section titles (h2)
text-xl:    22px / 1.3    — card group titles, detail h2
text-2xl:   28px / 1.2    — page titles (h1)
text-3xl:   36px / 1.15   — hero (marketing only)
```

Font: Geist Sans (body), Geist Mono (data, codes, dates, IDs)

### Spacing Scale

```
space-1:  4px    — icon gaps, badge internals
space-2:  8px    — item gaps in lists
space-3:  12px   — card padding (compact)
space-4:  16px   — card padding (standard), section item gaps
space-5:  20px   — card padding (relaxed, for detail pages)
space-6:  24px   — section gaps
space-8:  32px   — major section breaks
space-12: 48px   — page-level spacing
```

### Card Hierarchy

1. **Insight Card (signal/opportunity/risk/update):**
   - Type badge + confidence + timestamp → title → summary → why-it-matters → evidence
     → actions
   - Border-left accent color, subtle background

2. **Patent Card (search results, lists):**
   - Patent figure thumbnail (when available) → title → assignee · doc_id → score badge
     → tags → expiry badge → save action
   - Compact: 2-line title truncation, 3 metadata chips

3. **Company Card (rankings, lists):**
   - Company name (linked) → country/entity badges → composite score → patent count →
     tech breadth → expiry risk
   - Table row or compact card

4. **Topic Card (topic lists):**
   - Topic name → description (1 line) → CPC chips → keyword chips → patent count →
     active/inactive badge
   - Selectable state with border accent

5. **Expiry Radar Card:**
   - Patent title → expiry date badge (color-coded by urgency) → confidence label →
     active family risk flag → opportunity score → usage signal count
   - "Verify with official registers" subtle footer on every card. Not a banner — a
     persistent text element.

6. **Community Insight Card (V4):**
   - Author avatar + name + reputation → title → body (truncated) → evidence links →
     helpful count → timestamp
   - Different background treatment to distinguish from system-generated intelligence

### Grid / Layout Rules

- **Today/Feed:** 2-column grid (md+), cards span equal width
- **Search Results:** 2-column (lg: 3-column) grid. First result optionally full-width
  if high relevance.
- **Patent Detail:** Main column 65% + sidebar 35%. Sidebar sticks on scroll.
- **Company Profile:** Main column 65% + sidebar 35%.
- **Company Index:** Full-width table with summary cards above.
- **Expiry Radar:** Full-width sections, 2-column cards within sections.
- **Trends:** Full-width table/list for scanability.
- **Topics:** 3-column grid for topic cards.
- **Workspace:** Full-width list with inline actions.

### States

All states already defined. Standardize:
- **Loading:** Skeleton cards matching target card shape
- **Empty:** Icon + title + explanation + CTA (current pattern, keep)
- **Error:** Icon + title + user-facing message + technical detail (collapsible) + retry
- **Success:** No banner (data is the success state). Optional subtle check for
  actions (saved, followed).
- **Degraded:** FreshnessBanner (current pattern, keep)

### Status & Confidence Indicators

**Expiry Status Badges:**
```
active_estimated    → green pill, "Active (est.)"
expiring_soon       → amber pill, "Expiring ≤90d"
expired_estimated   → gray pill, "Expired (est.)"
lapsed_possible     → orange pill, "Lapsed?"
lapsed_confirmed    → red pill, "Lapsed"
expired_confirmed   → green pill, "Expired ✓"
unknown             → gray pill, "Unknown"
```

**Confidence Badges:**
```
high        → green dot + "High confidence"
medium      → amber dot + "Medium confidence"
low         → gray dot + "Low confidence"
confirmed   → green dot + "Confirmed"
estimated   → gray dot + "Estimated"
```

**Evidence Tier Badges (for usage signals):**
```
strong  → green, "Strong evidence"
medium  → amber, "Medium evidence"
weak    → gray, "Weak evidence"
```

**Data Freshness Indicators:**
```
Current     → subtle green dot + "Updated 2h ago"
Stale (7d+) → amber dot + "Data 8d old"
Degraded    → red dot + "Sources unavailable"
```

All freshness/confidence indicators render as:
- Compact: colored dot (8px) + label
- Expanded: colored pill with icon + label + detail text

### Card Structure Templates

**Insight Card (Today):**
```
┌──────────────────────────────────────────────┐
│ [Signal] [Medium confidence]    2h ago       │
│                                              │
│ G06N filing activity trending up             │
│ 142 patents in last 4 weeks with z-score 5.2 │
│                                              │
│ Why it matters: Above-average filing may     │
│ signal competitive R&D investment.           │
│                                              │
│ Evidence: 4-week count: 142 · Z-score: 5.2   │
│                                              │
│ [View trend detail →]  [Explore trends]       │
└──────────────────────────────────────────────┘
```

**Patent Card (Search/List):**
```
┌──────────────────────────────────────────────┐
│ [FIGURE]  Biodegradable implant with         │
│           controlled drug release...         │
│                                              │
│ Medtronic · US12345678 · GRANTED              │
│ [CPC: A61K] [CPC: A61M]                      │
│                                              │
│ Est. expiry 2028-03-15  [Opp: 82] [📑]       │
│ ──────────────────────────────────────────── │
│ Source: USPTO · Verify at source              │
└──────────────────────────────────────────────┘
```

### Button Hierarchy

```
Primary:    bg-[var(--accent)] text-white           — save, follow, create
Secondary:  border text-[var(--accent)]              — view, explore, see all
Tertiary:   text-[var(--text-muted)] hover:text-     — dismiss, cancel, hide
Ghost:      text-[var(--text-muted)]/50             — very low priority
Danger:     bg-[var(--expiry-lapsed-confirmed)]     — delete, remove
```

### Badge/Tag System

Consolidate current badges into consistent system:
- **Status badges:** colored pills (expiry status, legal status)
- **Confidence badges:** colored dots with labels
- **Tag chips:** neutral pills for CPC codes, keywords, categories
- **Score badges:** numeric with color gradient (green > amber > gray)
- **Risk flags:** red/amber pills with warning icon
- **Enrichment badges:** gray "Enrichment pending" or green "Verified" with source

---

## Part 7 — Key Screen Redesign Briefs

### 1. Today / Briefing

**User goal:** In 30 seconds, understand what changed since last visit and what to
investigate next.

**Primary content (above fold):**
- "Since your last visit (Tuesday):" header with comparison window
- 3-6 personalized insight cards, ranked by relevance × recency
- Each card: type badge, confidence, title, 1-line why-it-matters, primary action

**Secondary content (below fold):**
- "Your Watchlist" — if saved patents have status changes, show them
- "Trending in your topics" — top 3 topics with new activity
- "Companies you follow" — recent filing activity

**Key actions:**
- Save patent, follow company, create topic — inline on each card
- Mark insight useful/not useful
- Open full Expiry Radar / Trends / Company profile

**Trust/caveat requirements:**
- Freshness indicator always visible
- "Estimated" labels on all expiry data
- AI-generated content labeled
- Source attribution on every patent reference

**Layout:**
- Full-width, single column for feed narrative
- Cards stack vertically, not grid (more scannable for chronological feed)
- Group by relevance tier: "For You" → "Your Topics" → "Platform Signals"

**Mobile:** Single column, larger touch targets, collapsible sections

**Implementation notes:**
- Consolidate the duplicated "For You" sections — use only the V3.2 ForYouCard component
- Remove the InsightCard-based personalized/general split on Today
- The InsightCard component stays for other contexts (admin, alerts)
- Lower Platform Overview to a collapsible section at bottom
- Remove Recommended Actions as a panel — bake actions into empty states and individual
  cards

---

### 2. Patent Detail

**User goal:** Understand what a patent covers, whether it's expired, and what commercial
context exists — without tab-switching for the core questions.

**Primary content (above fold — no scroll):**
```
┌─────────────────────────────────────────────────────┐
│ ← Back to results                                   │
│                                                     │
│ [Patent Figure]  Biodegradable Implant with         │
│                  Controlled Drug Release Mechanism  │
│                                                     │
│ Medtronic  ·  GRANTED  ·  Expired (est.)  ·  Low    │
│ [Opp: 82]                                           │
│                                                     │
│ Filmed: 2018-06  ·  Granted: 2020-03  ·  Pub: US... │
│                                                     │
│ What it covers: A biodegradable polymer matrix that │
│ releases therapeutic agents at a controlled rate... │
│ (1-line AI summary)                                 │
│                                                     │
│ [Save]  [Share]  [Export]  [⚑ Follow company]       │
│─────────────────────────────────────────────────────│
│ ⚠ Expiry is estimated. Active family members in     │
│   EP, JP. Verify with USPTO before acting.          │
└─────────────────────────────────────────────────────┘
```

**Secondary content (scroll):**
- **Claims (Plain English):** 3-5 bullet points distilling key claims. "View full claims" →
  expands raw text.
- **Commercial Signals:** Usage evidence cards with tier badges and source links.
- **Legal & Expiry Card:** Expiry date, confidence, maintenance status, family risk.
- **Citations:** Forward citation count + velocity. "Cited by 12 newer patents."
  Expandable list.
- **Similar Patents:** Horizontal scroll of related patent cards.
- **AI Panels:** Collapsed by default. "Why Now," "Opportunity Narrative,"
  "Trend Snapshot" — each expandable.

**Key actions (persistent):**
- Save/unsave (watchlist toggle)
- Share (copy link)
- Follow company
- Add to topic
- Generate report (export)

**Trust/caveat requirements:**
- Expiry status confidence always visible next to date
- Active family risk warning prominent (not buried in a tab)
- "Verify with official registers" on every expiry display
- AI-generated content labeled with confidence
- Data completeness indicator (subtle, footer-level)

**Layout:**
- Single column, max-width 960px for readability
- Sticky action bar at top (or bottom on mobile)
- Progressive disclosure: summary → claims → signals → citations → similar → AI deep-dive
- NO tabs for primary content. Tabs only for deep-dive alternates (Claims full text vs
  Claims summary, Citation list vs Citation graph).

**Mobile:** Stack vertically. Action bar fixed to bottom. Expandable sections instead of
tabs.

---

### 3. Search Results

**User goal:** Find relevant patents by technology description or keywords, understand
result quality, and take action (save, compare, investigate).

**Primary content:**
- Search bar (persistent at top, prefilled with current query)
- Mode selector: integrated into search bar as a dropdown or segmented control, not
  separate pills
- Result count + active filters as chips
- Patent cards in 2-3 column grid
- Pagination

**Secondary content:**
- Search suggestions (if empty or low results)
- "Save this search" prompt (inline, not hidden below results)
- Related searches / CPC suggestions

**Key actions:**
- Save/unsave from card
- Open in new tab
- Refine search (mode switch, filter add)
- Save search query

**Trust/caveat:**
- Relevance mode indicator: "Ranked by semantic similarity" vs "Keyword match"
- Result quality: if all results are low relevance, show a message

**Layout:**
- Full-width search bar
- Filter row below
- Results grid
- Pagination

**Mobile:** Single column cards, search bar full-width, filters in expandable panel.

---

### 4. Company Intelligence

**User goal:** Understand a company's patent portfolio — strength, focus areas, movement
direction, and expiry exposure.

**Company Index:**
- Summary stats row (total companies, total patents, top country, top entity type)
- Company table: Name · Country · Entity · Score · Patents · Active · Tech Breadth ·
  Expiry Risk
- Filters: country, entity type, min score, sort
- Sortable columns

**Company Profile (redesign):**
- Hero: Company name, composite score, trend direction indicator, country/entity badges
- Stat cards: Total Patents, Active Grants, Expiring Soon, Tech Areas
- Filing trend chart (sparkline or mini bar chart of 12-month filing volume)
- Technology Focus: horizontal bar chart of top CPC areas
- Expiry Exposure: prominent card with count + link to Expiry Radar filtered to company
- Recent Notable Patents: patent cards with why-they-matter summaries
- Top Inventors list
- Actions: [Follow] [Export CSV] [Add to Watchlist]

**Trust/caveat:**
- Enrichment pending — clearly displayed when country/entity type not verified
- "Data derived from patent assignee records. Company names may vary from legal entity
  names."

---

### 5. Expiry Radar

**User goal:** Quickly identify expiring patents that matter, understand confidence and
risk, and prioritize investigation.

**Primary content (reorganized):**
1. **Priority: Expiring Soon (0-90 days)** — highest visual weight. Urgent.
2. **Recently Expired (90 days)** — what just became available.
3. **High-Opportunity Expirations** — scored, prioritized.
4. **Patent Cliffs** — technology areas with clustered expirations.
5. **Needs Verification** — active family risk or low confidence (caution).
6. **Archive: Likely Lapsed / Revival Candidates** — secondary, collapsible.

**Horizon control:**
- Segmented control at top: [Expired] [0-6mo] [6-12mo] [12-24mo] [24-36mo] [All]
- Removes the duplicate filter dropdown. Single control.
- Stats below: "Showing 847 patents expiring within 6 months"

**Filters (collapsible panel, not always visible):**
- Status: Expiring Soon / Expired (est.) / Expired (conf.) / Lapsed (poss.) / Lapsed
  (conf.) / Active (est.) / Unknown
- Confidence: Confirmed / High / Medium / Low
- Family risk: checkbox
- Score threshold: slider or input
- Sort: Expiring soonest / Highest opportunity / Highest confidence / Recently assessed

**Card design:**
- Title + assignee
- Expiry date with color-coded urgency badge
- Confidence badge
- Active family risk flag (red if present, absent if not)
- Opportunity score badge
- Usage signal count (if > 0)
- [Save to watchlist] [View patent] [Verify at USPTO →]

**Caveat banner:** Persistent at top of every section:
"Expiry dates are estimates. Verify with official registers before any commercial decision."

**Empty states:** Current empty states are excellent — keep them. They explain legal
uncertainty honestly.

---

### 6. Watchlist (→ Workspace)

**User goal:** Monitor saved patents, followed companies, and saved searches.
See what changed since last visit.

**Redesign concept:** "Your Workspace" becomes a delta-first monitoring surface.

**Saved Patents tab:**
- Sort by: Recently saved / Recently changed / Expiring soonest / Highest opportunity
- **Change indicators:** If a saved patent's expiry status changed, show "Status changed:
  Expiring Soon → Expired (est.)" with date
- **Bulk actions:** Export selected as CSV, remove selected
- **Add to collection:** Group saved patents into named collections (V4+)

**Followed Companies tab:**
- Company cards with: name, score, "3 new patents this week" if applicable
- **Change indicators:** "New filings detected" / "Score changed"

**Saved Searches tab:**
- Query cards with: name, query preview, "Run search" link, "New results" count if
  applicable

**Layout:** Full-width list with inline actions. Three tabs at top.

---

### 7. Topic Page

**User goal:** Understand a technology area's patent landscape — recent activity, trends,
expiry opportunities, and configure alerts.

**Topic Detail (redesign from bare themes/[id] page):**
```
┌──────────────────────────────────────────────────────┐
│ ← All Topics                                         │
│                                                      │
│ Semiconductor Packaging                              │
│ Advanced packaging techniques for integrated circuits │
│                                                      │
│ [CPC: H01L] [CPC: H05K]  Keywords: TSV, interposer   │
│ Min score: 50                                         │
│                                                      │
│ [Edit]  [Configure Alerts]  [Export Matches]          │
│──────────────────────────────────────────────────────│
│ Stats: 847 patents matched · 23 new this week         │
│                                                      │
│ [Recent Activity] [Trends] [Expiry] [Alerts]          │
│──────────────────────────────────────────────────────│
│ [Recent patent cards...]                              │
└──────────────────────────────────────────────────────┘
```

**Sub-tabs:**
- Recent Activity: newest matching patents (current behavior)
- Trends: filing trend sparkline for this topic's CPC/assignee pattern
- Expiry: matching patents with expiry dates, sorted by urgency
- Alerts: subscription management (frequency, delivery method, score threshold)

**Layout:** Two-column. Main: topic info + patent feed. Sidebar: stats, trend sparkline,
alert config.

---

### 8-10. V4 Surfaces (Future — Brief Only)

These are speculative and will need dedicated design sprints in V4.

**8. Public Insight Card (V4.1):**
- Author: name, avatar, reputation tier
- Content: title, body (markdown), evidence links
- Object context: "Insight on Patent US12345678" with link
- Actions: [Helpful ↑] [Report] [Share]
- Disclosure: "This is a community contribution. Not verified by II8."

**9. Profile Page (V4.2):**
- User identity, bio, reputation score/badge
- Activity feed: published insights, comments, followed topics
- Contributions: list of public insights with helpful counts
- Stats: insights count, helpful marks received, topics contributed to

**10. Discussion Surface (V4.3):**
- Threaded comments on patent/topic/insight objects
- Author identity + reputation on each comment
- Source/evidence linking in comments
- Moderation controls: report, flag, hide
- "Expert note" badge for verified contributors

---

## Part 8 — V4 Readiness

### How the Redesign Prepares for Community Features

1. **Object IDs everywhere.** Every patent card, company card, topic card, and insight
   card has a stable URL and an internal object reference. The community layer attaches
   discussions and insights to these objects. Current code already has this.

2. **Card as primary unit.** V4 public insight cards and community discussions inherit
   from the same card design system. The "Insight Card" component already has type,
   confidence, evidence, and action patterns. Add an `author` prop and it's a community
   card.

3. **Profile/identity anchor.** The current Account page needs a `/profiles/[username]`
   public view. The redesign shouldn't build the community profile yet, but should
   reserve the URL space and the component pattern.

4. **Actions as extensible slots.** The action row pattern (Save, Share, Follow, Compare)
   is already in use. V4 adds "Discuss" and "Add Insight" as additional action slots.
   No redesign needed — just append.

5. **Public/private boundary.** The redesign must establish a clear visual distinction
   between private workspace surfaces and public community surfaces. Different background
   treatment, different URL prefix (`/workspace/` vs `/community/`), clear labeling.

6. **Disclosure warnings.** Before any user publishes anything (insight, comment, profile
   detail), the UI must warn: "Do not share confidential invention details, trade secrets,
   unpublished patent applications, or privileged legal information. Your contribution
   will be public."

7. **Source health dashboard.** When community features launch, users and moderators need
   to see source freshness, data completeness, and ingestion status. The FreshnessBanner
   component should be extendable to a full `/admin/data-health` dashboard.

8. **Reputation primitives.** The design system should define reputation badge variants
   (Contributor, Expert, Moderator) now — even if they're not rendered anywhere yet.
   This prevents a rush of ad-hoc badge styles later.

### What NOT to Build Yet

- Community posting, profiles, discussions, or public share pages
- Reputation/scoring systems
- Moderation queues
- Expert verification workflows
- Community analytics

These are V4 implementation. The redesign should only ensure the IA, URL structure,
component patterns, and design tokens can accommodate them.

---

## Part 9 — UX Risk Audit

### 1. Legal/Trust Risk

**Risk:** Users misinterpret estimated expiry as confirmed. They make business decisions
based on incomplete or stale data.

**Mitigation:**
- Every expiry display shows confidence label
- Active family risk always visible, not buried in a tab
- Persistent "Verify with official registers" language on every expiry surface
- Never use "free to use" or "public domain" language
- Expiry data older than 7 days triggers a freshness warning
- Degraded source status triggers a prominent banner

### 2. Confidential Disclosure Risk

**Risk:** Founders/inventors type confidential invention details into the search bar,
topic creation, or future community posts, believing the system is private.

**Mitigation:**
- Onboarding should include explicit warning: "Your interests are private. Never share
  confidential invention details, trade secrets, or unpublished patent ideas in search,
  topics, or public surfaces."
- Public community surfaces must have a pre-post disclosure warning
- Search queries should never be displayed publicly or in URLs without user intent
- Saved searches are private by default

### 3. Overclaiming AI Accuracy

**Risk:** AI-generated narratives ("Why it matters," "Commercial significance") are
presented as factual analysis, not AI-generated interpretation.

**Mitigation:**
- All AI-generated content labeled "AI-generated" with confidence level
- AI panels collapsed by default; user explicitly generates or expands
- Source citations included with every AI narrative
- Data Completeness panel shows which fields are real vs generated

### 4. Clutter / Cognitive Overload

**Risk:** 7 sections on Today, 6 tabs on Patent Detail, 8 tabs on Opportunity, 7 sections
on Expiry. Users can't find signal in the noise.

**Mitigation:**
- Prioritize sections by user value, not data availability
- Collapse secondary sections
- Remove redundant surfaces (duplicate "For You" on Today, "Opportunity" as separate page)
- Progressive disclosure: summary first, detail on demand
- Card design reduces to essential data points

### 5. Stale Data Confusion

**Risk:** Users don't realize they're looking at data that hasn't been updated in weeks.
They make strategy decisions based on outdated intelligence.

**Mitigation:**
- Persistent freshness indicator (not just on-error banner)
- "Last updated" timestamp on every data-heavy page
- Stale data warning at 7+ days
- Degraded source banner when APIs are unavailable

### 6. Social Noise (V4 risk)

**Risk:** Low-quality community posts dilute the product's intelligence credibility.
"Patent bro" culture produces speculative, ungrounded commentary.

**Mitigation:**
- Evidence requirements: community insights must link to sources
- Reputation system: low-reputation contributors have limited visibility
- Moderation: report, flag, hide, and expert-review workflows
- Clear separation between system intelligence (algorithmic) and community intelligence
  (human-contributed)
- Expert/verified contributor tier with higher standards

### 7. Low-Quality Community Posts (V4 risk)

**Risk:** Posts like "This patent is garbage, I filed something better in 2019" with
no evidence, or AI-generated spam commentary.

**Mitigation:** Same as Social Noise above plus: minimum character count, evidence link
requirement, rate limiting, and AI-content detection on community posts.

### 8. Unclear Value Proposition

**Risk:** A first-time user (especially founder/inventor) lands on Today and sees generic
stats — doesn't understand what the product does or why it's useful.

**Mitigation:**
- First-time Today experience should immediately answer a question: "Based on your
  interests in [onboarding topics], here are 3 patents you should know about."
- Onboarding should be shorter (3 steps, not 5) — role, interests, done
- Marketing site should show realistic product screenshots, not just value prop cards

### 9. Weak Onboarding

**Risk:** 5-step onboarding asks for role, use_case, industry, interests, and confirm —
too many steps. Users drop off.

**Mitigation:**
- Reduce to 3 steps: role, industry, interests
- Show suggested companies and themes inline (not on a separate confirm page)
- Add the privacy/confidentiality warning on step 1
- Allow skipping — users can fill in preferences later from Account

### 10. Unconvincing Premium Feel

**Risk:** The dark theme with steel-blue accent looks functional but doesn't communicate
"premium research workspace." It could be mistaken for an open-source admin panel.

**Mitigation:**
- Improved typography hierarchy with Geist
- Subtle surface differentiation (base vs elevated vs card)
- Motion reserved for meaningful interactions (hover states, expand transitions), not
  decoration
- No generic AI dashboard tropes (glassmorphism cards, gradient buttons, purple/blue
  rainbow themes)
- White space used intentionally, not wasted
- Monospace for data, proportional for prose — creates visual texture

---

## Part 10 — Implementation Roadmap

### Phase A: UX Audit & Information Architecture (1-2 days)

**Scope:**
- Review this document with product owner
- Finalize IA decisions (what moves, what's removed, what's renamed)
- Create URL redirect map for any route changes
- Agree on naming conventions (Topics vs Themes, Watchlist vs Workspace)

**Files affected:**
- Route definitions
- Navigation components (TopNav, NavSidebar)
- middleware/auth route lists
- sitemap

**Acceptance criteria:**
- All current routes have a target (keep, move, or merge)
- URL redirects documented
- Nav labels document finalized

**What not to touch:** Backend routes, API endpoints, data models.

---

### Phase B: Design System & Tokens (3-5 days)

**Scope:**
- Update tokens.css with new color values per Direction A
- Update tailwind.config.ts with new design tokens
- Build/update base components: Badge, InsightCard, PatentCard, card template, button
  variants
- Create status/confidence indicator components
- Create disclosure warning component (for future V4 use)
- Update loading/empty/error states to match new design language
- Remove or consolidate duplicate components

**Files affected:**
- `frontend/src/styles/tokens.css`
- `frontend/tailwind.config.ts`
- `frontend/src/app/globals.css`
- `frontend/src/components/ui/Badge.tsx`
- `frontend/src/components/ui/InsightCard.tsx`
- `frontend/src/components/patents/PatentCard.tsx`
- `frontend/src/components/ui/EmptyState.tsx`
- `frontend/src/components/ui/LoadingState.tsx`
- `frontend/src/components/ui/StatusBadge.tsx`
- `frontend/src/components/patents/LegalConfidenceBadge.tsx`
- New: `frontend/src/components/ui/ConfidenceIndicator.tsx`
- New: `frontend/src/components/ui/DisclosureWarning.tsx`

**Acceptance criteria:**
- `make build` passes without errors
- Component storybook or dev page shows all component states
- Dark theme renders correctly
- Light theme renders correctly (basic, not exhaustive)
- No regressions in existing pages (visual comparison)

**What not to touch:** Backend, data models, API, page layouts (in this phase).

---

### Phase C: Today & Core Intelligence Screens (5-7 days)

**Scope:**
- Redesign Today page per brief #1
- Consolidate InsightCard + ForYouCard sections into unified feed
- Remove duplicated "For You" sections
- Collapse Platform Overview into footer-level section
- Remove Recommended Actions panel (bake into empty states)
- Add return-trigger language ("Since your last visit...")
- Restructure page header with freshness indicator

**Files affected:**
- `frontend/src/app/(app)/today/page.tsx`
- `frontend/src/app/(app)/today/layout.tsx`
- `frontend/src/components/today/ForYouCard.tsx`
- `frontend/src/components/ui/InsightCard.tsx`
- `frontend/src/components/ui/PageHeader.tsx`
- `frontend/src/components/ui/FreshnessBanner.tsx`

**Acceptance criteria:**
- Today shows personalized feed as primary content
- "For You" appears once, not twice
- Platform overview is collapsed by default (expandable)
- Freshness indicator visible without scrolling
- First-time experience triggers immediately on empty state
- `make test` passes (update snapshots/tests as needed)

**What not to touch:** Search, Patent Detail, Companies, Expiry, Watchlist.

---

### Phase D: Patent Detail & Search Overhaul (5-7 days)

**Scope:**
- Redesign Patent Detail per brief #2
- Move expiry/legal info above the fold (not in a tab)
- Collapse AI panels by default (expandable, not behind tab)
- Claims: add plain-English summary, raw text expandable
- Redesign Search results per brief #3
- Improve mode selector integration
- Add saved search prompt inline with results (not hidden in empty state)

**Files affected:**
- `frontend/src/app/(app)/patents/[id]/page.tsx`
- `frontend/src/components/patents/PatentDetailTabs.tsx`
- `frontend/src/components/patents/AISummaryPanel.tsx`
- `frontend/src/components/patents/ClaimsPanel.tsx`
- `frontend/src/components/patents/WhyNowPanel.tsx`
- `frontend/src/components/patents/UsageSignalsPanel.tsx`
- `frontend/src/components/patents/ExternalPatentLinks.tsx`
- `frontend/src/app/(app)/search/page.tsx`
- `frontend/src/components/patents/PatentCard.tsx`

**Acceptance criteria:**
- Patent detail shows expiry, confidence, and 1-line summary above fold
- AI panels are collapsed by default, expand on click
- Claims panel shows plain-English bullets + raw text toggle
- Search bar shows mode selector inline
- All existing data fields still accessible
- `make test` passes

**What not to touch:** Companies, Expiry, Watchlist, Topics.

---

### Phase E: Company / Expiry / Watchlist Polish (5-7 days)

**Scope:**
- Redesign Company Index + Profile per brief #4
- Redesign Expiry Radar per brief #5
- Redesign Watchlist → Workspace per brief #6
- Add "change since saved" indicators on watchlist items
- Consolidate horizon controls on Expiry Radar
- Add trend sparklines to Company Profile (if data available)

**Files affected:**
- `frontend/src/app/(app)/companies/page.tsx`
- `frontend/src/app/(app)/companies/[name]/page.tsx`
- `frontend/src/app/(app)/expiry/page.tsx`
- `frontend/src/components/expiry/ExpiryRadarSection.tsx`
- `frontend/src/components/expiry/ExpiryRadarCard.tsx`
- `frontend/src/components/expiry/ExpirySummaryCards.tsx`
- `frontend/src/app/(app)/watchlist/page.tsx` (potentially moved to `/workspace/watchlist`)

**Acceptance criteria:**
- Company profile shows filing trend visualization
- Expiry Radar sections prioritized by urgency
- Horizon control unified (single control, not tab + dropdown)
- Watchlist shows status deltas where available
- `make test` passes

**What not to touch:** Patent Detail, Search, Today, Topics.

---

### Phase F: Topics & Account (3-5 days)

**Scope:**
- Redesign Topics per brief #7
- Rename /themes → /topics (or keep route, change label)
- Add topic detail page with intelligence (trends, expiry, alerts)
- Restructure Account page (separate Identity, Billing, Subscriptions)
- Add privacy/confidentiality warning to onboarding
- Reduce onboarding from 5 steps to 3

**Files affected:**
- `frontend/src/app/(app)/themes/page.tsx`
- `frontend/src/app/(app)/themes/[id]/page.tsx`
- `frontend/src/app/(app)/account/page.tsx`
- `frontend/src/app/(app)/onboarding/page.tsx`
- `frontend/src/components/onboarding/StepRole.tsx`
- `frontend/src/components/onboarding/StepUseCase.tsx`
- `frontend/src/components/onboarding/StepIndustry.tsx`
- `frontend/src/components/onboarding/StepInterests.tsx`
- `frontend/src/components/onboarding/StepConfirm.tsx`

**Acceptance criteria:**
- Topic detail page shows intelligence, not just patent list
- Onboarding is 3 steps or fewer
- Privacy/confidentiality warning appears during onboarding
- Account page organized by concern (identity, billing, subscriptions)
- `make test` passes

**What not to touch:** Core intelligence screens completed in Phases C-E.

---

### Phase G: Navigation Consolidation (2-3 days)

**Scope:**
- Implement new IA with TopNav dropdowns per Part 4
- Retire NavSidebar
- Add footer freshness indicator
- Remove /opportunity if approved (redirect to Expiry Radar or Search)
- Remove /patents list page if approved (redirect to Search)
- Add URL redirects for any moved routes
- Update sitemap

**Files affected:**
- `frontend/src/components/nav/TopNav.tsx`
- `frontend/src/app/(app)/NavSidebar.tsx` (remove)
- `frontend/src/app/(app)/layout.tsx`
- `frontend/next.config.*` (redirects)
- `frontend/src/app/sitemap.ts`

**Acceptance criteria:**
- All current URLs either work or redirect correctly
- TopNav has ≤ 7 items (including dropdowns)
- Sidebar is removed
- Footer freshness indicator visible on all app pages
- `make build` passes
- `make test` passes

**What not to touch:** Backend routes, API, page content (other than nav wrapping).

---

### Phase H: Final Polish — Motion, Responsive, Accessibility (3-5 days)

**Scope:**
- Mobile/tablet responsive QA for all screens
- Keyboard navigation audit
- Screen reader audit
- Focus state standardization
- Color contrast verification
- Reduced motion support verification
- Loading state consistency check
- Empty state consistency check
- Remove Reveal animations from app pages (keep on marketing)
- Performance audit (Lighthouse)

**Files affected:** All pages — QA pass, not feature work.

**Acceptance criteria:**
- All pages usable on 375px width
- All interactive elements keyboard-accessible
- Focus rings visible and consistent
- Color contrast meets WCAG AA (at minimum)
- `prefers-reduced-motion` respected
- Lighthouse scores: Performance ≥ 80, Accessibility ≥ 90
- `make build` passes with no warnings
- `make test` passes

**What not to touch:** Feature code. Bug fixes only — no new features or redesign in
this phase.

---

## Part 11 — Acceptance Criteria

### What "Great" Means

1. **A user can understand the product in under 30 seconds.**
   - Marketing site clearly states what II8 does
   - Today page immediately shows personalized value
   - Empty states explain what will appear and why

2. **A user can find a useful insight in under 2 minutes.**
   - Search delivers relevant results for natural language queries
   - Today surfaces at least one actionable insight for returning users
   - Expiry Radar highlights the most urgent items first

3. **Patent detail is readable and trustworthy.**
   - Expiry status and confidence visible without scrolling or tab-switching
   - AI-generated content labeled and collapsible
   - Source attribution on every patent
   - Data completeness transparent

4. **Source degradation is clear but not alarming.**
   - FreshnessBanner uses amber for degraded, not red
   - Red reserved for complete source failure only
   - Clear language about what's affected and what's not
   - "Verify with official registers" consistently present

5. **Screens feel premium and coherent.**
   - Consistent typography, spacing, and color usage
   - Card patterns consistent across surfaces
   - Button hierarchy consistent
   - No visual dead-ends (every screen has a next action)

6. **Visual hierarchy reduces cognitive load.**
   - Primary content visually dominant
   - Secondary content visually subordinate
   - Tertiary content collapsed or deferred
   - Scannable at 10-second, 2-minute, and 20-minute depths

7. **Future V4 community surfaces fit naturally.**
   - URL structure accommodates /community/ and /profiles/
   - Card patterns extend to community content
   - Action patterns extend to community interactions
   - Disclosure warnings have a home in the design system

8. **Technical quality gates pass.**
   - `make build` passes (TypeScript, Next.js)
   - `make lint` passes
   - `make test` passes
   - No hardcoded data
   - No exposed private data
   - No accidental public disclosure paths

---

## Part 12 — Open Questions

These decisions require the product owner's input before implementation begins:

### Product Identity

1. **Product name: "Invention Index 8" vs "Patent Pulse"?**
   The codebase uses both. `BRAND.name` is "Invention Index 8" but the repo is
   "Patent-Pulse." Marketing copy says "Invention Index 8." Which is the permanent
   name? This affects every page title, nav label, and meta tag.

2. **Domain strategy:** inventionindex8.com is the current domain. Is this the final
   consumer-facing domain? Should "Patent Pulse" redirect or be retired?

### Feature Decisions

3. **Should /opportunity be removed/merged?**
   The 8-tab Opportunity page overlaps heavily with Expiry Radar (for
   expiry-opportunity) and Search (for general opportunity ranking). Proposal: merge
   opportunity scoring into those surfaces and remove the standalone page.

4. **Should /patents (unfiltered list) be removed?**
   Browsing 64K+ patents with no query is a data dump. Proposal: redirect /patents
   to /search with empty query showing "Start by searching or describing a technology."

5. **Should watchlist be renamed to "Workspace"?**
   "Watchlist" implies only saved patents. The page already includes followed companies
   and saved searches. "Workspace" is more accurate. But watchlist is a familiar term.

### V4 Community Scope

6. **What is the V4 community launch timeline relative to the UX overhaul?**
   Should the overhaul include community-ready surfaces (even if empty) or should
   community wait until the core experience is redesigned?

7. **Will community features be free or paid?**
   Affects whether community surfaces are gated behind auth/payment.

8. **Is there a target launch for profiles, discussions, and public insight cards?**
   Affects whether URL structure should be reserved now.

### Technical

9. **Next.js App Router compatibility with the proposed IA**
   Route group restructuring (/(app)/ → new layout groups) needs verification against
   current auth middleware and layout nesting.

10. **Backward compatibility for URL changes**
    How long should redirects from old URLs (/themes → /topics, /watchlist →
    /workspace/watchlist) be maintained?

### Design

11. **Should the design system support both "Terminal Intelligence" (Direction A) and
    "Precision Industrial" (Direction C) as a compact/dense mode toggle?**
    If yes, this needs to be designed from the start — retrofit is expensive.

12. **Light mode commitment level?**
    Current light mode is basic (just color value swaps). Full light mode QA is a
    separate effort. Should light mode be a Phase H item or deferred?

---

## Recommended First Implementation Branch

After strategy approval, the first implementation branch should be:

**Branch:** `feature/ux-phase-a-b-design-system`
**Scope:** Phase A (IA audit + decisions) + Phase B (Design system & tokens)
**Deliverable:** Updated design tokens, base components, nav structure decisions
documented and approved — ready for Phase C (Today redesign).

This is a foundation phase with no user-facing page changes. It establishes the visual
language and component patterns that all subsequent phases build on.

---

*End of strategy document. Awaiting product owner review.*
