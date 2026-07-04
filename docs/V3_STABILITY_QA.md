# V3 Stability QA

**Last updated:** 2026-06-22
**Branch:** `v3-6-production-stability`
**Health:** `overall=ok`, alembic=`0037`

Run this checklist on every deploy and before any user-facing launch.

---

## 1. Login / Magic Link

```bash
# Request link
curl -s -X POST http://<prod>:8080/api/v1/auth/request-link \
  -H 'Content-Type: application/json' \
  -d '{"email":"andy.keh@gmail.com"}'
```

| # | Check | Expected |
|---|-------|----------|
| 1.1 | Request returns ok | `{"ok":true}` |
| 1.2 | Email arrives (production) or backend log shows `DEV MAGIC LINK` (dev) | Link present |
| 1.3 | Open link in browser | Lands on `/onboarding` or `/today` |
| 1.4 | Refresh page | Still authenticated |
| 1.5 | Bad token | Shows "Sign-in failed" error |
| 1.6 | Expired token | Shows error (not blank page) |

## 2. Account / Preferences

| # | Check | Expected |
|---|-------|----------|
| 2.1 | `/account/preferences` loads | 200, all sections visible |
| 2.2 | Profile shows real email | Not placeholder text |
| 2.3 | Edit role/persona → Save | Persists after refresh |
| 2.4 | Edit use_case → Save | Persists after refresh |
| 2.5 | Edit industry → Save | Persists after refresh |
| 2.6 | Edit interests → Save | Persists |
| 2.7 | Preferences persist after logout/login | Values intact |

## 3. Today Page

| # | Check | Expected |
|---|-------|----------|
| 3.1 | `/today` loads | 200 |
| 3.2 | ForYouFeed renders | Cards with why-shown, scores |
| 3.3 | FreshnessBanner visible | Shows degraded/source-lag |
| 3.4 | Save/Useful/Not useful/Hide actions | Buttons present, call API |
| 3.5 | Hide action removes card | Card disappears |
| 3.6 | Platform Overview below For You | Generic stats secondary |
| 3.7 | Empty state (new user) | "Personalize your briefing" shown |

## 4. Patents

| # | Check | Expected |
|---|-------|----------|
| 4.1 | `/patents` loads | 200, patent list |
| 4.2 | Patent detail `/patents/{id}` | 200, shows title/assignee/abstract |
| 4.3 | Patent card shows opportunity score | Score visible |
| 4.4 | Patent card shows expiry estimate | "Estimated" label visible |
| 4.5 | Legal confidence badge | "estimated" shown |

## 5. Companies

| # | Check | Expected |
|---|-------|----------|
| 5.1 | `/companies` loads | 200 |
| 5.2 | No fake entity type badges | "Enrichment pending" or absent |
| 5.3 | No "Map-ready data" badge when 0% | Hidden or absent |
| 5.4 | Company names display correctly | No double-escaped ampersands |

## 6. Trends

| # | Check | Expected |
|---|-------|----------|
| 6.1 | `/trends` loads | 200 |
| 6.2 | Trend cards show Z-score | Numeric values |
| 6.3 | Trend detail loads | 200 |
| 6.4 | No duplicate CPC entries | Unique values |

## 7. Watchlist

| # | Check | Expected |
|---|-------|----------|
| 7.1 | `/watchlist` loads (auth required) | 200 |
| 7.2 | Tabs: Saved Patents, Followed Companies, Saved Searches | All three render |
| 7.3 | Save patent from patent detail | Appears in watchlist |
| 7.4 | Unsave removes from watchlist | Removed |

## 8. Admin — Source Health

| # | Check | Expected |
|---|-------|----------|
| 8.1 | API unauthorized | HTTP 401 |
| 8.2 | `/admin/source-health` loads (admin) | 200 |
| 8.3 | Provider status table | Shows uspto_bulkdata, uspto_odp |
| 8.4 | Manual retry buttons | Grant Week, App Week, Catch Up |
| 8.5 | Non-admin user | 403 or empty |

## 9. Topics / Themes

| # | Check | Expected |
|---|-------|----------|
| 9.1 | `/themes` loads | 200 |
| 9.2 | System themes have counts | AI/ML: 435, Medical: 465, Semi: 367 |
| 9.3 | `/topics` redirects to `/themes` | HTTP 301 |
| 9.4 | Create custom topic | Works, appears in list |
| 9.5 | Delete custom topic | Removes from list |

## 10. Expiry / Opportunities

| # | Check | Expected |
|---|-------|----------|
| 10.1 | `/expiry` loads | 200 |
| 10.2 | `/opportunity` loads | 200 |
| 10.3 | Expiry cards show warnings | "Verify with official registers" |
| 10.4 | No legal certainty overclaims | "estimated" labels |

## 11. Error States

| # | Check | Expected |
|---|-------|----------|
| 11.1 | API 500 → frontend error state | Error message, not blank |
| 11.2 | Loading state | Skeleton/spinner, not broken layout |
| 11.3 | Empty state (0 results) | Useful message, not "undefined" |
| 11.4 | Unauthenticated → login redirect | Redirect for protected pages |
| 11.5 | Network offline | Graceful degradation |

## 12. Cross-Cutting

| # | Check | Expected |
|---|-------|----------|
| 12.1 | Light mode readable | All text visible |
| 12.2 | Dark mode readable | All text visible |
| 12.3 | Mobile responsive | Cards stack, nav collapses |
| 12.4 | No console errors on page load | Clean browser console |

## QA Sign-Off

| Date | Tester | Result | Notes |
|------|--------|--------|-------|
| | | | |
