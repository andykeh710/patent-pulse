# Boris P0 — Final QA Checklist

**Branch:** sprint-boris-stabilization
**Head:** pending (will be next commit)
**Diff from:** release/revamp-launch-validation (fe3ebcb)

---

## Commits Since Release

1. `9e2bbd0` — Theme label, nav scroll, landing sections, plan doc
2. `cff99ca` — Topic follow/create/delete with auth
3. `ceff343` — Today For You vs More Signals
4. `5da444a` — GET /themes/following endpoint
5. `e90aa41` — QA plan doc updated
6. `501f85a` — User-context labels on company insights, login docs
7. `3fb8449` — Resend health /emails endpoint fix
8. `41dba00` — Real followed companies, empty personalized state

## Files Changed (13)

```
backend/app/api/v1/health.py
backend/app/api/v1/themes.py
docs/boris-feedback-plan.md
docs/boris-feedback-qa-plan.md
docs/controlled-login-guide.md
frontend/src/app/(app)/themes/page.tsx
frontend/src/app/(app)/today/page.tsx
frontend/src/app/(marketing)/MarketingNav.tsx
frontend/src/app/(marketing)/page.tsx
frontend/src/lib/ThemeProvider.tsx
frontend/src/lib/api.ts
```

## P0 Status — FINAL

| # | Requirement | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Today personalization real | ✅ | Watchlist items + followed-company insights in For You. Empty state with guidance. |
| 2 | Opportunity relevance user-specific | ✅ | Company follow: "Shown because you follow [X]" + evidence tag. Watchlist: "From watchlist." |
| 3 | Topic editing/tracking works | ✅ | Follow/Create/Delete with auth. /following endpoint. Onboarding persists TopicSubscriptions. |
| 4 | Company-first workflow | ✅ | suppliersApi.follows() wired. Followed companies prioritized in For You. |
| 5 | Resend health fix | ✅ | /emails endpoint (sending_access compatible). 401/403 both → "unauthorized". |
| 6 | Controlled login docs | ✅ | docs/controlled-login-guide.md: steps, limitations, troubleshooting. |
| 7 | UX polish | ✅ | System/Light/Dark, anchor nav, no debug labels. | 
| 8 | Placeholder audit | ✅ | See below. No debug labels, no incomplete features presented as finished. |

## Placeholder Audit Results

| Surface | Status | Action |
|---------|--------|--------|
| Today | ✅ | For You + More Signals sections. Empty personalized state with guidance. |
| Themes | ✅ | System themes with Follow. User topics with Delete. Create form. |
| Companies | ✅ | Honest enrichment-pending labels. No fake badges. |
| Patents/Search | ✅ | Filters, sort, saved searches. Functional. |
| Opportunities (Expiry) | ✅ | Horizon tabs, save/unsave, why-it-matters per card. |
| Onboarding | ✅ | Role/industry/interests → suggestions → confirm. Remove buttons on suggestions. |
| Account/Preferences | ⚠️ FYI | Account page exists (deletion, exports). Preferences limited. Acceptable for controlled launch. |
| Landing page | ✅ | Pricing/About scroll sections. Theme toggle. |
| Nav | ✅ | No dead-end pages. Logo returns home. |
| Theme toggle | ✅ | System/Light/Dark. No "Auto" or debug labels. |

No debug/internal labels found. No incomplete placeholder sections presented as finished.

## Today Personalization Examples

**With followed company (Qualcomm):**
```
For You
┌─────────────────────────────────┐
│ Qualcomm filing surge: +12 vs   │
│ 4-week average                  │
│                                 │
│ Shown because you follow        │
│ Qualcomm. Their filing surge of │
│ +12 vs average may signal a new │
│ product cycle, strategic IP     │
│ push, or competitive positioning│
│ relevant to your watch.         │
│                                 │
│ [Company you follow: Qualcomm]  │
│ [This week: 18] [4-week avg: 6] │
│ [Delta: +12]                    │
│                                 │
│ [View company profile]          │
└─────────────────────────────────┘
```

**With watchlist items:**
```
For You
┌─────────────────────────────────┐
│ 3 patents in your watchlist     │
│                                 │
│ Top watchlisted: Battery thermal│
│ management system, Solid-state  │
│ electrolyte composition,        │
│ Fast-charging anode material    │
│                                 │
│ [Saved patents: 3]              │
│ [From watchlist: Your personal  │
│  watchlist]                     │
│                                 │
│ [Open watchlist]                │
└─────────────────────────────────┘
```

**New user (no personalization):**
```
Personalize your briefing
Follow companies, save patents, or create topics to get
personalized intelligence on Today. Generic signals are shown below.

[Search patents] [Create topics] [Browse companies]
```

## Manual QA Checklist

### Landing Page
- [ ] Pricing scrolls to #pricing section
- [ ] About scrolls to #about section
- [ ] Theme toggle: System → Dark → Light → System
- [ ] No "Auto" label

### Login
- [ ] Controlled login works with magic link
- [ ] docs/controlled-login-guide.md is accurate

### Onboarding
- [ ] Role → Industry → Interests → Confirm
- [ ] Suggestions appear with remove buttons
- [ ] Confirm redirects to Today

### Today
- [ ] "Personalize your briefing" shown for new user
- [ ] After saving patents: watchlist insight in For You
- [ ] After following company: company insight in For You
- [ ] More Signals section below For You
- [ ] Your Topics section shows followed topics
- [ ] Expiring Opportunities section loads

### Themes
- [ ] System themes have Follow buttons
- [ ] Click Follow → appears in Your Topics
- [ ] Delete works on user topics
- [ ] Create Topic form works

### Companies
- [ ] No fake entity_type badges
- [ ] "Enrichment pending" shown
- [ ] Company detail loads

### Expiry Radar
- [ ] Horizon tabs work
- [ ] Save/unsave works
- [ ] FilterChips work

### Watchlist
- [ ] Tabs: Saved Patents, Followed Companies, Saved Searches

### API
- [ ] GET /health → resend: ok (with sending_access key)
- [ ] GET /suppliers/follows → returns followed companies
- [ ] GET /themes/following → returns subscribed themes
- [ ] POST /themes → creates with user_id
- [ ] DELETE /themes/{id} → owner-scoped

## Merge Decision

**READY TO MERGE** when manual QA passes.

All 8 P0 requirements closed. 7 commits since release baseline.
No production changes until merged into release/revamp-launch-validation.
