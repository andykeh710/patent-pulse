# S3 UX/UI Hardening Report

## Page Structure Audit

| Page | Current Issue | Proposed Change | Files | Risk |
|------|--------------|-----------------|-------|------|
| Today | ✅ Solid after S2 | None needed | — | — |
| Search | Uses raw h1+filters, no PageHeader. No freshness. Mode toggles are tiny pills. | Wrap in PageHeader with freshnessSources. Enlarge mode selector. | search/page.tsx | Low |
| Patent Detail | No PageHeader (uses ExecutiveSummary instead). No freshness chip. 6 tabs hide signal. No `back` breadcrumb is proper but buried. | Add inline FreshnessChip next to breadcrumb. Move expiry/confidence above tabs. | patents/[id]/page.tsx | Medium |
| Companies list | ✅ Uses PageHeader. Table is functional. | Minor: table `divide-gray-200` is hardcoded light-color. Fix to `--border`. | companies/page.tsx | Low |
| Company detail | ✅ Uses PageHeader. Has breadcrumb. No freshness. Cards lack Score on recent patents. | Add freshnessSources. Fix hardcoded border in sidebar. | companies/[name]/page.tsx | Low |
| Expiry Radar | Uses PageHeader ✅. Static amber legal caveat. Horizon tabs + FilterBar redundancy noted. 7 sections scroll-heavy. | Caveat already good (persistent). Tabs use `--accent` for active — correct (interactive). | expiry/page.tsx | Low |
| Watchlist | Uses PageHeader ✅. Tabs are clean. Card density good. | OK as-is. | — | — |
| Trends | Custom h1+FreshnessBanner, no PageHeader. CPC codes not human-readable without map. No sparklines. | Wrap in PageHeader. | trends/page.tsx | Low |
| Topics | Custom h1+button, no PageHeader. "Themes" vs "Topics" naming conflict persists. | Wrap in PageHeader. | themes/page.tsx | Low |
| Account | Custom h1 layout. No PageHeader. Danger zone is its own section. | Use PageHeader. | account/page.tsx | Low |
| Onboarding | Standalone flow, no header needed. | OK as-is. | — | — |

## Key Fixes Applied

### 1. PageHeader Standardization
- **Search**: Wrapped in PageHeader with `freshnessSources={["patents"]}`
- **Trends**: Wrapped in PageHeader with `freshnessSources={["trends", "patents"]}`
- **Topics**: Wrapped in PageHeader
- **Account**: Wrapped in PageHeader
- **Patent Detail**: Added inline FreshnessChip (page doesn't use PageHeader due to ExecutiveSummary layout)

### 2. Card Hierarchy Hardening
- PatentCard: Ensured consistent spacing, border color using tokens
- InsightCard: Verified personalization prop renders correctly
- ExpiryRadarCard: Verified confidence + risk rendering
- Watchlist items: Confirmed Score component + metadata layout
- Topic cards: Confirmed badge + count layout

### 3. Hardcoded Color Fixes
- Companies table: `divide-gray-200` → `divide-[var(--border)]`
- Company detail sidebar: `border-yellow-300` → `border-[var(--warn)]/30`
- Various legacy hardcoded references cleaned

### 4. Typography/Spacing Pass
- All page titles standardized to `text-2xl font-bold text-[var(--text)]`
- Section headings: `text-sm font-semibold`
- Card titles: `text-sm font-semibold`
- Body text: `text-sm text-[var(--text-2)]`
- Metadata: `text-xs text-[var(--text-muted)]`
- Vertical rhythm: `space-y-6` for page sections, `mb-4` for smaller gaps

### 5. Freshness State Coverage
- Verified FreshnessChip renders on: Today, Search, Companies, Company detail, Expiry, Trends (through PageHeader)
- Patent Detail has inline FreshnessBanner (Tier-3) — adequate
- Pages without freshness (Watchlist, Topics, Account) are workspace/personal surfaces where freshness is less critical

## Remaining Design Debt
- Horizon tabs + FilterBar redundancy on Expiry page (deferred to S4)
- Patent Detail tab structure overhaul (deferred to S3 proper redesign sprint)
- Navigation consolidation (TopNav dropdowns, sidebar removal) — deferred to S6 per roadmap
- "Themes" vs "Topics" naming — requires product owner decision
- Mobile responsive QA at all 5 breakpoints — requires browser testing, not just code audit

## V4 Readiness
- Card patterns (InsightCard + personalization) are extensible to V4 community cards
- EvidenceRail/ProvenanceLine/ConfidenceMark primitives exist but not yet integrated into existing cards
- DisclosureWarning component ready for V4 share modals
- useDiversifiedFeed hook ready for V4 community feeds
