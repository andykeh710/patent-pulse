# Patent & Search Intelligence — Sprint 4

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-4-patent-search-intelligence`

---

## 1. Patent Detail Information Architecture

### Before
```
Page
├── Breadcrumb
├── Title + Watchlist button + Score badges
├── Metadata row (number, office, status, confidence)
├── Risk flags
├── Citation counts
├── External links + Source attribution
├── Figures
├── DataCompleteness panel (prominent, collapsible)
├── FreshnessBanner
├── Tabs (8): Overview, Claims, Opportunity, Similar, Family, Citations, Legal, Usage
│   └── OverviewTab: Inventors, Summary, Tags, Abstract | DetailsPanel, Assignees
```

### After
```
Page
├── Breadcrumb
├── Risk flags
├── Figures
├── ExecutiveSummary (above the fold)
│   ├── Title, Assignee, Status, Expiry estimate
│   ├── AI commercial summary
│   ├── Why-it-matters sentence
│   ├── CTAs: Save to watchlist, Ask AI, Copy link
│   └── Score badges, Key dates, External links, Source
├── FreshnessBanner
├── Tabs (6): Overview, Commercial, Claims, Citations, Legal/Expiry, Similar
│   ├── OverviewTab: Inventors, Summary, Tags, Abstract, DetailsPanel, Assignees
│   └── CommercialTab: UsageSignals, Family, WhyNow, OpportunityNarrative,
│       LinkedInPost, TrendSnapshot, AssigneeIntelligence, Score breakdowns
└── DataCompleteness panel (footer, collapsed by default)
```

---

## 2. Search Changes

### Completed (Sprint 4)
- Replaced inline header with `PageHeader` component
- No-results state uses `EmptyState` with mode-specific suggestions

### Completed (Sprint 4.5)
- **Filters:** legal status dropdown (Granted/Published/Any)
- **Sort dropdown:** Relevance, Newest first, Oldest first, Expiring soonest
- **FilterChips:** visible active filters with remove + clear-all
- **URL state:** all filter/sort/mode state survives page reload via URL params
- **Saved searches:** full CRUD (create, list, open, delete) server-side
  - Model: `saved_searches` table (migration 0033)
  - Endpoints: `GET/POST/DELETE /api/v1/saved-searches`
  - Frontend: save input, list below search prompt, open restores full state
- **Backend:** search endpoint now supports `legal_status`, `sort_by`, `sort_order`
- **Result cards:** `PatentCard` with save button support

### Deferred
- CPC/assignee filter dropdowns (needs facet data from backend)
- Date range picker (low priority — most users search by topic)
- Summarized/has-figures filters (niche)
- Patent preview drawer (requires side-panel infrastructure)

---

## 3. PatentCard Changes

- New optional props: `isSaved`, `onToggleSave`
- Save/bookmark button in top-right corner with `stopPropagation`
- Works inside `<Link>` wrapper without navigation conflict
- Accessible: `aria-label`, `title`, keyboard-friendly

---

## 4. Empty-State Copy Guidelines

| Screen | Empty state message | Actions |
|--------|-------------------|---------|
| Search (hybrid) | "No patents matched across keyword and semantic indexes" | Try keyword, Browse all, Explore topics |
| Search (semantic) | "No patents were similar enough to your description" | Try rephrasing, Switch to keyword |
| Search (keyword) | "No patents matched your keywords" | Try different terms, Switch to semantic |
| Patent Detail (no summary) | Hides the summary text — no empty state needed | — |
| Patent Detail (no expiry) | Hides the expiry estimate — no empty state needed | — |
| Patent Detail (no figures) | Hides the figures section entirely | — |

---

## 5. Source-Grounding Rules

- Every insight on Today must be tied to a real patent, company, trend, or other app object
- Patent Detail ExecutiveSummary only shows data that exists (summary, why-now, expiry)
- If data is missing, the corresponding element is hidden — no placeholder text
- "Copy link" button copies the actual page URL
- AI summary source: `patent.summary.commercial_significance` from Anthropic Claude
- Why-it-matters source: `patent.why_now_text` from deterministic scoring + LLM

---

## 6. Mark-Seen Idempotency (Sprint 4.5 preflight)

### Issue
Client-side `markSeenRef` only prevents duplicates within one React mount. Hard browser reloads create new mounts, causing `markSeen` to fire on every reload and shift the comparison window forward each time.

### Fix
Server-side idempotency in `POST /today/mark-seen`: if the user's `last_today_seen_at` is within 5 minutes of the current time, return `{"status": "skipped"}` without updating. Hard reloads within a reasonable browsing session won't churn the comparison label.

### Behavior table
| Scenario | Frontend guard | Server guard | Result |
|----------|--------------|-------------|--------|
| First Today visit | — | last_seen is NULL → proceeds | Marked as seen |
| Switch tabs, return | markSeenRef prevents | — | Not called |
| Hard reload (within 5 min) | New mount → tries | 5-min window → skipped | Not shifted |
| Hard reload (after 5 min) | New mount → tries | Outside window → proceeds | Shifted |
| Next day visit | New mount → tries | Outside window → proceeds | Shifted, shows "Since yesterday" |

---

## 7. Screenshots

### SCREENSHOTS NEEDED
- [ ] Patent detail page with ExecutiveSummary visible
- [ ] Patent detail Overview tab
- [ ] Patent detail Commercial tab
- [ ] Patent detail with missing AI summary (summary not yet generated)
- [ ] Patent detail with missing expiry
- [ ] Search page with results
- [ ] Search page with no-results (EmptyState)
- [ ] Mobile (375px): patent detail, search

---

## 8. Baseline

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✅ PASS |
| `npm run build` | ✅ PASS |
| `npm run lint` | ✅ 0 errors, 0 warnings (excl. documented `<img>`) |
| `npm test` | ✅ 53/53 PASS |
| Backend tests (today_state) | ✅ 13 tests (including idempotency) |

---

## 9. Known Follow-Up

| Item | Sprint |
|------|--------|
| Search filter chips + sort dropdown | Sprint 4.5 |
| Saved searches data model + API | Sprint 4.5 |
| Quick-preview drawer for patent cards | Sprint 4.5 |
| PatentCard save integration in search/patents list pages | Sprint 4.5 |
| Company page follow/watch | Sprint 5 |
| Expiry Radar why-it-matters | Sprint 5/6 |
