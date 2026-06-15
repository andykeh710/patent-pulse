# UX Foundation — Sprint 2

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-2-ux-foundation`

---

## 1. Component Inventory

### New Components Created

| Component | File | Purpose |
|-----------|------|---------|
| `PageHeader` | `components/ui/PageHeader.tsx` | Consistent page header with title, description, freshness banner, action slots |
| `InsightCard` | `components/ui/InsightCard.tsx` | Core intelligence display pattern: type badge, title, summary, why-it-matters, evidence, confidence, actions |
| `StatusBadge` | `components/ui/StatusBadge.tsx` | Semantic status display with tone presets + helper functions for expiry/confidence states |
| `LoadingState` | `components/ui/LoadingState.tsx` | Unified loading skeletons: card, table, detail, grid variants |
| `ErrorState` | `components/ui/ErrorState.tsx` | Page-level error display with retry |
| `FilterChips` | `components/ui/FilterChips.tsx` | Reusable filter display with remove/clear-all |

### Existing Components (Preserved)

| Component | File | Status |
|-----------|------|--------|
| `Button` | `ui/Button.tsx` | ✅ 6 variants, focus-visible ring, disabled state |
| `Badge` | `ui/Badge.tsx` | ✅ 5 variants, 2 sizes |
| `Card` | `ui/Card.tsx` | ✅ 3 variants, interactive prop |
| `Skeleton` | `ui/Skeleton.tsx` | ✅ + `PatentCardSkeleton` |
| `EmptyState` | `ui/EmptyState.tsx` | ✅ Updated: multi-action support, detail field, 6 icons |
| `ErrorDisplay` | `components/ErrorDisplay.tsx` | ✅ Preserved (used by legacy pages) |
| `SectionHeader` | `ui/SectionHeader.tsx` | ✅ Preserved (used in patent detail panels) |
| `StatTile` | `ui/StatTile.tsx` | ✅ Counter animation, accent variants |
| `SourceAttribution` | `ui/SourceAttribution.tsx` | ✅ Patent office attribution |
| `FreshnessBanner` | `ui/FreshnessBanner.tsx` | ✅ (used by PageHeader) |
| `Spinner` | `ui/Spinner.tsx` | ✅ |
| `Counter` | `ui/Counter.tsx` | ✅ |
| `Pill` | `ui/Pill.tsx` | ✅ |
| `LiveIndicator` | `ui/LiveIndicator.tsx` | ✅ |
| `Reveal` | `ui/Reveal.tsx` | ✅ |
| `StarterTopics` | `ui/StarterTopics.tsx` | ✅ |

---

## 2. Component Usage Guidelines

### PageHeader

Every main app screen should start with a `PageHeader`.

**Props:**
- `title` (required) — page title rendered as h1
- `description` — 1-2 line description of what the screen is for
- `freshnessSources` — show data freshness indicator (e.g., `["patents"]`)
- `primaryAction` / `secondaryAction` — CTA slots for action buttons
- `label` — small uppercase label above the title
- `meta` — metadata below the description

**Applied to:** Companies, Expiry Radar

### InsightCard

Use for displaying intelligence signals across Today, Expiry Radar, and other intelligence surfaces.

**Props:**
- `type` — `signal | risk | opportunity | update | recommendation`
- `title`, `summary` (required)
- `whyItMatters` — 1-sentence user impact
- `evidence` — backing data (e.g., "14 patents, 5 assignees")
- `confidence` — `high | medium | low`
- `primaryAction` / `secondaryAction` — link or button CTAs
- `timestamp` — when the insight was generated
- `sourceIds` — badge-style source indicators

### EmptyState

Every data surface should have an empty state that explains what happened and suggests next actions.

**Props:**
- `icon` — `search | list | alert | patent | calendar | bookmark`
- `title`, `message` (required)
- `detail` — additional context about why data is missing
- `actions` — array of `{ label, href?, onClick?, primary? }`

### LoadingState

Use for page-level loading. Replaces ad-hoc skeleton patterns.

**Props:**
- `variant` — `card | table | detail | grid`
- `count` — number of skeleton items
- `className` — additional styling

### StatusBadge

For expiry status, legal confidence, and other semantic labels.

**Helper functions:**
- `expiryStatusTone(status)` — maps backend status strings to tones
- `confidenceTone(confidence)` — maps confidence levels to tones

---

## 3. UX State Guidelines

### Every data surface must handle four states:

| State | What to show | Component |
|-------|-------------|-----------|
| **Loading** | Skeleton matching the content shape | `LoadingState` |
| **Empty** | Explanation + next action suggestions | `EmptyState` |
| **Error** | Error message + retry button | `ErrorState` |
| **Success** | Data (the normal render) | Page-specific |

### Empty state copy guidelines:

- NEVER just "No results" or "Nothing here"
- ALWAYS explain what happened
- ALWAYS explain why (data not yet ingested, backfill pending, filters too narrow)
- ALWAYS suggest what to do next
- NEVER hide real data issues behind vague empty states

### Honesty principle:

If data is missing because of a known gap (backfill not run, enrichment pending), STATE THAT EXPLICITLY. The user should never wonder "is this broken or is there just no data?"

---

## 4. Navigation Model

### Target structure (implemented):

| Position | Label | Route | Purpose |
|----------|-------|-------|---------|
| 1 | Today | `/today` | Daily intelligence hub |
| 2 | Search | `/search` | Patent discovery |
| 3 | Companies | `/companies` | Company intelligence |
| 4 | Expiry Radar | `/expiry` | Expiry opportunities |
| 5 | Watchlist | `/watchlist` | Saved patents |
| 6 | All Patents | `/patents` | Browse all patents |
| 7 | Opportunities | `/opportunity` | High-opportunity patents |
| 8 | Trends | `/trends` | Filing momentum |
| 9 | Topics | `/themes` | Technology themes |

### Changes from previous:
- "Expiring Patents" → "Expiry Radar" (more commercially oriented)
- "Patents" → "All Patents" (disambiguates from Search)
- Reordered: Search and Companies promoted above legacy browse surfaces
- Removed "About / Limitations" (redundant; legal caveats are inline)
- Watchlist promoted from bottom to position 5

### TopNav sync:
TopNav still shows: Today, Patents, Expiry, Opportunities, Trends, Topics, Companies. This should be updated in a follow-up to match the sidebar. Low priority — most users use sidebar.

---

## 5. Before/After Screenshots

### SCREENSHOTS NEEDED (requires running app locally)

- [ ] Companies page with new PageHeader
- [ ] Expiry Radar with new PageHeader
- [ ] NavSidebar with reordered items
- [ ] Companies CoverageBar with enrichment-pending explanations (from Sprint 1)

---

## 6. Applied Surfaces

| Surface | PageHeader | EmptyState | LoadingState | ErrorState | Notes |
|---------|-----------|------------|-------------|------------|-------|
| Companies | ✅ | ⬜ (in-page) | ⬜ (in-page) | ⬜ | CoverageBar enhanced in Sprint 1 |
| Expiry Radar | ✅ | ⬜ (legal caveat exists) | ⬜ | ⬜ | Legal caveat banner preserved |
| Today | ⬜ | ⬜ | ⬜ | ⬜ | Full redesign in Sprint 3 |
| Search | ⬜ | ⬜ | ⬜ | ⬜ | Full redesign in Sprint 4 |
| Patent Detail | ⬜ | ⬜ | ⬜ | ⬜ | Full redesign in Sprint 4 |
| Watchlist | ⬜ | ⬜ | ⬜ | ⬜ | Redesign in Sprint 6 |
| Patents list | ⬜ | ⬜ | ⬜ | ⬜ | Redesign in Sprint 4 |

---

## 7. Accessibility Baseline

| Check | Status |
|-------|--------|
| Button has focus-visible ring | ✅ (Button component has `focus-visible:ring-2`) |
| Links vs buttons correct | ✅ (Link for navigation, button for actions) |
| Semantic heading order | ✅ (PageHeader uses h1) |
| FilterChips have aria-labels | ✅ |
| LoadingState has role="status" | ✅ |
| EmptyState icons have aria-hidden | ✅ |
| Touch targets | ⚠️ Need audit at 375px |
| Color contrast | ⚠️ Need Lighthouse audit |
| Keyboard navigation | ⚠️ Need manual walkthrough |

---

## 8. Known Follow-Up Work

### Sprint 3 — Today as daily habit screen
- Apply InsightCard to Today page
- Add Daily Brief synthesis card
- Add "Since your last visit" tracking
- Add persona nudge

### Sprint 4 — Patent & Search intelligence
- Redesign patent detail with executive summary
- Add search filters and saved searches
- Apply PageHeader to Search and Patents

### Sprint 5 — Company intelligence
- Company portfolio movement
- Follow/watch companies
- Expiry exposure per company

### Sprint 6 — Retention
- Expand Watchlist (companies, themes, searches)
- Feedback widget
- Activation tracking

---

## 9. Baseline

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✅ PASS |
| `npm run build` | ✅ PASS (7.8s) |
| `npm run lint` | ✅ PASS |
| `npm test` | ✅ 53/53 PASS |
