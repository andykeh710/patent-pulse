# Invention Index 8 — Revamp Roadmap

**Date:** 2026-06-14
**Author:** Hermes Agent
**Based on:** app-map.md, tech-audit.md, product-audit.md
**Operating principle:** Stabilize core flows first, then revamp screens for repeat usage and commercial value.

---

## Guiding Principles

1. **Do not rewrite the whole app.** Refactor screen-by-screen, flow-by-flow.
2. **Create a safety net first.** Fix build/typecheck/tests, then change UI.
3. **Ship in small PRs.** One screen, one flow, or one infrastructure layer per PR.
4. **Every main screen must answer three questions:**
   - What changed?
   - Why should I care?
   - What action should I take now?
5. **Every empty state must sell the product.**
6. **Every key data object must lead to a user action** (save, follow, compare, export, alert, share, investigate).

---

## Phase 0 — Stabilization (Sprint 1)

**Goal:** Trust the app before improving it. Fix what's broken, document the rest.

### PR 0.1: Fix typecheck + lint errors
- **Files:** `frontend/src/app/blog/[slug]/page.tsx`, `frontend/src/app/(app)/account/webhooks/page.tsx`
- **Changes:** Fix `prefer-const` error (line 238), fix `Type '{}' is not assignable to type 'ReactNode'` (line 225)
- **Verification:** `tsc --noEmit` passes, `npm run lint` passes (0 errors)
- **Estimate:** 30 min

### PR 0.2: Fix timezone-dependent test
- **Files:** `frontend/src/lib/utils.test.ts`
- **Changes:** Set `TZ=UTC` in test or use `toLocaleDateString('en-US', {timeZone: 'UTC'})` in `formatDate`
- **Verification:** `npm test` passes (53/53)
- **Estimate:** 15 min

### PR 0.3: Fix Companies "0 of 0" coverage bars
- **Files:** Backend supplier enrichment, `backend/app/api/v1/suppliers.py`
- **Root cause:** `supplier_normalized.country` and `supplier_normalized.entity_type` columns are never populated. The `assigned_suppliers` table has country data from PatentsView that needs to flow into the normalized table.
- **Changes:** Backfill country/entity_type from `assigned_suppliers` → `supplier_normalized`. Add migration if needed. Fix the summary query or add fallback logic.
- **Verification:** Companies page shows non-zero coverage bars. Country filter dropdown populates. Entity mix badges appear.
- **Estimate:** 2-4 hours (investigation + backfill)

### PR 0.4: Fix remaining unused-var lint warnings
- **Files:** 10+ files with `@typescript-eslint/no-unused-vars` warnings
- **Changes:** Prefix unused params with `_` or remove dead imports
- **Verification:** `npm run lint` shows 0 warnings
- **Estimate:** 30 min

### PR 0.5: Address npm audit vulnerabilities (non-breaking)
- **Command:** `npm audit fix`
- **Verification:** `npm audit` shows 0 non-breaking vulnerabilities
- **Note:** Do NOT force-update @sentry/nextjs (major version jump). Defer to post-revamp.
- **Estimate:** 5 min

### PR 0.6: Backend venv recreation (dev experience)
- **Changes:** `rm -rf .venv && python3.12 -m venv .venv && poetry install --with dev`
- **Verification:** `ruff check .` runs, `pytest` runs
- **Estimate:** 15 min

---

## Phase 1 — UX Foundation (Sprint 2)

**Goal:** Make the app feel like one coherent product before adding new intelligence.

### PR 1.1: Insight Card component
- **Files:** `frontend/src/components/ui/InsightCard.tsx`
- **Schema:** `type: signal | risk | opportunity | update | recommendation`, `title`, `summary`, `why_it_matters`, `evidence`, `source_ids`, `confidence`, `timestamp`, `primary_action`, `secondary_action`
- **This is the reusable pattern for every intelligence surface.** Build once, use everywhere.
- **Verification:** Component renders in `/dev/components`

### PR 1.2: Standardize empty states
- **Files:** All app pages
- **Changes:** Every screen with data must show one of:
  - Loading: Skeleton
  - Empty: Explanation + suggested action
  - Error: Error message + retry
  - Success: Data
- **Apply to:** Companies (already partially done), Expiry, Search (add no-results), Today (add null-card explanations)
- **Verification:** Every screen handles all 4 states

### PR 1.3: Unified loading states on Today
- **Files:** `frontend/src/app/(app)/today/page.tsx`
- **Changes:** Instead of 7+ independent SWR skeletons, show a single unified briefing skeleton until all data loads
- **Verification:** No layout shift on Today page load

### PR 1.4: Navigation polish
- **Files:** `NavSidebar.tsx`, `TopNav.tsx`
- **Changes:**
  - Highlight active route
  - Add global search shortcut (Cmd+K / Ctrl+K pattern)
  - Ensure responsive mobile nav works (hamburger → slide-out)
- **Verification:** All routes accessible, active state visible, keyboard nav works

### PR 1.5: Responsive pass
- **Files:** Grid-heavy pages (Companies, Today, Search results)
- **Changes:** Ensure 1-col on mobile, 2-col on tablet, 3-4 col on desktop for card grids
- **Verification:** View at 375px, 768px, 1440px — no overflow, no collapsed layouts

---

## Phase 2 — Today Screen: The Daily Habit Loop (Sprint 3)

**Goal:** Make the Today screen the reason users come back. This is the retention engine.

### PR 2.1: Add "Since Your Last Visit" tracking
- **Backend:** Add `user.last_active_at` timestamp to UserModel. On Today page load, record the visit. Compare with previous visit.
- **Frontend:** Show "You last visited X hours/days ago. Here's what changed."
- **Verification:** After second visit, Today shows change since first visit

### PR 2.2: Daily Brief synthesis card
- **Frontend:** Top-of-page card that synthesizes the most important signals into a 3-4 sentence narrative
- **Backend:** Call existing `briefing.py` with persona weights, format output as the Daily Brief card
- **Schema:** "Good morning. 3 new signals in your watchlist. 14 patents approaching expiry in battery tech. Qualcomm filing activity up 40% in edge AI."
- **Verification:** Card renders with personalized content, every statement links to source

### PR 2.3: Redesign Today cards around Insight Card pattern
- **Apply `InsightCard` to:** FilingTrend, ExpiringOpp, NotablePatent, CompanyMove, PriorityWatch
- **Each card must have:** Title, why-it-matters (1 sentence), primary action (link), confidence indicator
- **Remove:** Raw z-scores and counts as primary display (demote to expandable detail)
- **Verification:** Every card on Today answers "why should I care?"

### PR 2.4: Post-onboarding persona nudge
- **Frontend:** If `user.persona` is null on Today, show a non-intrusive banner: "Personalize your briefing — set your focus in 30 seconds"
- **Verification:** Banner appears for users who skipped onboarding, links to persona setup

---

## Phase 3 — Patent Intelligence (Sprint 4) ✅ SHIPPED (2026-06-14)

**Goal:** Make patent detail pages convert raw data into perceived commercial value.

### PR 3.1: Executive Summary section (above the fold) ✅
- **Frontend:** New `ExecutiveSummary` component at TOP of patent detail page
- **Contains:** Title, assignee, status badge, AI commercial summary, why-it-matters, expiry estimate, opportunity score badge, primary CTA (Save/Follow), secondary CTA (Ask AI/Share)
- **Verification:** Scrolling is NOT required to understand the patent's value

### PR 3.2: Restructure patent detail sections ✅
- **Reorder panels into logical groups:**
  - **Above fold:** Executive Summary
  - **Tabs (6):** Overview, Commercial (WhyNow, OpportunityNarrative, UsageSignals, Family), Claims, Citations, Legal/Expiry, Similar
- **Collapse:** DataCompleteness panel into footer
- **Verification:** Tab navigation groups content sensibly, critical info is above the fold

### PR 3.3: Search page improvements ✅
- **Frontend:** Replaced inline header with PageHeader
- **Frontend:** No-results recovery uses EmptyState with mode-specific suggestions
- **Deferred:** filter chips, saved searches, sort dropdown (backend endpoint work needed)
- **Verification:** No-results state provides actionable next steps

### PR 3.4: Patent card improvements ✅
- **Frontend:** Added optional save/bookmark button to PatentCard with stopPropagation
- **Deferred:** Quick-preview drawer (requires side-panel infrastructure)
- **Verification:** Save button works inside Link wrapper, accessible

---

## Phase 4 — Company Intelligence (Sprint 5) ✅ SHIPPED (2026-06-14)

**Goal:** Make company pages feel like commercial intelligence products.

### PR 4.1: Company page enrichment ✅
- **Backend:** Added top inventors query to company profile endpoint
- **Frontend:** Company detail page redesigned with portfolio summary, technology focus, top inventors, expiry exposure card
- **Verification:** Page shows portfolio composition, tech concentration, inventor roster, and expiry risk — not just a patent list

### PR 4.2: Follow company infrastructure ✅
- **Backend:** Wired `follow_company.py` to API: GET/POST/DELETE `/suppliers/follow/{name}`, GET `/suppliers/follows`
- **Frontend:** Follow/unfollow button on company detail page with live SWR state
- **Verification:** Button toggles between "Follow company" and "Following", persists server-side

### PR 4.3: Company "What Changed" module ⬜
- **Deferred:** Filing delta comparison requires period-over-period snapshot infrastructure. Documented as follow-up in docs/company-intelligence.md.
- **Verification:** N/A — deferred

### Deferred Search items (from Sprint 4.5)
| Item | Reason | Priority |
|------|--------|----------|
| CPC/assignee filter dropdowns | Needs facet aggregation from backend | P2 |
| Date range picker | Most users search by topic | P3 |
| Patent preview drawer | Side-panel infrastructure needed | P2 |
| Save/unsave on result cards | ✅ Completed in Sprint 5 (commit bb8e477) | — |

---

## Phase 5 — Expiry Radar + Opportunity Workflows (Sprint 6)

**Goal:** Turn expiry data into actionable commercial opportunities.

### PR 5.1: Expiry Radar why-it-matters
- **Frontend:** Add commercial relevance explanation to each expiry card using Insight Card pattern
- **Backend:** Call `opportunity_narrative.py` to generate per-patent "why this expiry matters"
- **Verification:** Every expiry card show a why-it-matters sentence

### PR 5.2: Expiry filters + missing data explanation
- **Frontend:** Add company, theme, date-range filters
- **Frontend:** Empty state: explain WHY data is missing ("Expiry data is still being calculated...")
- **Verification:** Filters work, empty state is explanatory

### PR 5.3: Save/Export/Alerts on expiry cards
- **Frontend:** Add save to watchlist, export CSV, create alert per card
- **Backend:** Wire alert creation for expiry events
- **Verification:** Save/export/alert all work from expiry page

---

## Phase 6 — Retention & Feedback (Sprint 7)

**Goal:** Make the app sticky and collect user feedback.

### PR 6.1: Expand Watchlist
- **Frontend:** Add tabs for: Saved Patents, Followed Companies, Followed Themes, Saved Searches, Recently Viewed
- **Backend:** Endpoints for each entity type
- **Verification:** All watchlist tabs load correct data

### PR 6.2: Feedback widget
- **Frontend:** Lightweight feedback component on Today, Patent Detail, and Companies pages
- **Questions:** "Was this useful? What is missing? Report a data issue"
- **Backend:** Store feedback in DB (or log to structlog)
- **Verification:** Feedback submits and is logged

### PR 6.3: Activation event tracking
- **Backend:** Log events: `signup_completed`, `onboarding_completed`, `entity_followed`, `search_performed`, `search_saved`, `patent_opened`, `patent_saved`, `company_opened`, `expiry_opportunity_opened`, `daily_brief_opened`
- **Frontend:** Fire events via API calls or structlog
- **Define activation:** User follows ≥3 entities/themes, saves ≥1 search, opens ≥3 patent details
- **Verification:** Events appear in logs/admin dashboard

### PR 6.4: Analytics dashboard (admin)
- **Frontend:** Simple admin dashboard showing: signups/week, activation rate, DAU/WAU, popular routes
- **Backend:** Aggregate queries from event logs
- **Verification:** Dashboard renders with real data

---

## Future Phases (Post-Revamp)

Not in scope for the current revamp. Listed for awareness.

- **Alerts/notification center** — in-app notification bell, email digest opt-in
- **Email digest** — weekly personalized briefing via email
- **Report/export workflow** — PDF reports, batch export
- **Pricing plan boundaries** — feature gating visualization, upgrade prompts
- **Landing page redesign** — fresh value prop with screenshots and use cases
- **Performance optimization** — Core Web Vitals (LCP, INP, CLS), Lighthouse scores
- **Accessibility pass** — WCAG 2.2 AA: keyboard nav, focus states, contrast, screen readers
- **Blog post ID replacement** — replace placeholder patent IDs in posts 3, 4, 5

---

## Estimated Timeline

| Phase | Sprints | PRs | Focus |
|-------|---------|-----|-------|
| Phase 0 — Stabilization | 1 | 6 | Fix broken things |
| Phase 1 — UX Foundation | 1 | 5 | Coherent feel |
| Phase 2 — Today screen | 1 | 4 | Retention engine |
| Phase 3 — Patent intelligence | 1 | 4 | Value perception |
| Phase 4 — Company intelligence | 1 | 3 | Commercial depth |
| Phase 5 — Expiry Radar | 1 | 3 | Opportunity workflows |
| Phase 6 — Retention | 1 | 4 | Stickiness + feedback |
| **Total** | **7 sprints** | **29 PRs** | |

---

## Acceptance Criteria for Revamp Completion

- [ ] All main screens have a clear purpose, visible on first load
- [ ] All main screens handle loading, empty, error, and success states
- [ ] Build passes (`next build`, `tsc --noEmit`)
- [ ] Lint passes with 0 errors (`npm run lint`)
- [ ] All tests pass (`npm test`, `pytest`)
- [ ] Companies page shows real country/entity coverage data
- [ ] Today screen shows personalized, synthesized intelligence
- [ ] Patent detail pages have executive summary above the fold
- [ ] Every insight card answers "why should I care?"
- [ ] Users can save/follow patents, companies, and themes
- [ ] Expiry Radar explains commercial relevance per patent
- [ ] Activation events are tracked
- [ ] Feedback widget exists on main surfaces
- [ ] Mobile/responsive layout works on main routes
- [ ] No screen shows empty/broken state without explanation

---

## Issue Template

All implementation issues should follow this format:

```
Title: [Screen] — [What's wrong]
Area: [Frontend/Backend/Both]
Screen/Route: [URL]
User Impact: [What user sees/feels]
Business Impact: [Why it matters commercially]
Severity: P0/P1/P2/P3
Evidence: [Screenshot, API response, log]
Root Cause: [If known]
Proposed Fix: [What to change]
Acceptance Criteria:
  - [ ] [Specific, verifiable conditions]
Test Plan:
  - [ ] [How to verify the fix]
Related Files: [List]
Related API Endpoints: [List]
Related DB Tables: [List]
```
