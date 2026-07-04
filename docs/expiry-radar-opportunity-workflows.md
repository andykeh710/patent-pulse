# Expiry Radar + Opportunity Workflows — Sprint 6

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-6-expiry-radar-opportunity-workflows`

---

## What Actually Shipped (Sprint 6)

| Deliverable | Status | Notes |
|------------|--------|-------|
| Expiry Radar UI layer | ✅ | why-it-matters, StatusBadge, FilterChips, EmptyState, horizon tabs |
| whyItMatters() copy on cards | ✅ | Deterministic — no LLM, derived from score/usage/window/family fields |
| StatusBadge integration | ✅ | Replaces inline colored spans |
| FilterChips | ✅ | Active filters with remove + clear-all |
| EmptyState | ✅ | Per-section via ExpiryRadarSection |
| Watchlist save integration | ✅ | Bookmark button on cards, useWatchlist + addToWatchlist/removeFromWatchlist |
| Save error handling | ✅ | try/catch in handleToggleSave (preflight fix) |
| Horizon tabs | ✅ | Quick-filter: Expired, 0-6mo, 6-12mo, 12-24mo, 24-36mo, All |
| Legal caveat rewrite | ✅ | Compact, mentions term adjustments, continuations, jurisdiction rules |
| CSV export | ✅ | Existing — unchanged, verified working |
| ExpiryOpportunity TS contract | ✅ | Full type with score_components, evidence, actions |

## What Did NOT Ship (Deferred)

| Item | Reason | Target |
|------|--------|--------|
| Full opportunity scoring model (backend) | Score computed at ingest by `expiry_assessments.py`, surfaced on cards. No new backend scoring infra built. | Existing |
| Durable expiry alerts | No alert infrastructure in place. Would need new model, endpoints, UI. | Sprint 7 |
| Opportunity detail drawer | No side-panel infrastructure. Cards link to patent detail for full view. | Future |
| Expiry workflow product events | No analytics/event layer implemented. console.debug available for dev. | Sprint 7 |
| Backend-backed assignee/topic filters | Backend filter params exist for CPC/assignee but no facet data API. | Future |
| Opportunity scoring explanation in UI | Score shown numerically on cards. Component breakdown not surfaced. | Future |
| Mobile layout verification | Responsive grids in place, not manually tested at 375px. | QA |

---

## 1. ExpiryOpportunity Data Contract

```typescript
type ExpiryWindow = "expired" | "0-6m" | "6-12m" | "12-24m" | "24-36m" | "36m+";

interface ExpiryOpportunity {
  id: string;
  patent_id: string;
  title: string | null;
  publication_number?: string;
  assignee?: string;
  legal_status?: string;
  estimated_expiry_date?: string;
  days_until_expiry?: number;
  expiry_window: ExpiryWindow;
  expiry_confidence: "high" | "medium" | "low" | "unknown";
  legal_caveat: string;
  technology_tags?: string[];
  opportunity_score?: number;
  score_components?: {
    expiry_proximity?: number;
    data_completeness?: number;
    commercial_relevance?: number;
    assignee_signal?: number;
    topic_signal?: number;
  };
  why_it_matters: string;
  evidence: Array<{ label: string; value: string | number; href?: string }>;
  primary_action: { label: string; href: string };
  secondary_actions?: Array<{ label: string; href?: string; action?: string }>;
}
```

Backend response: `PaginatedResponse<ExpiryItem>` with fields mapped via `expiryItemToCardProps()` in expiry/page.tsx.

---

## 2. Opportunity Scoring Model

**Deterministic — no LLM.** Score is computed at ingest by `expiry_assessments.py` and stored as `expiry_opportunity_score` on the patent record. Frontend derivation from available card data:

```
whyItMatters() derivation:
  IF expiryOpportunityScore >= 70 AND usageSignalCount > 0
    → "strong expiry opportunity score, N commercial usage signals, expiring within N days"
  IF expiryOpportunityScore >= 70
    → "strong expiry opportunity score, expiring within N days"
  IF usageSignalCount > 0 AND expiring within 90 days
    → "N commercial usage signals, expiring within 90 days"
  IF activeFamilyRisk
    → includes "active family members in other jurisdictions"
  ELSE null (no sentence shown)
```

Score display: numeric badging (green ≥70, amber ≥40, gray <40).

Evidence sources: opportunity score, usage signal count, days until expiry, family risk flag. No invented claims.

---

## 3. Expiry Estimate Caveats

- All expiry indicators are heuristic estimates from filing metadata
- Maintenance fees, patent term adjustments, terminal disclaimers, and jurisdictional rules may affect actual enforceability
- Active family members may exist in other jurisdictions even if the listed patent is expired
- Legal caveat banner displayed prominently on the Expiry Radar page
- Each card includes "Verify with official registers" + Google Patents link
- Status labels use explicit confidence: "Active (est.)", "Expiring Soon", "Lapsed (possible)", "Expired (confirmed)"

---

## 4. Screen Structure

```
Expiry Radar
├── PageHeader (title, description, freshness)
├── ExpirySummaryCards (total, by-status, by-confidence, family risk, high-opp)
├── Legal caveat banner (amber, non-dominant)
├── FilterBar (days ahead, status, confidence, family risk, sort)
├── FilterChips (active filters with remove + clear-all)
├── CSV Export button
├── Sections (7):
│   ├── Expiring Soon
│   ├── Recently Expired
│   ├── Likely Lapsed
│   ├── Revival Candidates (high opportunity score + expired)
│   ├── Patent Cliffs (concentration analysis)
│   ├── High-Opportunity Candidates
│   └── Active Family Risk
└── Each section: ExpiryRadarSection → ExpiryRadarCard[]
```

### ExpiryRadarCard structure

```
┌──────────────────────────────────────────────┐
│ [Save bookmark]                              │
│ Title (link to patent detail)                │
│ docId · assignee                             │
│                                              │
│ [StatusBadge] [ConfidenceBadge] [FamilyRisk] │
│ Expiry: date · N days remaining              │
│                                              │
│ Why this may matter: ...                     │  ← accent left border
│ Usage signals: N · ⚠ Self-cite              │
│                                              │
│ Source · Verify at Google Patents →          │
└──────────────────────────────────────────────┘
```

---

## 5. Filters

| Filter | Type | Backend param |
|--------|------|--------------|
| Days ahead | Select (90d/180d/1yr/2yr/5yr/10yr/All) | `days_ahead` |
| Expiry status | Select (Expiring/Expired/Lapsed/Active/Unknown) | `expiry_status` |
| Confidence | Select (Confirmed/High/Medium/Low) | `confidence` |
| Family risk | Checkbox | `active_family_risk` |
| Min opportunity score | URL param | `min_expiry_opportunity_score` |

All filters reflected in FilterChips. Clear-all resets all. State URL-backed via `syncURL()`.

---

## 6. Sort Options

| Option | Backend params |
|--------|---------------|
| Expiring soonest | `sort_by=expiry_urgency&sort_order=asc` |
| Highest expiry opp. | `sort_by=expiry_opportunity_score&sort_order=desc` |
| Highest opportunity | `sort_by=opportunity_score&sort_order=desc` |
| Highest confidence | `sort_by=confidence&sort_order=desc` |
| Recently assessed | `sort_by=recently_assessed&sort_order=desc` |
| Expiry date (asc) | `sort_by=expiry_date&sort_order=asc` |
| Expiry date (desc) | `sort_by=expiry_date&sort_order=desc` |

---

## 7. Actions

| Action | Implementation | Status |
|--------|---------------|--------|
| Save to watchlist | `addToWatchlist`/`removeFromWatchlist` with `mutateWatchlist` | ✅ |
| Open patent detail | Link to `/patents/{id}` | ✅ |
| CSV export | `CSVExportButton` component (existing) | ✅ |
| Create alert | Not implemented — needs alert infrastructure | ⬜ Sprint 7 |
| PDF report | Not implemented — needs report system | ⬜ Future |

---

## 8. States

| State | Implementation |
|-------|---------------|
| Loading | ExpiryRadarSection: 3 skeleton cards with animate-pulse |
| Empty (no data) | EmptyState: calendar icon, message, detail, no actions needed |
| Empty (filters too restrictive) | EmptyState suggests removing filters |
| Error | Not yet implemented — uses SWR error state |

---

## 9. Sprint 2 Components Used

| Component | Where |
|-----------|-------|
| `PageHeader` | Page title |
| `StatusBadge` | Expiry status + confidence badges on cards |
| `FilterChips` | Active filter display |
| `EmptyState` | Section empty states (via ExpiryRadarSection) |
| `SourceAttribution` | Patent office attribution on cards |

---

## 10. Baseline

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✅ PASS |
| `npm run build` | ✅ 7.6s |
| `npm run lint` | ✅ 2 documented `<img>` only |
| `npm test` | ✅ 53/53 |

---

## 11. Deferred / Follow-Up

| Item | Sprint |
|------|--------|
| Horizon tabs (0-6m, 6-12m, etc.) replacing section-based layout | Sprint 6.5 |
| Per-card alert creation | Sprint 7 (needs alert infra) |
| PDF/report export | Future |
| Company/theme filter dropdowns on Expiry Radar | Future |
| Opportunity detail drawer | Future (side-panel infra) |
| Backend tests for expiry endpoints | Post-venv-fix |

---

## 12. Open Ops/Product Follow-Ups

1. Run or verify production assignee backfill
2. Rotate production Postgres password safely
3. Add CPC/assignee facets to Search
4. Add date range picker to Search
5. Add patent preview drawer
6. Save/unsave on Search result cards ✅ (completed Sprint 5)
