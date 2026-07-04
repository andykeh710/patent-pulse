# Pre-Production QA Plan — Boris Feedback Stabilization

**Date:** 2026-06-15
**Branch:** sprint-boris-stabilization
**Target:** Merge into release/revamp-launch-validation after QA passes

---

## 1. Commits Included (3)

| Commit | Title | Files |
|--------|-------|-------|
| `9e2bbd0` | boris-feedback: P0/P1 fixes — theme label, nav scroll, landing sections, plan doc | 5 files: ThemeProvider, MarketingNav, landing page, boris-feedback-plan.md |
| `cff99ca` | fix: topic tracking — follow, create, delete with auth | 2 files: themes.py, themes/page.tsx |
| `ceff343` | fix: Today personalization — For You vs More Signals, topic-aware insights | 2 files: today/page.tsx, themes.py (import only) |

## 2. P0 Acceptance Criteria — Current State

| # | P0 Requirement | Status | Notes |
|---|--------------|--------|-------|
| 1 | Today starts with personalized For You | ✅ Partial | "For You" section shows watchlist items. Also shows if no personalization exists. Generic stats still appear in More Signals below. |
| 2 | Cards include "why for you" explanations | ⚠️ Gap | Watchlist cards show "From watchlist" evidence. But individual patent/opportunity cards don't explain WHY a specific patent is relevant to THIS user. |
| 3 | User can add topics | ✅ | Create Topic form (themes page) + POST /themes with auth-populated user_id. |
| 4 | User can remove topics | ✅ | Delete button on user-owned themes. DELETE /themes/{id} with owner check. |
| 5 | Suggested topics distinct from selected | ✅ | Onboarding StepConfirm shows suggestions with ✕ remove buttons. User can remove before confirming. |
| 6 | System does not auto-select suggestions | ✅ | Industry selection triggers topic SUGGESTIONS via POST /onboarding/complete. User must confirm. |
| 7 | Onboarding creates real records | ✅ Fixed | `cff99ca` + `5da444a`. Confirm creates TopicSubscription rows. `GET /themes/following` returns them. |
| 8 | Theme follow buttons persist | ✅ | Follow creates user-owned theme via POST /themes. Delete removes it. |
| 9 | Company follow path exists or hidden | ✅ Exists | Sprint 5 follow infrastructure exists — companies can be followed from detail pages. Watchlist "Followed Companies" tab wired. |
| 10 | Today consumes followed topics | ⚠️ Gap | Today loads themes via useThemes() which returns ALL themes. Does NOT filter by TopicSubscription or user_id for personalization. |
| 11 | Empty states explain why no results | ✅ Partial | "Personalize your briefing" card shows when no topics. But doesn't explain topic subscription vs user-owned difference. |
| 12 | Opportunity cards explain why it matters | ⚠️ Gap | Cards show "why it matters" text but it's generic (e.g., "New filings may indicate competitor activity"). Does NOT say "why for you specifically." |
| 13 | UX polish: Pricing/About not dead ends | ✅ | Anchor links on marketing nav. id="pricing" and id="about" sections on landing page. |
| 14 | UX polish: Theme toggle | ✅ | "Auto" → "System" |
| 15 | UX polish: No debug labels | ✅ | "System" / "Light" / "Dark" |
| 16 | UX polish: No incomplete placeholders | ⚠️ Gap | Full placeholder audit not done. Boris mentioned "too many placeholder-feeling surfaces." |
| 17 | Login documented | ⚠️ Gap | Open signup blocked by Resend (documented). Controlled login not fully documented for new users. |

## 3. Key Gaps Found (Not Yet Fixed)

### Gap A: Topic/Subscription Mismatch
Onboarding creates `TopicSubscription` rows. Themes page shows "Your Topics" from `Theme.user_id`. These are two different data paths. A user who completes onboarding and follows topics will NOT see them in "Your Topics" on the themes page until they click "+ Follow" on each one.

**Fix needed:** Either unify the data paths OR add TopicSubscription-aware filtering to the themes page API.

### Gap B: Today Personalization Depth
Today shows "For You" section with watchlist items, but does not:
- Filter Trending/Expiring by user's topic CPC prefixes
- Filter by saved searches
- Show "why for you" per-card explanations beyond watchlist

**Fix needed:** Wire user's topic CPC prefixes into Today's trend/expiry filtering.

### Gap C: Opportunity Card Relevance
Opportunity cards on Today use generic "why it matters" copy. No per-user personalization.

**Fix needed:** Add user-context labels. Minimally: "Your topic: [name]" when the patent matches a subscribed topic.

## 4. Manual QA Checklist

### 4.1 Landing Page
- [ ] Navigate to https://inventionindex8.com (or staging)
- [ ] Click "Pricing" → page scrolls to pricing cards section
- [ ] Click "About" → page scrolls to "We show our work" section
- [ ] Theme toggle shows "System" / "Light" / "Dark" (not "Auto")
- [ ] Cycle through all three modes

### 4.2 Login / Onboarding
- [ ] Login with controlled account (no Resend magic link)
- [ ] Onboarding: select a role → next
- [ ] Onboarding: select an industry → next
- [ ] Onboarding: type interests → next
- [ ] Onboarding: confirm page shows suggested companies + themes
- [ ] Onboarding: ✕ removes a suggested theme/company
- [ ] Onboarding: confirm → redirected to Today

### 4.3 Themes / Topics
- [ ] Navigate to /themes
- [ ] System Themes section shows with "+ Follow" buttons
- [ ] Click "+ Follow" on a system theme → it appears in Your Topics
- [ ] Click "Delete" on a user topic → it disappears
- [ ] Click "Create Topic" → fill form → submit → appears in Your Topics
- [ ] Click a topic → patent list loads

### 4.4 Today
- [ ] Navigate to Today
- [ ] "For You" section appears (if user has watchlist/topics)
- [ ] Watchlist card shows saved patent names
- [ ] "More Signals" section below shows trending/notable/expiring
- [ ] "Your Topics" section shows followed topics with patent counts
- [ ] "Personalize your briefing" card shows when no topics exist
- [ ] "Expiring Opportunities" section loads with data or honest empty state

### 4.5 Company Intelligence
- [ ] Navigate to /companies
- [ ] Companies page loads with normalized names + patent counts
- [ ] Entity Type Coverage shows "0 of N — enrichment pending"
- [ ] No heuristic entity_type badges visible
- [ ] Click a company → detail page shows portfolio summary
- [ ] "Enrichment pending" label visible (not fake badges)

### 4.6 Expiry Radar
- [ ] Navigate to /expiry
- [ ] Horizon tabs visible, filter works
- [ ] Save/unsave on expiry cards works
- [ ] CSV export works

### 4.7 Watchlist
- [ ] Navigate to /watchlist
- [ ] Saved Patents tab loads
- [ ] Followed Companies tab loads (if companies followed)
- [ ] Saved Searches tab loads (if searches saved)

## 5. API Verification

```bash
# Theme creation (auth required)
curl -X POST https://inventionindex8.com/api/v1/themes \
  -H "Content-Type: application/json" \
  -H "Cookie: <admin_cookie>" \
  -d '{"name":"Test Topic QA","cpc_prefixes":["G06F"]}'
→ 200, returns theme with user_id set

# Theme deletion (only owner)
curl -X DELETE https://inventionindex8.com/api/v1/themes/<id> \
  -H "Cookie: <admin_cookie>"
→ 200 or 403 if not owner

# Supplier summary (no entity_type)
curl https://inventionindex8.com/api/v1/suppliers/summary
→ No "entity_types" key. entity_type_enrichment_pending: true
```

## 6. Rollback Plan

If any QA check fails at the P0 level:
1. Do not merge sprint-boris-stabilization into release
2. Production stays on release/revamp-launch-validation at `fe3ebcb`
3. Fix the gap on sprint-boris-stabilization
4. Re-run QA checklist
5. Merge only after full pass

Rollback is simply: don't merge.

## 7. What Is Deferred (Post-QA)

| Item | Sprint |
|------|--------|
| Topic/subscription data path unification | V3.1 |
| Deep Today personalization (CPC-filtered trends) | V3.1 |
| Per-card "why for you" explanations | V3.1 |
| Full placeholder audit | V3.1 |
| Natural language search | V3.3 |
| Login reliability audit | Post-Resend fix |

## 8. Boris Review Criteria

Boris should review AFTER this build when:
- Topics are followable and removable on /themes
- Today shows "For You" vs "More Signals" clearly separated
- Theme toggle says System/Light/Dark
- Pricing/About scroll on landing page
- No heuristic badges on companies
- Open signup is clearly blocked with Resend status

Current build: NOT recommended for Boris review yet — opportunity relevance (P0 #4) and placeholder audit (P0 #5) are still gaps.

## 9. Merge Decision

**DO NOT MERGE** until:
- [ ] All 4.1-4.7 manual QA checks pass on staging
- [ ] API checks pass
- [ ] No new P0 regressions
- [ ] Andy approves the remaining gaps as acceptable for this sprint

Recommended: fix Gap A (topic/subscription mismatch) before merge since onboarding creates subscriptions but themes page doesn't show them. This is the single most impactful remaining gap.
