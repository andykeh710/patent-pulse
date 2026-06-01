# Frontend Overhaul — V1 Design Spec

**Date:** 2026-06-01
**Status:** Brainstorming complete. Design preview approved by Andy on 2026-06-01. Awaiting written-spec review before implementation planning.
**Author:** Brainstorming session — Claude as architect, Andy as product owner
**Implementer:** Hermes (per `hermes-workflow` memory)
**Estimated V1 effort:** 7–9 weeks of Hermes work in phased blocks

---

## 1. Context & motivation

Invention Index 8 (II8) shipped to production on 2026-05-31 at `inventionindex8.com`. The rebrand from Patent Pulse landed, the V1 close-out fixed the high-leverage bugs, and the data layer is healthy enough to support a real product experience: 64,231 patents (USPTO + EPO + WIPO), 32,150 AI summaries, 2,087 tagged, the four Today highlight cards live (filing trend, expiring opportunity, notable patent, company move).

But the visual experience is fractured. The marketing landing page at `/` is fully expressed in the locked dark/premium aesthetic — `bg-[#0a0e27]`, signal orbs with animated drift, glass panels, indigo/violet/cyan accents, scan-hover effects, signal-pulse indicators. The moment a user signs up and arrives at `/today`, they're dropped into a generic light-mode SaaS dashboard with `bg-white`, gray borders, and `bg-blue-100 text-blue-700` chip tags. The same product, two different identities.

The infrastructure to fix this is already in the codebase: `tailwind.config.ts` defines `signal.electric`, `signal.violet`, `signal.cyan`, `signal.glow`, `surface.glass`, `score.high/medium/low`, plus drift, scan-sweep, signal-pulse animations. `globals.css` defines `.glass-panel`, `.gradient-border-hover`, `.scan-hover`, `.signal-pulse`. Only the marketing landing page consumes any of this. The app interior was never pulled up.

This spec covers the V1 overhaul: bring the entire authenticated app to the dark/premium visual identity, add the two highest-leverage personalization features (Persona-based onboarding, Follow Companies), and design hooks for V1.1 (AI "For you", news ↔ patents linking, Follow Inventors) so they slot in without re-architecting.

---

## 2. Locked decisions (from brainstorming, 2026-06-01)

These decisions came out of six clarifying questions during the brainstorming session. Each is a fork the design hangs on; flipping any of them would require re-running the brainstorming.

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Direction of visual unification | **Pull app interior up to marketing aesthetic** | Marketing already premium; tearing it down to match the generic app would lose conversion polish. App interior is the gap to close. |
| 2 | Primary user persona | **Mixed — operator + investor + curious researcher** with persona-based onboarding selector | Pricing tiers ($0/$8/$108/$1000) span prosumer and enterprise. Locking to one persona narrows the market. Persona-based onboarding lets each user tailor without forcing a single voice. |
| 3 | Arrival pattern | **Weekly email + daily in-app feed** | App is a destination, not a tool. Email is the gentle nudge, the app is the regular reading experience. |
| 4 | Today screen structure | **Hybrid C — stats row + briefing feed** | Evolves the existing Today page rather than replacing it. Preserves the stats-at-glance utility while adding the editorial briefing feel. Lowest re-architect cost. |
| 5 | Personalization dimensions | **Topics + Watchlist (exists) + Follow Companies (V1) + Follow Inventors (V1.1) + AI "For You" (V1.1) + Persona-driven defaults** | "Do everything" requested. Phased so V1 ships in 7–9 weeks not 14–18. |
| 6 | Phasing approach | **Phased ambitious** — V1 / V1.1 / V2 | V1 ~7–9 weeks ships a polished foundation. V1.1 ~4–6 weeks layers the AI features. V2 covers power-user tooling. Keeps shipping momentum. |

The "news ↔ patents linking" feature the user raised is a V1.1 build but a V1 design concern — the briefing feed must include a card-type slot designed in now so V1.1 integration is a backend wire-up, not a frontend restructure.

### 2.1 Decision register — consequence-level resolutions

These resolve route-level naming, surface conflicts, and language posture that the 6 locked decisions imply but don't make explicit. Hermes will follow this register without guessing.

| # | Decision | Final choice | Consequence |
|---|---|---|---|
| 1 | `/today` vs `/dashboard` | `/today` is the canonical command center | `/dashboard` already deleted in earlier UX sprint — confirm no references remain in code, emails, Stripe success_url, or docs. Re-add a 307 redirect if any external reference is found in the preflight grep. |
| 2 | `/themes` vs `/topics` naming | UI label is **"Topics"** everywhere; route URL stays `/themes` in V1 | No rename of the route URL in V1 (404 risk on existing topic URLs). V1.1 may add a `/topics` alias with a 308 to `/themes`. Update all UI nav labels + copy. |
| 3 | `/news` standalone route | Not created in V1 | Today briefing feed has a `news` card type slot (V1.1 placeholder). No `/news` page. V1.1 may add `/news` as a dedicated view if the feature warrants it. |
| 4 | AI "For You" — algorithm posture | **Rule-based early personalization** for V1. AI engine is V1.1. | Card label and subtext must NOT claim AI personalization yet. Copy says "early personalization based on your persona, followed companies, and selected topics." No "AI-recommended" language. See §7.3. |
| 5 | Follow Companies — persistence model | Real persisted user follows in `user_company_follows` table | Requires migration, endpoints, frontend `FollowButton`, honest empty states, tests. Not a fake garnish. |
| 6 | Patent detail refactor — approach | **Decompose, not redesign from scratch** | Preserve all existing AI panels (`AISummaryPanel`, `OpportunityBreakdown`, `OpportunityNarrativePanel`, `WhyNowPanel`, `ClaimsPanel`, `RiskFlagsBadge`, etc.) inside the new tab structure. Don't rewrite their internals; reposition and re-skin. |
| 7 | News content honesty | News slot designed in; fake news content forbidden | V1 placeholder card is honest: "V1.1 — news linking slot reserved." V1.1 ships real news linking via a chosen news source with AI-summarized "why this matters." Never fabricate news headlines, sources, or "why this matters" copy. |
| 8 | `/companies/[name]` 500 in dev | **V1 blocker, not a defer** | Follow Companies onboarding points users at this route. A broken company detail page is a product bug, not a polish task. Fixed in Phase B before any Follow Companies UI ships. |
| 9 | Data freshness and caveat visibility | **Trust infrastructure, not polish** | Every data surface shows freshness (last-update timestamp + relative), source attribution, and confidence/caveat where applicable. `FreshnessBanner` and `SourceAttribution` are mandatory on Today, patent detail, expiry, trends. Not optional. |
| 10 | Account/billing scope | Account: **real changes** (add Persona field, dark theme). Billing: **dark theme only, no new UI** | Don't build fake subscription state or new Stripe flows. Existing Stripe wiring stays; just visual refresh of the existing `/account/billing` page. |

---

## 3. Design foundation

### 3.1 Color tokens

Create `frontend/src/styles/tokens.css` with the canonical palette, then import it once in the root layout. Tailwind config keeps the same names so utility classes stay consistent. CSS variables are required for `<svg>`, `<canvas>`, and CSS module contexts that can't access Tailwind.

```css
:root {
  /* Base surfaces */
  --bg-base: #0A0E27;        /* deep navy with blue undertone */
  --bg-elevated: #11162A;    /* one level up — panels, modals */
  --bg-glass: rgba(255, 255, 255, 0.04);
  --bg-glass-strong: rgba(255, 255, 255, 0.06);
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.16);

  /* Text */
  --text-primary: #E8ECF7;
  --text-secondary: #C7D2FE;
  --text-muted: #94A3B8;
  --text-disabled: #64748B;

  /* Signal — for icons, accents, indicators */
  --signal-blue: #6366F1;       /* primary */
  --signal-violet: #8B5CF6;     /* secondary, AI affordances */
  --signal-cyan: #06B6D4;       /* technical / live */
  --signal-glow: #818CF8;       /* hover, focus rings */

  /* Semantic */
  --score-high: #34D399;        /* positive opportunity */
  --score-medium: #F59E0B;      /* caution / warning */
  --score-low: #94A3B8;         /* neutral / muted */
  --warning: #F59E0B;           /* expiring, caveats */

  /* Briefing item-type accents (left-border colors) */
  --type-trend: var(--signal-blue);
  --type-notable: var(--score-high);
  --type-company: #7DD3FC;      /* sky blue */
  --type-expiring: var(--warning);
  --type-foryou: var(--signal-violet);
  --type-news: var(--signal-violet);  /* V1.1 slot */
}
```

### 3.2 Typography

Adopt **Geist Sans + Geist Mono** via `next/font/google`. Geist is Vercel's typeface, free, ships well, geometric without being cold, and Geist Mono has excellent tabular numerics.

Rule: any numeric display gets Geist Mono with `font-variant-numeric: tabular-nums`. This includes:
- Patent numbers (e.g., `US12,345,678`)
- Dates
- Opportunity scores (e.g., `opp 92`)
- Counts, deltas (e.g., `+1,247`, `↑ 12%`)
- Percentages, z-scores, ratios
- Timestamps

Body, headings, labels: Geist Sans. Weights used: 400 (body), 500 (subheads, emphasis), 600 (page titles, section headers, primary CTAs). Weight 700 is reserved for the marketing landing hero only — within the app interior, visual hierarchy comes from size and color, not weight stacks.

Configuration goes in `frontend/src/app/layout.tsx` via `next/font/google` so subsets are correct and CLS is zero.

### 3.3 Motion

Three primitives are already defined in `tailwind.config.ts`:
- `animate-drift-slow` (20s) and `animate-drift-slower` (30s) — used on signal orbs
- `animate-scan-sweep` (4s) — patent card hover sweep
- `animate-shine` (1.5s) — CTA button shine

For V1 add:
- `animate-signal-pulse` (3s, ease-in-out, infinite) — already in config, surface on live indicators
- One-time **first-load reveal** sequence (logo materializes 50ms → grid drops in 200ms → hero text reveals 300ms → counters count up 1200ms). Plays once per session via `sessionStorage` flag. **Landing page only**, not the app interior.
- **Counter component**: `<Counter value={64231} duration={1200} />`. Easing: cubic-bezier(0.16, 1, 0.3, 1). Triggers on first IntersectionObserver entry, not on every re-render. Mono typography, tabular nums.

**`prefers-reduced-motion: reduce` handling (mandatory):**
- Drift animations disable
- Scan-sweep disables
- Signal pulses freeze
- Counters jump to final value
- First-load reveal becomes instant
- Hover states keep simple opacity/border transitions, no movement

### 3.4 Base UI primitives (build first, everything else uses these)

Create these in `frontend/src/components/ui/`:

| Component | File | Purpose |
|---|---|---|
| `Card` | `Card.tsx` | Glass-panel surface. Props: `variant` ("default" \| "glass" \| "elevated"), `interactive` (adds scan-hover). |
| `StatTile` | `StatTile.tsx` | Used in Today stats row. Props: `label`, `value` (Counter-driven), `subtext`, `accent` ("default" \| "signal" \| "warning"). |
| `BriefingItem` | `BriefingItem.tsx` | Feed item wrapper. Props: `type` ("trend" \| "expiring" \| "notable" \| "company" \| "foryou" \| "news"), `label`, `title`, `subtext`, `href`. Renders colored left border by type. |
| `Counter` | `Counter.tsx` | Animated number count-up. See §3.3. |
| `Pill` | `Pill.tsx` | Inline label/chip. Replaces all the ad-hoc `bg-blue-100 text-blue-700` chip code. Props: `variant`, `tone`, `mono` (for numeric pills). |
| `Button` | `Button.tsx` | Refresh existing if present. Variants: `primary` (gradient blue→violet), `secondary` (border + transparent), `ghost`, `danger`. All with focus-visible rings. |
| `Badge` | already exists | Audit for dark-theme readiness; refactor if needed. |
| `LiveIndicator` | `LiveIndicator.tsx` | Pulsing dot + label. States: "Live" (green), "Scanning" (blue), "Updated 2m ago" (muted), "No signal yet" (gray). |
| `EmptyState` | already exists | Audit; ensure brand voice from `COPY` (in `brand.ts`) is used. |
| `Skeleton` | already exists | Audit; ensure dark-theme variant. |
| `SectionHeader` | `SectionHeader.tsx` | Page section heading with optional secondary metadata. |

### 3.5 App shell + nav

Refactor `frontend/src/app/(app)/layout.tsx` to apply the dark base everywhere. Replace any white background. Replace any `border-gray-200` with `border-[var(--border-subtle)]`.

**Nav structure (top bar, persistent):**

```
[II8 logo + 8-pill]   Today  Patents  Expiry  Opportunities  Trends  Topics  Companies   [🔍 search]  [🔔 alerts]  [👤 account ▾]
```

- Logo: `Invention` (Geist Sans 600) + `Index` (Geist Sans 500) + `8` in a rounded pill with `--signal-violet` background and soft glow. Hover triggers a single pulse on the 8 only. Tooltip on the 8: "8 invention signals tracked daily."
- Nav items: 7 top-level — Today / Patents / Expiry / Opportunities / Trends / Topics / Companies. (Per IA decisions from prior brainstorming round.)
- 🔍 icon → `/search` (no inline omnisearch in V1; defer to V2)
- 🔔 alerts indicator — V1 shows count of new items since last visit; V1.1 wires to actual alert rules.
- Account dropdown: Watchlist, Account, Billing, Logout. Admin link if `user.is_staff`.

**Right sidebar on Today only** (not other pages):
- "My Follows" widget (topic chips + company chips, "+ Follow more" link)
- "Quick Actions" widget (3-5 deep-link CTAs)
- "Saved Patents" widget (3 most-recent + "View all N →")

### 3.6 Data freshness and caveat visibility (trust infrastructure)

Data freshness is not polish. It is the trust layer the product is built on. Patent intelligence claims that aren't dated, sourced, or caveated are indistinguishable from speculation. Every data surface in the app must answer four questions implicitly or explicitly:

1. **What am I looking at?** (the data itself)
2. **Where did this come from?** (source attribution)
3. **When was this last updated?** (freshness timestamp + relative)
4. **How confident should I be?** (confidence level + caveat for legal-sensitive surfaces)

**Mandatory components per surface:**

| Surface | Freshness | Source | Confidence/caveat |
|---|---|---|---|
| Today (each briefing item) | per-item freshness via the required `freshness` field (§4.4) | per-item via `source` field (§4.4) | per-item via `confidence` field where applicable |
| Today (top-level) | "Last scan Nm ago" pill in the header `LiveIndicator` | covered per-item | n/a |
| Patent detail | `FreshnessBanner` showing last enrichment date | `SourceAttribution` near each data block (summary, claims, opp score) | `LegalConfidenceBadge` for expiry / legal status |
| Expiry Radar | `FreshnessBanner` near filter bar | `SourceAttribution` near results | **Required caveat**: "Verify with official registers before relying on expiry status" — always visible, not collapsible |
| Trends | last-computed timestamp on each trend card | n/a (computed from indexed data) | momentum confidence label where applicable |
| Companies detail | last-filed timestamp + last-indexed timestamp | per-section | n/a |
| Search results | n/a (live query) | n/a | n/a |

The components `FreshnessBanner`, `SourceAttribution`, `LegalConfidenceBadge`, and `LiveIndicator` already exist in `frontend/src/components/ui/` and `frontend/src/components/patents/`. They are not optional. If a surface displays patent data and does not surface freshness + source + confidence, that surface is incomplete and fails the Phase F gate.

Forbidden: hiding freshness because the data is stale. If a surface has 7-day-old data, show "7 days old" plainly. Honesty about staleness is better than false currency.

---

## 4. Today screen — the killer surface

### 4.1 Layout

Three vertical zones inside a max-width container:

1. **Top header** (~80px) — greeting + day/date + freshness pill (top-right)
2. **Stats row** (~110px) — 4 tiles, equal-width grid
3. **Main grid** — left column (briefing feed) + right sidebar (280px fixed)

Spacing: 24px between zones. Inside the briefing feed, 12px between items. Cards have 14px internal padding.

### 4.2 Top header

```
Monday · June 1, 2026
Good morning, Andy                                    [● Live · last scan 2m ago]
Filtered by your 4 topics, 3 companies, and Operator persona
```

- Day/date in label style (uppercase 10px, letter-spacing 0.12em, muted indigo)
- Greeting in 22px Geist Sans 600
- Subtitle line in 12px muted, includes counts of active follows and persona
- Live pill (right): green dot, green text, soft glow on dot. Updates to "Scanning…" briefly during a scan, then back to "Live · last scan Nm ago"

### 4.3 Stats row — 4 tiles

| Tile | Label | Value | Subtext | Accent |
|---|---|---|---|---|
| 1 | INDEX SIZE | `64,231` | USPTO · EPO · WIPO | default (neutral) |
| 2 | NEW THIS WEEK | `+1,247` | ↑ 12% vs avg (green) | signal (indigo border) |
| 3 | YOUR FOLLOWS | `7` | 4 topics · 3 companies | default |
| 4 | EXPIRING 90D | `47` | high-opp in your topics | warning (amber border) |

- All values use `Counter` for first-load count-up animation
- All numeric: Geist Mono, tabular-nums, 24px, 600 weight
- Tile background: glass panel
- Tile 2 has the indigo accent border (it's the "newest" stat — the one that changes most)
- Tile 4 has the amber accent border (action-worthy)

### 4.4 Briefing feed — left column

Section header: `YOUR BRIEFING` (label style) with secondary metadata: `12 items · weighted by relevance to your follows`.

#### Item ordering

Items are weighted by a relevance score, not pure recency. The weighting formula (server-side, in a new `/api/v1/today/briefing` endpoint):

```
score = (
  recency_weight * recency_score  +
  follow_weight * follow_overlap  +
  quality_weight * quality_score
)
```

Where:
- `recency_score` ∈ [0, 1], decays exponentially over 14 days
- `follow_overlap` ∈ [0, 1], higher if the item touches a topic or company the user follows
- `quality_score` ∈ [0, 1], composite of opportunity_score / z_score / momentum where applicable
- `recency_weight = 0.3`, `follow_weight = 0.5`, `quality_weight = 0.2`

(Exact weights are tunable; this is the starting point. Output: 12–20 items per briefing depending on availability.)

#### Item types (V1)

Each item is rendered by `<BriefingItem>` with a `type` prop that determines the left-border color and label icon.

| Type | Color | Icon | Title shape |
|---|---|---|---|
| `trend` | `--type-trend` (indigo) | 📈 | "[Trend label] — [delta vs avg]" |
| `notable` | `--type-notable` (green) | 🔍 | "[Patent title]" + assignee · pub# subtext |
| `company` | `--type-company` (sky) | 🏢 | "[Company] — [filing surge headline]" |
| `expiring` | `--type-expiring` (amber) | ⏳ | "[Count] high-value patents in your topics expire soon" + verify caveat |
| `foryou` | `--type-foryou` (violet) | ✨ | Gradient background, distinct from others. V1: stub message. V1.1: real AI recommendations. |
| `news` (V1.1) | `--type-news` (violet, dashed border) | 📰 | "News-patent linking slot reserved" placeholder. Becomes real cards in V1.1. |

#### Required item fields (every briefing item must include these)

Every item returned by `/api/v1/today/briefing` must include:

| Field | Type | Purpose | UI placement |
|---|---|---|---|
| `reason` | string | 1-sentence explanation of WHY this item appears. Example: "Shown because you follow NVIDIA and AI imaging trend is rising." | Always visible as small line under the title, muted color |
| `source` | string | Where the data comes from. Example: "USPTO direct", "EPO OPS", "BigQuery patents-public-data" | Shown in info-icon tooltip on hover, or in expanded card detail |
| `freshness` | object `{ updated_at, relative }` | When this item was last updated. Example: `{ updated_at: "2026-06-01T08:30:00Z", relative: "2h ago" }` | Always visible, small muted text |
| `confidence` (optional) | enum `high \| medium \| low` + caveat string | For opportunity / expiry items. Example: `{ level: "medium", caveat: "Verify with official registers before relying on expiry status" }` | Always visible as Pill badge for non-high confidence; caveat string shown inline for expiry |

This is non-negotiable. The product positions itself as "evidence-first patent intelligence." A feed item that doesn't tell the user where it came from, when it was updated, and why it's showing is just noise. Reason codes make the feed self-explaining and defensible.

#### First-time user empty state

When `user.created_at < 24h ago` AND `user.topic_count == 0`:

The feed is replaced by the existing onboarding component (`StarterTopics`) PLUS three "demo briefing items" using the system-default starter topic, so the user can see what their feed will look like. Includes a banner: "Pick topics to make this yours."

#### Sparse state (data is fine, user has follows, but the feed only has 3-4 items)

Show the items naturally. Below them: `MORE TO COME` divider, then a short prompt: "Your briefing will grow as patents are filed and indexed against your follows. New items appear daily."

### 4.5 Right sidebar (280px fixed)

Three stacked widgets, each ~glass-panel card:

#### Widget 1 — My Follows
- Section: Topics — chip cluster of followed topic names, max 4 shown + "+N more"
- Section: Companies — chip cluster of followed company names, max 4 shown + "+N more"
- Footer link: `+ Follow more` → `/companies` or `/themes` depending on context

#### Widget 2 — Quick Actions
3-5 deep-link CTAs based on the user's persona:
- Operator persona: "Explore expiring in your topics", "View all trends", "Search prior art"
- Investor persona: "View momentum charts", "See company breakouts", "Browse trends"
- Curious persona: "This week's notable patents", "Surprising filings", "Trend explorer"

#### Widget 3 — Saved Patents
- Top 3 most-recently-saved watchlist items
- Each shows: pub# (mono) + assignee + 1-line title fragment
- Footer link: `View all N →`

### 4.6 Loading state

Show 4 skeleton stat tiles + 6 skeleton briefing items. Skeleton uses muted glass background with shimmer. Brand-voice loading text under the stats row: rotates through `COPY.loadingIndexing`, `loadingScanning`, `loadingMapping`, `loadingRanking`.

### 4.7 Error state

If `/api/v1/today/briefing` fails: show top header + stats row (independent endpoint) + a single error panel where the feed would be. Uses existing `ErrorBoundary` + `ErrorDisplay` styled for dark theme. CTA: "Retry" + "Report issue" (mailto:support@inventionindex8.com).

---

## 5. Patent surfaces

### 5.1 PatentCard (used on every list page)

Currently at `frontend/src/components/patents/PatentCard.tsx` (107 lines).

**Refresh:**
- Surface: glass panel (`--bg-glass`, `backdrop-blur-md`, `border-subtle` 1px)
- Scan-sweep on top edge on hover (already defined in globals.css; just apply)
- Office badge (USPTO / EPO / WIPO) — small uppercase pill with appropriate accent color
- Publication number: Geist Mono, tabular-nums, muted-secondary color
- Title: Geist Sans 600, primary color, 1.3 line-height, line-clamp-2
- Assignee + date: Geist Sans 400, muted
- **Opportunity score chip (top-right)**: gradient `--score-high` → `--signal-blue` background, "opp 92" label, mono font
- **Affordances row (bottom-left)**: small inline indicators using muted text + emoji
  - "📷 figures" if `figure_page_url` present
  - "📄 summary" if `summary` present
  - "⏳ expires 2041" if `expiry_date` known
- **View action (bottom-right)**: text link "View →" with hover underline

Hover state: gradient border (blue→violet, 1px) appears + 2px upward lift + scan-sweep across top. 200ms ease.

Focus state: 2px focus ring in `--signal-glow`, no transform.

### 5.2 Patent detail page

Currently at `frontend/src/app/(app)/patents/[id]/page.tsx`, **956 lines**. That's well past the "this file is doing too much" threshold. Decompose into:

```
frontend/src/app/(app)/patents/[id]/
  page.tsx                  # ~120 lines, orchestrates the others
  PatentDetailHeader.tsx    # ~80 lines, title/assignee/dates/save/follow
  PatentDetailTabs.tsx      # already exists at components/patents/, evolve
  tabs/
    SummaryTab.tsx          # AI summary, why-now, key claims
    OpportunityTab.tsx      # opp breakdown, narrative, risk flags
    FamilyTab.tsx           # family members, citations forward/back
    SourceTab.tsx           # claims, abstracts, drawings, source links
```

Header (top of page, not tab-gated):
- Title (Geist Sans 600, larger)
- Office badge + pub number (mono) + status pill
- Assignee + dates row
- Drawing thumbnail (right side, ~200x200) — uses `figure_page_url`
- Action row: Save (toggle, watchlist), Follow Company (toggle, follows the assignee), External Source link (Espacenet / Google Patents / USPTO)

Tabs (sticky under header):
- **Summary** (default) — uses existing `AISummaryPanel`, `WhyNowPanel`, `ClaimsPanel`
- **Opportunity** — uses existing `OpportunityBreakdown`, `OpportunityNarrativePanel`, `OpportunityScoreBadge`, `RiskFlagsBadge`
- **Family** — needs new component `FamilyPanel`, uses existing citation data
- **Source** — uses existing `ClaimsPanel` (full text), `ExternalPatentLinks`, drawing gallery

Each tab is its own component file. Tab switching uses URL query param (`?tab=opportunity`) for shareability and back-button correctness.

---

## 6. Other app surfaces (visual overhaul, no structural change)

Each of these gets the dark/premium treatment but keeps its current information architecture. The work is: replace `bg-white` with `--bg-base`, replace gray borders with `--border-subtle`, replace generic chip pills with `<Pill>`, swap loading/empty states to brand voice.

| Surface | Path | Notes |
|---|---|---|
| Trends index | `/trends` | Use `<Card variant="glass" interactive>` for trend rows. Add momentum sparklines if not present. |
| Trend detail | `/trends/[surface]/[key]` | Apply detail-page header pattern from §5.2. |
| Expiry Radar | `/expiry` | Caveat banner stays — required by brand rule. Filter pills get `<Pill>`. Result cards use glass-panel. |
| Opportunity | `/opportunity` | Differentiation from Expiry: this surface emphasizes signal-driven (commercial signals, market gaps), not time-driven. |
| Topics index | `/themes` | Topic cards use glass-panel. Subscribe button → Follow Topic. |
| Topic detail | `/themes/[id]` | Apply detail-page pattern. |
| Companies index | `/companies` | New: Follow button on each company row. Glass-panel cards. |
| Company detail | `/companies/[name]` | **Bug fix needed** (was returning 500 in dev). New: Follow button in header. Patent grid uses refreshed `PatentCard`. |
| Watchlist | `/watchlist` | Just visual refresh. List of patents using new `PatentCard`. |
| Search | `/search` | Search input dark, result cards use new `PatentCard`. Filters pane on left. |
| Account | `/account` | **Real change.** Dark form fields. Persona field (new — editable, dropdown of operator/investor/curious). Add management of followed topics + companies links. |
| Account billing | `/account/billing` | **Dark theme only, no new UI.** Preserve all existing Stripe wiring. Do NOT build fake subscription state, fake invoices, fake tier-upgrade flows, or any UI that implies production-ready billing if backend isn't there. The page just re-skins with the dark/premium aesthetic. |
| Admin pages | `/admin/*` | **Skip visual polish.** Staff-only. Make them functional, no aesthetic priority. |
| Auth pages | `/login`, `/login/verify`, `/unsubscribed` | Already passable; light touch-up only. |
| Marketing landing | `/` | **Already dark.** Minor refinements only — no major redesign. |

---

## 7. Personalization (NEW in V1)

### 7.1 Persona-based onboarding (3-step wizard)

Triggered for new users on first visit if `user.persona IS NULL`. Cannot be skipped (the persona seed is needed for sensible defaults), but Step 2 and Step 3 each have an optional "skip for now" affordance.

#### Step 1 — Pick persona

```
What brings you here?

[ Builder / Operator                                                  ]
  Track what's being built in your space, find inspiration, learn from prior art

[ Investor / Scout                                                    ]
  Identify trends, emerging companies, technology shifts before they're obvious

[ Curious / Researcher                                                ]
  Patent intelligence the way you read Stratechery — discover, briefing, highlights
```

- Single-select
- Each card uses glass-panel, hover-elevate
- Selected card gets a 1px indigo border
- Bottom: `Continue` (primary) — disabled until selection

Stored as: `user.persona` enum value: `operator` | `investor` | `curious`

#### Step 2 — Pick topics

Show the 6 existing starter topic packs (already defined in `frontend/src/lib/starterTopics.ts`) — AI / ML, Clean Energy, Biotech, Wireless, Medical Devices, Semiconductors — plus a `+ Custom topic` option that opens a name/keyword input.

- Multi-select chip cluster (toggle on/off)
- Subtitle: "Pick 1–5. You can change these anytime."
- Bottom: `Continue` (disabled if 0 selected) | `Skip for now` (skips to step 3 without setting topics)

Stored as: `topic` records via existing API.

#### Step 3 — Follow companies

Show 6–8 suggested companies based on `user.persona` and selected topics. Each row:
```
[ Company name                                          + Follow ]
  X patents in your topics · last 12mo
```

- Multi-action (click + Follow for each, toggles to ✓ Following)
- Bottom: `Finish` | `Skip for now`

Stored as: `user_company_follows` rows (new table — see §11).

#### Persona-driven defaults

The persona choice biases:
- Quick Actions widget on Today (see §4.5)
- Default sort on Trends (operator → relevance, investor → momentum, curious → most-discussed)
- Email digest tone (operator → bullet-dense, investor → trend-focused, curious → narrative)
- Suggested companies in Step 3 (different lists per persona)

### 7.2 Follow Companies feature

Adds a "Follow" button to every company surface (company detail page header, company rows on `/companies`, on patent detail pages next to the assignee).

When followed, the company name appears in:
- The Today right sidebar "My Follows" widget
- A new tab on `/companies` called "My follows"
- The briefing feed weighting (follow_overlap factor)

#### Backend additions

New table:

```
user_company_follows
  user_id                  fk users
  company_normalized_name  text  (e.g. "apple" — lowercase, suffix-stripped)
  display_name             text  (e.g. "Apple Inc." — original casing)
  created_at               timestamp
  PRIMARY KEY (user_id, company_normalized_name)
```

Normalization uses the same regex pattern locked in during Bug 4 (V1 close-out):
```
LOWER(REGEXP_REPLACE(assignee, '[ ,.]+(inc|corp|ltd|llc|gmbh|sa|ag|co)\.?$', '', 'i'))
```

New endpoints:
- `POST /api/v1/account/companies` — body: `{ company_name: string }` → normalizes and inserts
- `DELETE /api/v1/account/companies/{normalized_name}`
- `GET /api/v1/account/companies` — returns array of followed companies with patent counts in user's topics
- `GET /api/v1/account/companies/suggested?persona=...` — returns 6–8 suggestions for onboarding step 3

### 7.3 "For you" — rule-based early personalization (V1)

V1 ships a card on Today briefing feed that is honest about what it is. **It is not AI.** It is a rule-based query over follow data. The card is real (real data, real query), but its positioning must not claim AI personalization that doesn't exist yet.

**Copy (V1):**
- Label: **"For you — early personalization"** (not "✨ AI For You")
- Title: e.g., "Patents from companies adjacent to your follows"
- Body: dynamic, naming the rule. Example: "Shown because you follow Samsung and NVIDIA, and these companies file in overlapping technology areas."
- Footer line: **"Full AI recommendations are coming later."**

**V1 algorithm (rules):**
- Computes "1-hop adjacent" companies — companies that share at least one topic with a company the user follows
- Surfaces 2–3 such companies and recent notable patents from them
- No embedding, no model inference, no AI artifacts

**`reason` field** (per the briefing item required fields, §4.4): every "For you" item names exactly which follow triggered it. Example: "Shown because you follow Apple + AI imaging trend is rising."

**V1.1 upgrade:** Replaces the rule with an actual embedding-similarity query over user behavior. Card structure, slot, and reason-code pattern stay identical — only the algorithm changes. The label may upgrade to "AI personalization" once the AI engine is live.

This honest framing matters because the product positions itself as evidence-first. Implying AI personalization that doesn't exist would undermine that positioning.

---

## 8. V1.1 design hooks

These features ship in V1.1 but the V1 frontend must accommodate them without restructuring.

### 8.1 News ↔ patents linking

The briefing feed must include the `news` card type slot, designed in. V1: stub with "V1.1 — news linking slot reserved" message. V1.1: real news items from a news API (TBD: NewsAPI, AlphaSense, or RSS aggregator), with AI-generated "why this matters for patents X, Y, Z" links.

Each news card will have:
- Headline
- Source + timestamp
- "Why this matters" 1–2 sentence AI summary
- 1–3 linked patents (clickable, opens patent detail)

The card type is defined in V1 so backend can plug it in without frontend changes.

### 8.2 Full AI "For you" engine

Replaces the V1 stub. Uses patent embeddings (already in DB) + user behavior embedding (computed from viewed/saved patents) for cosine-similarity recommendations. Backend work mostly. Frontend just upgrades the stub card to a real list.

### 8.3 Follow Inventors

Mirror of Follow Companies but for inventor names. New table `user_inventor_follows`, parallel endpoints, parallel UI. Inventors are messy data (name variants, multiple people with same name) — V1.1 includes an inventor canonicalization pass before launch.

### 8.4 Email digest customization

Settings page section. Lets users:
- Toggle digest on/off
- Pick day of week (default: Monday)
- Pick item types to include (filing trends, expiring, notable, company moves, news)
- Pick item count cap

V1 ships a single fixed weekly digest. V1.1 adds the customization UI.

---

## 9. Component decomposition — files

### 9.1 New files in V1

```
frontend/src/styles/tokens.css                              # design tokens (§3.1)
frontend/src/components/ui/Card.tsx                         # glass panel surface
frontend/src/components/ui/StatTile.tsx                     # Today stats row tile
frontend/src/components/ui/BriefingItem.tsx                 # briefing feed item
frontend/src/components/ui/Counter.tsx                      # animated counter
frontend/src/components/ui/Pill.tsx                         # inline chip
frontend/src/components/ui/Button.tsx                       # CTA buttons (if not present)
frontend/src/components/ui/LiveIndicator.tsx                # pulsing-dot status
frontend/src/components/ui/SectionHeader.tsx                # page section heading
frontend/src/components/onboarding/PersonaWizard.tsx        # 3-step onboarding orchestrator
frontend/src/components/onboarding/Step1Persona.tsx
frontend/src/components/onboarding/Step2Topics.tsx
frontend/src/components/onboarding/Step3Companies.tsx
frontend/src/components/companies/FollowButton.tsx          # used on company surfaces
frontend/src/components/today/StatsRow.tsx                  # composes 4 StatTiles
frontend/src/components/today/BriefingFeed.tsx              # composes BriefingItems
frontend/src/components/today/MyFollowsWidget.tsx           # sidebar widget
frontend/src/components/today/QuickActionsWidget.tsx        # sidebar widget
frontend/src/components/today/SavedPatentsWidget.tsx        # sidebar widget
frontend/src/components/patents/PatentDetailHeader.tsx      # decomposed from page.tsx
frontend/src/components/patents/tabs/SummaryTab.tsx
frontend/src/components/patents/tabs/OpportunityTab.tsx
frontend/src/components/patents/tabs/FamilyTab.tsx
frontend/src/components/patents/tabs/SourceTab.tsx
frontend/src/lib/hooks/useFollowedCompanies.ts              # SWR wrapper for follows API
frontend/src/lib/hooks/usePersona.ts                        # SWR wrapper for user.persona
```

### 9.2 Refactored in V1

```
frontend/src/app/layout.tsx                                 # import tokens.css, set Geist fonts
frontend/src/app/(app)/layout.tsx                           # dark app shell, new nav
frontend/src/app/(app)/today/page.tsx                       # full rewrite using new components
frontend/src/app/(app)/patents/[id]/page.tsx                # decompose 956 → ~120 lines
frontend/src/app/(app)/patents/page.tsx                     # use new PatentCard
frontend/src/app/(app)/trends/page.tsx                      # visual overhaul
frontend/src/app/(app)/trends/[surface]/page.tsx            # visual overhaul
frontend/src/app/(app)/trends/[surface]/[key]/page.tsx      # visual overhaul
frontend/src/app/(app)/expiry/page.tsx                      # visual overhaul
frontend/src/app/(app)/opportunity/page.tsx                 # visual overhaul + content differentiation
frontend/src/app/(app)/themes/page.tsx                      # visual overhaul
frontend/src/app/(app)/themes/[id]/page.tsx                 # visual overhaul
frontend/src/app/(app)/companies/page.tsx                   # add Follow button column
frontend/src/app/(app)/companies/[name]/page.tsx            # FIX 500, add Follow, refresh layout
frontend/src/app/(app)/watchlist/page.tsx                   # visual refresh
frontend/src/app/(app)/search/page.tsx                      # visual refresh
frontend/src/app/(app)/account/page.tsx                     # add Persona field, dark form
frontend/src/components/patents/PatentCard.tsx              # full refresh (§5.1)
frontend/src/components/ui/Badge.tsx                        # dark-theme audit
frontend/src/components/ui/EmptyState.tsx                   # brand voice from COPY
frontend/src/components/ui/Skeleton.tsx                     # dark-theme variant
frontend/src/components/ui/StarterTopics.tsx                # dark-theme refresh
frontend/src/components/ui/FreshnessBanner.tsx              # dark-theme refresh
frontend/src/components/ui/SourceAttribution.tsx            # dark-theme refresh
frontend/src/app/globals.css                                # tokens.css import, more component classes
frontend/tailwind.config.ts                                 # confirm tokens mirror tokens.css
```

### 9.3 Unchanged in V1

```
frontend/src/app/(marketing)/page.tsx                       # marketing landing
frontend/src/app/(marketing)/pricing/page.tsx
frontend/src/app/(marketing)/about/page.tsx
frontend/src/app/(marketing)/contact/page.tsx
frontend/src/app/(marketing)/privacy/page.tsx
frontend/src/app/(marketing)/terms/page.tsx
frontend/src/lib/brand.ts                                   # brand constants — keep
frontend/src/lib/starterTopics.ts                           # starter topic packs — keep
frontend/src/components/marketing/*                         # marketing-only components
frontend/src/app/(app)/admin/*                              # admin pages — skip polish
```

---

## 10. Backend changes needed for V1

| Change | Where | Priority | Why |
|---|---|---|---|
| **Fix `/companies/[name]` 500** | `backend/app/api/v1/companies.py` | **BLOCKER — Phase B before any Follow UI** | Follow Companies onboarding points users at this route. Broken company detail = broken onboarding. |
| `user.persona` column (nullable enum) | `users` table + Alembic migration | High | Persona onboarding |
| `user_company_follows` table | new Alembic migration | High | Follow Companies |
| `GET /api/v1/today/briefing` | new endpoint, returns typed items with `reason` / `source` / `freshness` / `confidence` fields per §4.4 | High | Weighted feed for Today |
| `POST/DELETE/GET /api/v1/account/companies` | new endpoints | High | Follow Companies CRUD |
| `GET /api/v1/account/companies/suggested?persona=X` | new endpoint | High | Onboarding step 3 |
| `PUT /api/v1/account/persona` | new endpoint | High | Set/update persona |
| Brief item-type discriminator + reason/source/freshness fields in API responses | `backend/app/api/v1/today.py` | High | So frontend can render with correct `<BriefingItem type=...>` and reason codes |

All backend changes are additive (new tables, new endpoints, new columns). No breaking changes to existing endpoints. No data migrations beyond schema.

**Future-proofing note (V1.1+):** `user.persona` is a single-column enum for V1 simplicity. V1.1 will likely add a `user_preferences` JSONB column to hold richer preferences (email digest cadence, item-type toggles, timezone, locale, notification rules). The persona enum stays as a separately-indexed column; the JSONB holds non-indexed soft preferences. V1 spec does **not** add the JSONB column — only documents the future direction so Hermes doesn't paint itself into a corner.

---

## 11. Phasing

### 11.1 V1 — 7–9 weeks

Phases are ordered to put **personalization substrate before the surface that uses it**. The Today screen depends on persona, follows, and the briefing endpoint — so backend + onboarding ship before Today's final build. Foundation primitives ship first because every later phase consumes them.

#### Phase 0 — Preflight gate (Day 0, before any implementation)

A no-code orientation pass. Hermes reports findings before Phase A begins. If anything in this gate fails, Andy decides whether to fix it or carry on.

1. **Route inventory**: list every file under `frontend/src/app/(app)/` and `frontend/src/app/(marketing)/`. Confirm what exists vs what this spec assumes exists.
2. **Resolve route naming**: confirm `/themes` is the canonical route, "Topics" is the UI label (per §2.1 decision 2). Grep for "Topics" / "Themes" / "themes" / "topics" in code and copy. Flag any inconsistency.
3. **Resolve `/today` vs `/dashboard`**: grep `/dashboard` in `frontend/`, `backend/`, email templates, Stripe success_url, and `.hermes/`. Report all references. If anything still points at `/dashboard`, propose a redirect strategy.
4. **Working tree state**: `git status` — confirm clean. If not, name what's uncommitted and ask Andy whether to land or revert before starting.
5. **Screenshot capability**: confirm whether Hermes can produce real screenshots (headless browser available?) or whether observations will be HTML/structural only. Be explicit; do not fabricate visual descriptions either way.
6. **`/companies/[name]` 500**: reproduce the bug locally and report the stack trace. Confirm scope of the fix needed before Phase B.
7. **Existing component audit**: read `frontend/src/components/ui/` and `frontend/src/components/patents/` and list what already exists vs what this spec adds. Flag any duplication between §9.1 (new) and components already present.
8. **No new dependencies without approval**: list any npm/pip package Hermes thinks it needs beyond `next/font/google` (Geist). Andy approves before install.

Deliverable: short preflight report at `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md`. Wait for Andy's go-ahead before Phase A.

#### Phase A — Foundation + shell (Week 1)
1. Create `tokens.css`, wire into root layout
2. Set up Geist Sans + Geist Mono via `next/font/google`
3. Build base UI primitives: `Card`, `StatTile`, `BriefingItem`, `Counter`, `Pill`, `Button`, `LiveIndicator`, `SectionHeader`
4. Refresh `Badge`, `EmptyState`, `Skeleton`, `StarterTopics`, `FreshnessBanner`, `SourceAttribution` for dark theme
5. Refactor `(app)/layout.tsx` to dark shell. Rebuild nav: logo + 7-item nav + search/alerts/account
6. Verify `prefers-reduced-motion` behavior across all primitives
7. **Gate**: build clean, no TS errors, every primitive renders in a temporary `/dev/components` route or equivalent for visual review; app shell loads at every existing authenticated route without layout breakage (even if pages inside are still light-themed)

#### Phase B — Data contracts + backend minimums (Week 2)
1. **Fix `/companies/[name]` 500** (V1 blocker per §2.1 decision 8 + §10)
2. Alembic: `user.persona` nullable enum column on `users`
3. Alembic: `user_company_follows` table per §7.2 schema
4. Endpoint: `PUT /api/v1/account/persona`
5. Endpoints: `POST/DELETE/GET /api/v1/account/companies`
6. Endpoint: `GET /api/v1/account/companies/suggested?persona=X`
7. Endpoint: `GET /api/v1/today/briefing` returning typed items with mandatory `reason` / `source` / `freshness` / `confidence` fields per §4.4
8. Pytest coverage for each new endpoint
9. **Gate**: 341-test baseline still green (3 xfail OK). New endpoints all return real shapes against current DB. `/companies/[name]` returns 200 for at least 5 real companies. Migrations apply cleanly on a throwaway DB.

#### Phase C — Onboarding + Follow Companies UI (Week 3)
1. `PersonaWizard` 3-step flow components (Step 1 / 2 / 3)
2. Trigger logic: open wizard on first authenticated visit when `user.persona IS NULL`
3. `FollowButton` component, wired to Phase B endpoints
4. Add `FollowButton` to: `/companies` list rows, `/companies/[name]` header. (Patent detail header gets `FollowButton` in Phase E when the detail page is decomposed.)
5. "My follows" tab on `/companies` (filter view)
6. Account page Persona edit field (links to wizard or inline-edits)
7. **Gate**: signup → wizard → arrive at Today with persona + topics + followed companies persisted. Follow toggle works on companies list and detail. Account page shows current persona, editable. All four data points (persona, topics, companies, followed-company-feed-overlap) verifiably influence the briefing endpoint response.

#### Phase D — Today screen (Week 4)
1. Build `StatsRow` composing 4 `StatTile`s
2. Build `BriefingFeed` consuming `/api/v1/today/briefing`, rendering all 6 item types (5 real + 1 V1.1 placeholder)
3. Build sidebar widgets: `MyFollowsWidget`, `QuickActionsWidget`, `SavedPatentsWidget`
4. Wire reason / source / freshness / confidence rendering per §4.4 required fields
5. Implement first-time empty state (uses Phase C wizard if persona unset)
6. Implement sparse state (3-4 items + "MORE TO COME" divider)
7. Implement loading / error states
8. **Gate**: end-to-end usability on Today. All 4 stat tiles count up. All 5 V1 item types render with their required fields visible. V1.1 `news` slot shows placeholder. Right sidebar widgets all populated from real data. First-time + sparse + error states all reachable and look intentional.

#### Phase E — Patent surfaces (Week 5)
1. Refresh `PatentCard` with glass-panel + scan-hover + opp chip + affordances per §5.1
2. Decompose `patents/[id]/page.tsx` (956 → ~120) into Header + Tabs + 4 tab components per §5.2
3. Wire tab navigation via `?tab=` query param
4. Update `patents/page.tsx` (list page) to use new `PatentCard`
5. Add Follow Company button to patent detail header (from Phase C `FollowButton`)
6. **Gate**: 5 representative patents render correctly across all tabs. The 956-line file is fully decomposed; no tab component exceeds ~200 lines. Existing AI panels (`AISummaryPanel`, `OpportunityBreakdown`, etc.) function inside the new tab structure unchanged.

#### Phase F — Remaining surfaces (Week 6)
1. Trends index + detail + nested routes
2. Expiry Radar (with mandatory caveat banner from §3.6)
3. Opportunity (differentiate content from Expiry — signal-driven framing)
4. Themes index + detail
5. Companies index (Follow button column from Phase C already wired)
6. Watchlist
7. Search
8. Account: real changes per §6 + §2.1 decision 10
9. Account billing: dark theme only, no new UI per §6 + §2.1 decision 10
10. Auth pages: light touch-up only
11. **Gate**: every authenticated route is dark/premium. No white surfaces remain except admin (intentional). Freshness + source + caveat visible on every data surface per §3.6.

#### Phase G — Polish + verification (Week 7)
1. Mobile responsiveness audit (375px, 768px, 1024px)
2. `prefers-reduced-motion` audit (every animation respects it)
3. Accessibility audit: keyboard nav, focus-visible, aria-labels, color contrast ≥ 4.5:1
4. Loading states + error states pass
5. Lighthouse: ≥ 90 accessibility, ≥ 80 performance on `/today`, `/patents/[id]`, `/`
6. Component tests: `Counter`, `BriefingItem`, `Pill`, `FollowButton`, `PersonaWizard` steps, `StatTile`, `LiveIndicator`
7. E2E test: signup → wizard → Today → click into a patent → save to watchlist → return to Today → confirm "Saved Patents" widget shows the patent
8. Honesty audit: every "For you" / news / data card displays its `reason`, `source`, `freshness`, and `confidence` (where applicable). No fabricated content anywhere.
9. **Gate**: build clean, all tests pass, no TS errors, Lighthouse targets hit, accessibility report green, honesty audit clean.

#### Phase H — Buffer (Weeks 8–9)
Reserved for overflow, regressions, copy revisions, design tweaks Andy requests after seeing it live.

### 11.2 V1.1 — 4–6 weeks (post-V1 ship)

1. **AI "For you" full engine** — patent embedding pipeline upgrade, user behavior embedding, cosine-similarity recommendation endpoint, replace stub card
2. **News ↔ patents integration** — pick news source (NewsAPI / RSS aggregator), AI linker (uses Anthropic with cached `AIArtifact` rows), feed integration via existing `news` card type
3. **Follow Inventors** — inventor canonicalization pass + parallel feature to Follow Companies
4. **Email digest customization** — settings page section, per-type item toggles
5. **Per-topic notification rules** — alert when specific events happen in a topic

### 11.3 V2 — later, not committed

1. Saved searches + alert rules engine
2. CPC code follows
3. Team workspaces (Enterprise tier)
4. Public sharing of briefings (signed URLs)
5. Slack / API exports
6. Mobile-first redesign (V1 is desktop-primary, tablet-acceptable)

---

## 12. Constraints (carry-over)

- **Andy commits, Claude/Hermes never run state-changing git** (per `feedback-andy-controls-commits-and-prod-flips` memory)
- **Stripe stays TEST MODE**; flipping to LIVE is a separate explicit decision
- **Email stays `EMAIL_SEND_MODE=dev`**; sending to real users requires explicit approval
- **ScrapeGraphAI stays muted** (`SCRAPEGRAPH_ENABLED=false`); Enterprise V1.1+ only
- **Patent figures: link-only, never host or re-serve** (per `AGENTS.md`)
- **AI output cached as `AIArtifact` rows** (per `AGENTS.md`)
- **Forbidden language**: never "free to use", "public domain", "safe to build", "guaranteed", "predicts", "directional intelligence signals" (sounds AI-generated). Required disclaimer near opportunity scores: "Research intelligence only. Not legal, financial, or investment advice."
- **No fake data of any kind.** This is a load-bearing constraint:
  - No fabricated patent records, assignee names, inventor names, or publication numbers
  - No fake news headlines, sources, or "why this matters" copy — the V1.1 news slot stays an honest placeholder until V1.1
  - No mocked-up briefing items, "demo" trends, or sample company moves shown to real users (a clearly-labeled `/dev/components` showcase page for component review only is acceptable, gated behind staff-only auth)
  - No simulated subscription state, fake invoices, or staged tier upgrades on the billing page
  - No "AI-recommended" labeling on the V1 rule-based "For you" card (§7.3)
  - Honest empty / sparse / blocked states are always better than fabricated content. If a surface has nothing real to show, say so plainly.
- **No new heavy dependencies**. Allowed: `next/font/google` (Geist). Disallowed: framer-motion (use CSS), D3, Three.js, canvas/WebGL, any new charting library.

---

## 13. Out of scope (V1)

- Marketing landing page redesign — already polished, do not touch beyond minor copy refinements if any
- Admin pages visual polish — staff-only, no aesthetic priority
- Mobile-first redesign — V1 supports tablet+, mobile-acceptable; mobile-primary is V2
- Backend Round 3 (PatentsView + BigQuery targeted abstracts, citation/family debug) — parked, separate sprint
- News data integration — V1.1
- AI "For you" embedding engine — V1.1
- Saved searches / alerts — V2
- Stripe LIVE flip — separate decision
- GCP migration of hosting — current Hetzner VPS deploy stays

---

## 14. Quality bars

| Dimension | V1 target |
|---|---|
| Lighthouse accessibility | ≥ 90 on `/today`, `/patents/[id]`, `/` |
| Lighthouse performance | ≥ 80 on `/today` (slower acceptable on deeply-componented pages) |
| Color contrast | WCAG AA minimum (4.5:1 for body text, 3:1 for large text) |
| Keyboard navigation | Every interactive element reachable, focus-visible always present |
| Screen reader | aria-labels on icon-only buttons, semantic HTML throughout |
| `prefers-reduced-motion` | Every animation respects it |
| Mobile breakpoint | 375px works (degrades to single-column), 768px is decent, 1024px+ is target |
| Browser support | Chrome / Safari / Firefox / Edge latest 2 versions |
| Build artifact | No TS errors, no new lint warnings |
| Backend tests | 341-test baseline still green (3 xfail OK) |

---

## 15. Risks & open questions

1. **Briefing feed performance** — weighting 12–20 items across multiple sources per request may be slow if naively implemented. Mitigation: cache the briefing per-user per-day (re-compute once daily, not per-request).
2. **AI "For You" stub feels hollow** — if the V1 stub message is too obviously fake, it undermines the "tailored insights" promise. Mitigation: the adjacent-companies query returns real data, so the stub is a real card with a slightly different (less personalized) algorithm. V1.1 replaces the algorithm, not the card.
3. **Followed-companies normalization edge cases** — "Alphabet Inc." vs "Google LLC" are the same entity to a human but won't normalize together by regex. Mitigation: V1 normalization is regex-based and acceptable; V1.1 adds an entity-resolution pass.
4. **Geist font fallback** — Geist Sans is on Google Fonts but loading from there has a network dependency. Mitigation: `next/font/google` self-hosts the fonts at build time.
5. **Persona-driven defaults complexity** — different sort orders / suggestion lists per persona is real conditional logic. Mitigation: keep persona influence to the Quick Actions widget and Step 3 suggestions; don't fork the entire app per persona.
6. **Today briefing endpoint design** — Should be a single endpoint returning all item types or multiple parallel endpoints orchestrated frontend-side? **Decision: single endpoint** (`/api/v1/today/briefing`) returning a typed array, so backend owns the weighting logic.

---

## 16. Approval gate

This spec captures Andy's brainstorming decisions through 2026-06-01. Before the writing-plans skill is invoked to produce a step-by-step implementation plan, Andy reviews this doc and confirms:

- [ ] All 6 locked decisions match what was discussed
- [ ] Phasing breakdown (V1 / V1.1 / V2) reflects desired ambition vs scope
- [ ] No surface is missing from the §6 visual-overhaul list
- [ ] No new personalization dimension expected in V1 beyond what's listed in §7
- [ ] Backend changes in §10 are acceptable
- [ ] Quality bars in §14 are appropriate (not too lax, not unrealistic)
- [ ] Out-of-scope list in §13 is comprehensive — no surprises

Once approved, Claude invokes the `writing-plans` skill to produce a step-by-step Hermes-executable plan against this spec.
