# Patent Pulse V1 Roadmap — Updated May 21, 2026

## Goal

Transform Patent Pulse from an internal/demo analyst tool into a polished, useful, sellable patent intelligence product. Defer auth/billing infrastructure. Focus on making the application genuinely valuable before gating it.

## Current State (verified via code audit today)

**Stats:** ~13 DB tables, ~50k patents, ~30.5k summarized, ~2.4k trend snapshots
**Stack:** Next.js 15 + FastAPI + Postgres/pgvector + Redis/Celery, Docker Compose (6 services)
**Pages:** 14 pages (including /about, /companies/[name], /admin/ai-runs)

---

## Phase 0 — Harden Current Product

**Goal:** Make every existing page reliable, honest, and polished.

### 0.1 Duplicate-click protection ✅ DONE
All 4 AI panels (WhyNow, OpportunityNarrative, TrendSnapshot, AssigneeIntelligence) use `useAsyncAction` hook with ref-based guard — no race condition possible even on rapid clicks. Watchlist toggle has `disabled` guard. AI Runs page has similar patterns.

### 0.2 Freshness indicators ⚠️ PARTIAL — 4/5 pages done
`FreshnessBanner` component exists, backed by `GET /api/v1/patents/freshness` endpoint.
- Dashboard ✅
- Opportunity ✅
- Expiry ✅
- Trends ✅
- Patent detail ❌ MISSING (was in the original spec)
- Others (patents list, suppliers, etc.) were not in spec but could benefit

### 0.3 External patent links ✅ DONE
`ExternalPatentLinks` component renders on patent detail. Links to USPTO/Google Patents/Espacenet.

### 0.4 Claims section ✅ DONE
`ClaimsPanel` renders as a tab on patent detail page.

### 0.5 URL state for filters ✅ DONE
All 5 specified pages sync filter state to URL params:
- Opportunity: tab, sort, all 6 filters, page ✅
- Expiry: days_ahead, industry, time_horizon, sort, page ✅
- Patents: sort_by, sort_order, page ✅
- Search: q, mode, page ✅
- Trends: view, surface, cliff_window ✅
Filters are bookmarkable/shareable. Additional pages (suppliers, watchlist, themes) don't need it (mostly static views).

### 0.6 Rename Suppliers to Companies ⚠️ PARTIAL
- Nav label: "Companies" ✅
- Page heading: "Companies / Assignees" ✅
- Route: still `/suppliers` ❌ (should be `/companies`)
- Directory: still `app/suppliers/` ❌
- Company detail links back to `/suppliers` ❌
- Backend endpoint: `/api/v1/suppliers/` (acceptable for now — internal API)

### 0.7 Error and empty states ✅ MOSTLY DONE
`EmptyState` and `ErrorState` components exist and are used.
- Patents list: EmptyState + ErrorState ✅
- Patent detail: loading skeleton, not-found, per-tab empty states ✅
- Opportunity: loading skeleton, empty state with guidance ✅
- Expiry: loading/empty coverage (inline) ✅
- Search: loading, empty state, per-mode guidance ✅
- Trends: per-view loading, empty states ✅
- Watchlist: loading, empty state with CTA ✅
- Themes: loading, empty state with CTA ✅
- Suppliers: has summary loading cards ✅
- Company profile: loading, error/not-found ✅
- Dashboard: needs empty state audit (very data-dependent)
- A minor consistency pass could help (move some inline empty states to the shared component), but functionally covered.

### 0.8 V1 Limitations page ✅ DONE
`/about` page with full caveats, "About / Limitations" in nav.

---

## Phase 1 — Patent Credibility Features ✅ SUBSTANTIALLY DONE

This phase was executed ahead of schedule, in parallel with Phase 0.

### 1.1 Tabbed layout ✅ DONE
7 tabs on patent detail: Overview, Claims, Opportunity, Similar, Family, Citations, Legal/Expiry.

### 1.2 Family viewer ✅ DONE
FamilyTab shows members, empty state, legal caveats.

### 1.3 Citations tab ✅ DONE
CitationsTab shows backward citations with Google Patents links, empty state.

### 1.4 Similar patents ✅ DONE
SimilarTab uses semantic API, shows similarity %, handles embedding-missing errors.

### 1.5 Legal / Expiry tab ✅ DONE
LegalExpiryTab shows status, confidence, dates, amber warning box.

### 1.6 Company / Assignee pages ✅ DONE
`/companies/[name]` page exists with profile, stats, recent patents, CPC breakdown.

### 1.7 Source confidence badges ✅ PARTIAL
`AISourceFooter` component exists for AI-generated content. Confidence badges (LegalConfidenceBadge, RiskFlagsBadge) used on patent cards. Could be more thoroughly wired — low priority.

---

## Phase 0 Closure Plan (what remains)

Three items to close Phase 0 completely:

1. **0.2 — Add FreshnessBanner to patent detail page** (5 min)
   - Import FreshnessBanner in `/patents/[id]/page.tsx`
   - Add `<FreshnessBanner show={["patents", "summaries"]} className="mb-4" />` below the header

2. **0.6 — Rename Suppliers route** (10 min)
   - Move `app/suppliers/page.tsx` → `app/companies/page.tsx`
   - Update nav href from `/suppliers` to `/companies`
   - Update `/companies/[name]/page.tsx` back-link from `/suppliers` to `/companies`
   - Add redirect from `/suppliers` to `/companies` in next.config (optional, nice to have)

3. **0.7 — Final consistency pass** (15 min)
   - Audit dashboard for empty/error states
   - Ensure every page has: loading state, empty state, error state with retry

After Phase 0 closure: proceed to Phase 2 (Navigation Rebuild + Today Page) per original plan.

---

## Phase 2 — Navigation Rebuild and Today Page (next after Phase 0)

**Goal:** Transform nav and landing page from stats dashboard to editorial product experience.

### 2.1 New navigation structure
- Reorganize sidebar:
  1. Today (new, replaces dashboard)
  2. Opportunities
  3. Trends
  4. Expiring Patents
  5. Topics (new, placeholder — full topic system comes in Phase 3)
  6. Companies (renamed from suppliers)
  7. Search
  8. Watchlist
  9. Content Studio (placeholder, Phase 4)
- Remove or relegate: Dashboard, Themes (admin-only for now), Admin behind separator

### 2.2 Today page (editorial dashboard)
- Replace stats dashboard with editorial layout:
  - **Your Patent Pulse**: topic updates, new matches (placeholder)
  - **Top Opportunities**: top 5 scored patents with Why Now snippets
  - **Emerging Trends**: top 5 hot trends with context
  - **Expiring Opportunities**: top 5 expiring with revival potential
  - **Companies Moving**: top 5 assignees by recent activity
  - **System Freshness**: last ingest, last computation, next scheduled

### 2.3 Responsive polish
- Ensure all pages work on tablet/mobile widths
- Collapsible sidebar on small screens

---

## Phase 3 — User-Created Topics

Build topic CRUD, matching, and topic detail pages. Core retention mechanic.

## Phase 4 — Content Studio / LinkedIn Radar

Content generation, draft management, content export.

## Phase 5 — Exports

Markdown/CSV/JSON export for patents, lists, trends, companies.

## Phase 6 — Search and Filtering Depth

Date range, assignee, CPC filters. Saved searches (localStorage).

## Phase 7 — Newsletter Preview

Weekly digest rendering, topic-scoped newsletters. No email delivery yet.

---

## Execution Status

| Phase | Status | Effort |
|-------|--------|--------|
| 0     | 90% — 3 items remain | ~30 min |
| 1     | 95% — substantially done | Done |
| 2     | Not started | 3-4 days |
| 3     | Not started | 5-7 days |
| 4     | Not started | 5-7 days |
| 5     | Not started | 3-4 days |
| 6     | Not started | 3-4 days |
| 7     | Not started | 3-4 days |

After V1 polish: auth, billing, quotas, email delivery, alerts, team features, reports.
