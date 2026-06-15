# Retention & Feedback — Sprint 7

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-7-retention-feedback`

---

## What Shipped

| Deliverable | Status |
|------------|--------|
| Enhanced Watchlist (3 tabs) | ✅ |
| FeedbackWidget (Today, Search) | ✅ |
| Feedback API (POST + admin GET) | ✅ |
| Activation state endpoint (GET /api/v1/activation-state) | ✅ |
| Alert intent model + endpoint | ✅ |
| Retention summary (admin-only) | ✅ |
| Analytics utility (trackEvent) | ✅ |
| Feedback migration (0034) | ⬜ needs creation |

---

## 1. Watchlist / Saved Workspace

**3 tabs:** Saved Patents, Followed Companies, Saved Searches.
PageHeader, LoadingState, EmptyState on all tabs. Empty states have contextual actions.

---

## 2. Feedback Model

```
POST /api/v1/feedback
GET /api/v1/feedback/admin (admin only)

Fields: route, surface, rating, message, object_type, object_id
```

Surfaces instrumented: Today, Search. Ready for Patent Detail, Companies, Expiry Radar, Watchlist.

---

## 3. Activation State

```
GET /api/v1/activation-state

Returns: has_opened_today, saved_patent_count, saved_search_count,
         followed_company_count, feedback_count, activated,
         strongly_activated, missing_steps
```

Activated: 2+ of [Today opened, saved patent, saved search, followed company, submitted feedback]
Strongly activated: 4+

---

## 4. Alert Intent

```
POST /api/v1/alert-intent

Types: saved_search_changes, company_expiry, expiry_window
Frequency: weekly (default)

Returns: {id, status: "intent_captured", note: "Alert delivery
         will be available in a future update."}
```

Honest — doesn't fake delivery. Stores intent server-side for when alert infra is ready.

---

## 5. Retention Summary

```
GET /api/v1/admin/retention (admin only)

Returns: total_users, today_views, saved_patents, saved_searches,
         feedback_count, top_feedback_surfaces
```

---

## 6. Product Event Contract (analytics.ts)

Non-blocking `trackEvent(name, payload)`. Console.debug for now. Ready for POST endpoint.

Events available: daily_brief_opened, today_insight_clicked, search_performed, patent_saved, feedback_submitted, activation_step_completed, etc.

---

## 7. Baseline

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✅ PASS |
| `npm run build` | ✅ 6.5s |
| `npm run lint` | ✅ 2 documented `<img>` |
| `npm test` | ✅ 53/53 |

---

## 8. Deferred

| Item | Reason |
|------|--------|
| Feedback migration (0034) | Needs table creation — deferred for deployment |
| Analytics dashboard UI | Needs event storage + aggregation |
| Alert delivery (not just intent) | Needs notification infra |
| FeedbackWidget on all surfaces | Only Today + Search instrumented |
| Activation nudge on Today/Watchlist | Backend ready, frontend component not built |
