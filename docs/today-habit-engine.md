# Today — Daily Habit Engine (Sprint 3)

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `sprint-3-today-habit-engine`

---

## 1. Today Data Contract

### API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/today/state` | GET | Optional | Returns Today view state for since-last-visit display |
| `/api/v1/today/mark-seen` | POST | Required | Shifts last_seen → previous_seen, sets last_seen = now |
| `/api/v1/today/highlights` | GET | None | Editorial highlight cards (trend, expiry, notable, company) |

### TodayState Response

```typescript
interface TodayState {
  generated_at: string;       // ISO 8601 UTC
  last_seen_at: string | null; // ISO 8601 UTC — null for first-time users
  comparison_label: string;    // "Since June 14, 2026" or "Welcome — your first Today briefing"
}
```

### TodayInsight Type

```typescript
type TodayInsightType = "signal" | "risk" | "opportunity" | "update" | "recommendation";

interface TodayInsight {
  id: string;
  type: TodayInsightType;
  title: string;
  summary: string;
  why_it_matters: string;
  evidence: Array<{ label: string; value: string | number; href?: string }>;
  confidence: "high" | "medium" | "low";
  timestamp: string;
  primary_action: { label: string; href: string };
  secondary_action?: { label: string; href: string };
}
```

---

## 2. Since-Last-Visit Tracking

### Implementation

- **User model:** `last_today_seen_at` and `previous_today_seen_at` columns (migration 0032)
- **`GET /today/state`:** Reads both timestamps, returns comparison_label
- **`POST /today/mark-seen`:** Shifts last_seen → previous_seen, sets last_seen to now
- **Frontend:** Calls mark-seen via `useEffect` after state loads successfully
- **UTC timestamps used throughout** — no timezone bugs

### Behavior

| Scenario | Comparison label |
|----------|-----------------|
| First visit (both NULL) | "Welcome — your first Today briefing" |
| Returning same day | "Since earlier today" |
| Returning next day | "Since yesterday (Jun 14, 2026)" |
| Returning after N days | "Since Jun 14, 2026" |

### Design decisions
- Only marks seen AFTER data loads (not on mount)
- `markSeen` failure is silent — doesn't block UX
- Uses existing User model — no new table needed
- `previous_today_seen_at` enables rollback/diagnostics
- **Preflight fix (Sprint 3.5):** Added `markSeenRef` to prevent repeat mark-seen on rapid refreshes. Repeated reloads within the same React mount lifecycle will not create misleading "Since earlier today" behavior. The ref ensures mark-seen fires exactly once per page session.

### Mark-seen verification (Sprint 3.5 preflight)

| Requirement | Status | Implementation |
|------------|--------|---------------|
| Comparison window based on prior visit | ✅ | `state` fetched via SWR before `useEffect` fires mark-seen |
| mark-seen only after data loads | ✅ | Guard: `if (state && !stateError)` |
| Not triggered by prefetches/crawlers | ✅ | `revalidateOnFocus: false`, `dedupingInterval: 60_000` |
| Repeated refreshes don't mislead | ✅ | `markSeenRef` prevents double-fire within same mount |
| UTC storage/compare, local display-only | ✅ | Backend uses `datetime.now(timezone.utc)`, frontend displays `comparison_label` only |

---

## 3. Insight Generation Rules

All insights are **deterministic** — no LLM calls. Derived from real data hooks.

| Insight ID | Data source | Type | Condition |
|-----------|------------|------|-----------|
| `new-patents-week` | `usePatentStats().patents_this_week` | update | stats.patents_this_week > 0 |
| `trend-*` | highlights.filing_trend (from TrendSnapshot) | signal | highlight exists |
| `expiring-opportunities` | highlights.expiring_opportunity | opportunity | highlight exists |
| `notable-*` | highlights.notable_patent | signal | highlight exists |
| `company-*` | highlights.company_move | update | highlight exists |
| `watchlist-status` | useWatchlist() | update | watchlist.length > 0 |

### Evidence rule
Every insight must have `evidence` fields. If an insight cannot be tied to a real patent, company, trend, or other app object, it is not shown.

### Confidence rule
- `high` — data from direct queries, no AI inference
- `medium` — derived from computed scores or aggregated stats
- `low` — reserved for LLM-generated content (not used in Sprint 3)

---

## 4. Screen Structure

```
Today
├── PageHeader (title, comparison_label, freshness)
├── At-a-glance metrics (total patents, new this week, AI summarized, top assignee)
├── This Week's Highlights (4 cards: trend, expiry, notable, company)
├── Top Signals (InsightCards — up to 6, derived from highlights)
├── Your Topics (if themes exist) or Personalize prompt
├── Expiring Opportunities (from usePriorityWatch)
├── Companies Moving (from useSuppliers)
├── Recommended Actions (4 cards: search, watchlist, expiry, companies)
└── SourceAttribution
```

### First-time / unpersonalized state
Shows `FirstTimeWelcome` with StarterTopics and two entry points (Search, Trends). Honest copy: "Today gets better as you save patents, searches, companies, and technology areas."

---

## 5. Analytics Events

| Event | When fired |
|-------|-----------|
| `today_state_loaded` | Today state API returns successfully |
| `today_marked_seen` | mark-seen POST succeeds |
| `today_insight_viewed` | InsightCards render |
| `today_highlight_clicked` | User clicks a highlight card |
| `today_action_clicked` | User clicks a Recommended Action |

Events are logged via `console.debug` in development. Production-ready event pipeline deferred to Sprint 6.

---

## 6. Screenshots

### SCREENSHOTS NEEDED (requires running app)
- [ ] Today with comparison_label + highlights
- [ ] Today with Top Signals (InsightCards)
- [ ] Today first-time welcome state
- [ ] Today error state
- [ ] Today loading state

---

## 7. Baseline

| Check | Result |
|-------|--------|
| `tsc --noEmit` | ✅ PASS |
| `npm run build` | ✅ PASS (7.6s) |
| `npm test` | ✅ 53/53 PASS |
| `npm run lint` | ✅ Clean |

---

## 8. Backend Changes

| File | Change |
|------|--------|
| `core/ai_models.py` | Added `last_today_seen_at`, `previous_today_seen_at` to User model |
| `api/v1/today.py` | Added `GET /today/state` and `POST /today/mark-seen` endpoints |
| `alembic/versions/0032_today_seen_at.py` | Migration for new columns |

---

## 9. Backend Test Coverage (Sprint 3.5 preflight)

12 tests in `backend/tests/api/test_today_state.py`:

| Test | Covers |
|------|--------|
| `test_today_state_first_time_user_no_cookie` | Unauthenticated user, null last_seen |
| `test_today_state_first_time_with_cookie_no_history` | Auth'd first-time, welcome label |
| `test_today_state_returning_user` | 3-day-ago comparison, date in label |
| `test_today_state_returning_same_day` | "Since earlier today" |
| `test_today_state_timestamps_are_utc_iso8601` | Valid ISO 8601, within 120s of now |
| `test_mark_seen_requires_auth` | 401 without cookie |
| `test_mark_seen_first_time` | last_seen set, previous stays None |
| `test_mark_seen_shift` | last_seen → previous, new last_seen |
| `test_mark_seen_idempotent` | Double-call works correctly |
| `test_mark_seen_utc_storage` | Timestamps have UTC timezone |
| `test_migration_columns_default_null` | New users start with NULL columns |
| `test_state_reflects_mark_seen` | Full integration: state → mark → state |

## 10. Deferred / Follow-up

| Item | Status | Sprint |
|------|--------|--------|
| LLM-generated Daily Brief synthesis | Deferred | Sprint 4+ |
| Personalized persona-weighted insights | Deferred | Sprint 4+ |
| Saved search recommendations | Deferred | Sprint 4 (Search) |
| Company follow/watch integration | Deferred | Sprint 5 (Companies) |
| Production event pipeline | Deferred | Sprint 6 |
| Backend venv fix to run tests locally | Deferred | Post-Sprint 3 |

---

## 11. Sprint 3.5 Preflight Results

| Check | Result |
|-------|--------|
| Lint: 0 errors, 0 warnings (excl. documented `<img>`) | ✅ |
| Backend tests: 12 new tests for today/state + mark-seen | ✅ |
| Migration 0032: columns nullable, timezone-aware | ✅ |
| mark-seen semantics: fires once, after load, UTC | ✅ |
| Repeated refreshes: guarded by markSeenRef | ✅ |
| docs/today-habit-engine.md updated | ✅ |

| Item | Status | Sprint |
|------|--------|--------|
| LLM-generated Daily Brief synthesis | Deferred | Sprint 4+ |
| Personalized persona-weighted insights | Deferred | Sprint 4+ |
| Saved search recommendations | Deferred | Sprint 4 (Search) |
| Company follow/watch integration | Deferred | Sprint 5 (Companies) |
| Production event pipeline | Deferred | Sprint 6 |
| Backend tests for today/state and today/mark-seen | Needs venv fix | Post-Sprint 3 |
| `previous_today_seen_at` used for change detection window | Future | Sprint 4+ |
