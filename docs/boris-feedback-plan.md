# Boris Feedback — Stabilization Plan (V3 Readiness)

**Date:** 2026-06-15
**Branch:** sprint-boris-stabilization

---

## P0 — Launch/Signup Blocker

| # | Issue | Root Cause | Files | Fix |
|---|-------|-----------|-------|-----|
| 1 | **Today not personalized** | insight cards use generic stats, not user preferences. `buildInsights()` doesn't filter by user's topics/saved items. | `today/page.tsx` | Add topic/watchlist filtering to insights. Add "why for you" labels. Move generic stats below personalized feed. |
| 2 | **Topics uneditable** | Onboarding is single-select for industry only. No add/remove UI after onboarding. | `themes/page.tsx`, `onboarding/` | Add "Add topic" button. Add delete button per topic. Show suggestions separately from selected. |
| 3 | **Topic tracking broken** | `userTopics` filters by `t.user_id` — topics only appear if created/followed via API. No topics exist unless the user explicitly follows them. | `themes/page.tsx`, backend `themes.py` | Add `GET /topics/following` endpoint. Wire onboarding to auto-follow selected topics. Add "follow" button on theme cards. |
| 4 | **Opportunity cards arbitrary** | Cards show "Top Opportunities" without user context. No "why this" or "for whom" explanation. | `today/page.tsx` | Add relevance explanation to each opportunity card. Only show if score ≥ threshold. Show "why relevant to you." |

## P1 — UX Polish

| # | Issue | Root Cause | Files | Fix |
|---|-------|-----------|-------|-----|
| 5 | **Header nav dead ends** | Pricing and About link to separate pages with no back nav. | `MarketingNav.tsx`, `page.tsx` | ✅ Fixed: anchors `#pricing` + `#about` with section IDs. |
| 6 | **Theme toggle "Auto"** | Hardcoded label. | `ThemeProvider.tsx` | ✅ Fixed: "Auto" → "System". |
| 7 | **About layout** | Light/dark contrast issues noticed. | `page.tsx` | ✅ Already uses design tokens — verify in both modes. |
| 8 | **Placeholders** | Several surfaces feel incomplete: themes page, onboarding confirm. | Multiple | Audit: hide or label as coming soon. Add "More coming soon" labels. Remove empty sections. |

## P2 — Feature Depth

| # | Issue | Root Cause | Files | Fix |
|---|-------|-----------|-------|-----|
| 9 | **Natural language search** | Only keyword/semantic/hybrid modes. No chat/query-expansion. | `search.py` | V3.3 — expand semantic search, add chat interface. |
| 10 | **Login reliability** | Need to reproduce. May be Resend-related (magic-link unavailable). | `auth/` | Verify controlled/manual login flow. If Resend is the blocker, documented. |
| 11 | **Login→onboarding flow** | If user skips onboarding, no path to set topics later. | `onboarding/`, `account/` | Add "Edit preferences" in account or Today. |

## Implementation Plan

### Done this commit:
- [x] Theme toggle: "Auto" → "System"
- [x] Header nav: Pricing/About scroll to `#pricing` / `#about` on landing page
- [x] Landing page: `id="pricing"` and `id="about"` sections

### Next sprint (V3.1):
- [ ] Today personalization: filter insight cards by user topics/watchlist
- [ ] Topic editing: add/remove UI
- [ ] Topic follow: onboarding auto-follow + follow button on theme cards
- [ ] Opportunity cards: "why for you" explanations
- [ ] Placeholders: audit and hide/label incomplete sections

### Deferred (V3.2-V3.3):
- [ ] Natural language search improvements
- [ ] Login reliability audit (gated on Resend)

## Acceptance Criteria

- Today shows personalized insights based on user's topics/companies/searches
- User can add and remove topics from themes page
- Onboarding creates real followed topics (not just suggestions)
- Opportunity cards explain relevance
- Landing page: Pricing/About navigable without dead-end pages
- Theme toggle: no debug labels
- No incomplete sections presented as complete features
