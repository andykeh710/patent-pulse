# Visual Revamp Plan — Post PR #51

Branch: `visual-revamp-post-pr51`
Base: `origin/release/revamp-launch-validation` (e038208)

## Audit Findings

### Critical — Must Fix

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | **NavSidebar active state typo** — `bg-bg-[var(--bg-elevated)]` (double `bg-` prefix, invalid CSS) | `NavSidebar.tsx:91` | Active nav item has no visible background highlight. Users can't tell which page they're on. |
| 2 | **TopNav and Sidebar both render on app pages** — 256px sidebar + 14px topnav = ~270px of permanent chrome. On 1440px screens this leaves only ~1170px for content. On 1280px it's ~1010px. | `layout.tsx` + `TopNav.tsx` + `NavSidebar.tsx` | Wasted screen real estate. The sidebar and topnav list the same items. |

### Medium — Visual Quality

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 3 | **Source Health page commented-out import** — `// import { FreshnessChip }` | `admin/source-health/page.tsx:10` | Dead code. Remove. |
| 4 | **Marketing page hardcoded colors** — uses `text-orange-400`, `text-red-400`, `bg-red-500/15` instead of design tokens | `(marketing)/page.tsx` | Marketing page doesn't respond to theme changes. Inconsistent with app dark theme. |
| 5 | **Sidebar has 9 main nav items + 2 admin items** — too many. "All Patents", "Opportunities", "Trends" are secondary. | `NavSidebar.tsx` | Cognitive overload. |

### Low — Polish

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 6 | **BrandMark "8" badge** in a colored square — reads as a notification badge, not a version number | `BrandMark.tsx` | Minor confusion. |
| 7 | **Sidebar uses raw SVG path strings** for icons — hard to maintain, no hover states | `NavSidebar.tsx` | Visual stagnation. |

## Plan

### Fix 1: NavSidebar active state typo
- Line 91: `bg-bg-[var(--bg-elevated)]` → `bg-[var(--bg-elevated)]`
- This is a one-character fix that restores the active nav item highlight.

### Fix 2: Source Health dead import
- Remove commented-out line 10 in `admin/source-health/page.tsx`

### Fix 3: Marketing page tokenize hardcoded colors
- Replace `text-orange-400` → `text-[var(--warn)]`
- Replace `text-red-400` → `text-[var(--danger)]`
- Replace `bg-red-500/15` → `bg-[var(--danger-bg)]`
- Replace `bg-orange-500/15` → `bg-[var(--warn-bg)]`
- These are the confidence pill and usage signal badge colors.

### Fix 4: Sidebar item reduction (cosmetic only)
- Group secondary items under a collapsible "More" section
- This is a judgment call — if you prefer to keep all items visible, skip this fix.

### NOT Doing (out of scope for this revamp sprint)
- Removing sidebar entirely (requires nav restructure — S6 per roadmap)
- TopNav dropdown restructure (S6)
- Removing `/opportunity` and `/patents`-list (product decision)
- V4 community surfaces
- Backend changes

## Risk Assessment

- All fixes are cosmetic/presentation-layer only
- No route changes, no data model changes, no backend changes
- Fix #1 is one character — zero blast radius
- Fix #3 changes marketing page colors but only within the confidence pill badges — the rest of the page already uses tokens
- Fix #2 is dead code removal only
