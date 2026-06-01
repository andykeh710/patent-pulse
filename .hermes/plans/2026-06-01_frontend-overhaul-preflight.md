# Frontend Overhaul — Preflight Report

**Date:** 2026-06-01
**Reporter:** Hermes
**Status:** Complete — awaiting Andy's review and go-ahead for Phase A

Phase 0 preflight report resolving all open questions from the design spec §11.1 before Phase A implementation begins.

---

## 1. Route inventory

All 27 page routes listed with spec cross-reference:

| Route | File | In Spec? |
|---|---|---|
| `/` | `(marketing)/page.tsx` | ✅ |
| `/today` | `(app)/today/page.tsx` | ✅ |
| `/patents` | `(app)/patents/page.tsx` | ✅ |
| `/patents/:id` | `(app)/patents/[id]/page.tsx` | ✅ |
| `/trends` | `(app)/trends/page.tsx` | ✅ |
| `/trends/:surface/:key` | `(app)/trends/[surface]/[key]/page.tsx` | ✅ |
| `/expiry` | `(app)/expiry/page.tsx` | ✅ |
| `/opportunity` | `(app)/opportunity/page.tsx` | ✅ |
| `/themes` | `(app)/themes/page.tsx` | ✅ |
| `/themes/:id` | `(app)/themes/[id]/page.tsx` | ✅ |
| `/companies` | `(app)/companies/page.tsx` | ✅ |
| `/companies/:name` | `(app)/companies/[name]/page.tsx` | ✅ |
| `/search` | `(app)/search/page.tsx` | ✅ |
| `/watchlist` | `(app)/watchlist/page.tsx` | ✅ |
| `/account` | `(app)/account/page.tsx` | ✅ |
| `/account/billing` | `(app)/account/billing/page.tsx` | ✅ |
| `/admin` | `(app)/admin/page.tsx` | ✅ |
| `/admin/data-health` | `(app)/admin/data-health/page.tsx` | ✅ |
| `/admin/ai-runs` | `(app)/admin/ai-runs/page.tsx` | ✅ |
| `/login` | `(auth)/login/page.tsx` | ✅ |
| `/login/verify` | `(auth)/login/verify/page.tsx` | ✅ |
| `/unsubscribed` | `(auth)/unsubscribed/page.tsx` | ✅ |
| `/about` | `(marketing)/about/page.tsx` | ✅ |
| `/contact` | `(marketing)/contact/page.tsx` | ✅ |
| `/pricing` | `(marketing)/pricing/page.tsx` | ✅ |
| `/privacy` | `(marketing)/privacy/page.tsx` | ✅ |
| `/terms` | `(marketing)/terms/page.tsx` | ✅ |

**Mismatches:**
- `/trends/:surface` (e.g., `/trends/cpc` as intermediate drilldown) — **MISSING.** Only `/trends/:surface/:key` exists. Spec §6 references `/trends/[surface]` as a distinct page. The frontend hook `useTrends.ts` calls `trendsApi.list(surface)` which likely maps to the same list endpoint. No file is missing that blocks Phase A; this is a spec documentation gap.

**Verdict:** All spec-referenced routes exist. One intermediate trends drilldown page is absent but not a blocker.

---

## 2. Route naming resolution (/themes vs /topics)

Decision register §2.1 #2: UI label is "Topics" everywhere; route URL stays `/themes` in V1.

**Scan findings:** Zero `/topics` route references in the entire frontend codebase. All internal references use `/themes` as the URL path.

**Labels to update in Phase A:**

| File | Current | Change to |
|---|---|---|
| `NavSidebar.tsx:40` | `label: "Topics"` | Already says Topics ✅ |
| `StarterTopics.tsx` | Various | Already says Topics ✅ |
| `(app)/themes/page.tsx` | Page title | Verify "Topics" is used |
| `(app)/themes/[id]/page.tsx` | Page title | Verify "Topics" is used |

The nav already says "Topics" in the sidebar. Most labels are already correct from the rebrand pass. Phase A should audit remaining labels and ensure consistent "Topics" in UI while keeping `/themes` URLs.

**Verdict:** No route rename needed. Minor label audit in Phase A.

---

## 3. /today vs /dashboard references

Decision register §2.1 #1: `/today` is canonical. `/dashboard` was deleted in earlier UX sprint.

**Scan findings:**
- Frontend: Zero `/dashboard` references ✅
- Backend: Zero `/dashboard` references ✅
- Email templates: Zero `/dashboard` references ✅
- Docs/plans: Zero `/dashboard` references ✅

**Verdict:** Clean — no `/dashboard` references remain anywhere. `/today` is the canonical command center.

---

## 4. Working tree state

```
Modified (not staged):
  M backend/app/ai/llm_client.py         # DeepSeek provider support
  M backend/app/api/v1/admin.py           # LLM provider admin toggle
  M backend/app/api/v1/auth.py            # Magic link verify fix
  M backend/app/config.py                 # DeepSeek settings
  M backend/app/core/ai_models.py         # User ID/display_name fixes
  M frontend/src/app/(app)/patents/[id]/page.tsx  # Patent figures iframe
  M frontend/src/app/(auth)/login/verify/page.tsx # Auth verify fix
  M frontend/src/components/ui/SourceAttribution.tsx # Nested <a> fix
  M frontend/src/lib/api.ts               # Verify API fix

Untracked:
  .hermes/plans/2026-06-01_frontend-overhaul-preflight.md  (this report)
  backend/uv.lock
  dpa-2026-05-31.pdf
```

**BLOCKER:** 9 modified files from the deployment session are uncommitted. Andy must commit these before Phase A begins so the working tree is clean and Hermes works from a known state.

**Branch:** `main` is up to date with `origin/main` (commit `a71a69e`).

---

## 5. Screenshot capability

- Playwright: **NOT installed**
- Puppeteer: **NOT installed**
- Headless Chrome/Chromium: **NOT on host**

**Verdict:** No headless browser available. Visual verification during phase gates will be done via HTML structural observation (curl + grep DOM structure). Do NOT fabricate visual descriptions. If screenshots are needed for the design review, Andy should install Playwright on the host (`npx playwright install chromium`).

---

## 6. /companies/[name] 500 reproduction

The design spec §2.1 decision 8 flags this as a V1 blocker.

**Reproduction attempt:**

- Backend endpoint: `/api/v1/suppliers/profile/{name}` (not `/api/v1/companies/{name}`)
- Test: `curl http://localhost:8000/api/v1/suppliers/profile/SAMSUNG%20ELECTRONICS%20CO%20LTD`
- Result: **HTTP 200** — full company profile returned (1,152 patents, supplier_score 88.52, top CPCs, recent patents)

The backend endpoint works correctly. The 500 error reported may occur:
1. When the frontend's API proxy (`rewrites()` in `next.config.ts`) fails to route the request
2. When URL encoding of company names with special characters fails
3. On the frontend rendering side (React component crash)

**Frontend route:** `/companies/[name]` exists and uses `useSuppliers().profile(name)` hook. Needs to be tested in-browser with a real company name. The backend data is healthy.

**Verdict:** Backend is healthy. The 500 is likely a frontend proxy/rendering issue, not a backend data bug. Phase B should start by curling the frontend directly and examining the Next.js error overlay.

---

## 7. Existing component audit

**UI components** (`frontend/src/components/ui/`):
`Badge`, `Button`, `EmptyState`, `FreshnessBanner`, `Skeleton`, `SourceAttribution`, `Spinner`, `StarterTopics`

**Patent components** (`frontend/src/components/patents/`):
19 components including `AISummaryPanel`, `WhyNowPanel`, `ClaimsPanel`, `OpportunityBreakdown`, `PatentCard`, `PatentDetailTabs`, `OpportunityScoreBadge`, `RiskFlagsBadge`, etc.

**Cross-reference against spec §9.1 new components:**

| Proposed Component | Status | Action |
|---|---|---|
| `Card` | **NEW** | Create in Phase A |
| `StatTile` | **NEW** | Create in Phase A |
| `BriefingItem` | **NEW** | Create in Phase A |
| `Counter` | **NEW** | Create in Phase A |
| `Pill` | **NEW** — replaces ad-hoc chip code | Create in Phase A |
| `Button` | **EXISTS** — audit for dark theme | Refactor in Phase A |
| `LiveIndicator` | **NEW** | Create in Phase A |
| `SectionHeader` | **NEW** | Create in Phase A |
| `PersonaWizard` + steps | **NEW** | Create in Phase C |
| `FollowButton` | **NEW** | Create in Phase B |
| `StatsRow` / `BriefingFeed` / widgets | **NEW** | Create in Phase A/B |
| `PatentDetailHeader` / tabs | **NEW** | Create in Phase E |

No naming collisions — none of the proposed names overlap with existing components.

---

## 8. New dependencies required

**Already present:**
- `next` 15.1 ✅
- `swr` 2.2.5 ✅ (data fetching)
- `date-fns` 4.1.0 ✅ (relative timestamps "2h ago")
- Tailwind CSS with custom animations ✅

**Needed (no install required):**
- `next/font/google` — Geist Sans + Geist Mono. Part of Next.js, no npm install. Add font loader to `layout.tsx`.

**No new packages needed.** All V1 requirements are met with existing dependencies plus Next.js built-in font support.

---

## Summary

**8 findings at a glance:**

1. **Routes:** 26/27 spec routes exist. `/trends/:surface` intermediate page absent — not a blocker.
2. **Topics/Themes:** Zero `/topics` URL references. UI labels mostly say "Topics" already. Minor audit in Phase A.
3. **Dashboard:** Zero `/dashboard` references anywhere. Clean removal. ✅
4. **Working tree:** 9 modified files uncommitted — **BLOCKER.** Andy must commit before Phase A.
5. **Screenshots:** No headless browser. Visual verification via curl+inspect only. Andy: install Playwright if needed.
6. **Companies bug:** Backend healthy (HTTP 200). Likely frontend proxy/rendering issue. Phase B starts here.
7. **Components:** 8 new primitives needed, none collide with existing. All net-new.
8. **Dependencies:** Zero new packages needed. Geist via next/font/google (built-in).

**Phase A is BLOCKED** — reason: 9 uncommitted modified files from the deployment session. Andy must commit these to clean the working tree.

**Andy decision points:**
- Commit the 9 modified files (production bugfixes + DeepSeek integration)
- Confirm screenshot strategy (install Playwright or accept curl+inspect verification)
- Review `/companies/:surface` route gap (intentional? add intermediate page?)

Once working tree is clean and decisions are confirmed, Phase A is GO.
