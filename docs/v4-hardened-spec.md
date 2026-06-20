# V4.0 — Hardened Strategy & Spec

**Status:** Spec-complete. Implementation NOT authorized until V3 production stable.
**Last updated:** 2026-06-19
**Release base:** `e038208`

---

## 1. Decisions Already Accepted

These are locked. Do not revisit in V4.0 planning.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Community features attach to valuable objects, not empty social | Prevents shallow engagement loops without anchored utility |
| 2 | Visibility model: private → unlisted → org → public → moderated → removed | Six-tier, each tier has clear rules |
| 3 | Public sharing requires explicit opt-in | No accidental data exposure |
| 4 | Confidential disclosure warning required on all content-submission UIs | Legal risk mitigation |
| 5 | `intelligence_items` single-table model | Avoids per-type table explosion |
| 6 | Evidence items required for all public objects | Source provenance is non-negotiable |
| 7 | Moderation: report → review → hide/delete/suspend | Minimum viable before any public content |
| 8 | Trust tiers: verified → active → trusted → expert | Gates publishing privileges |
| 9 | AI-generated content must be labeled | Transparency requirement |
| 10 | No anonymous voting or commenting at launch | Prevents spam without identity anchor |

---

## 2. Unresolved Decisions (Must Decide Before V4.1)

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| U1 | **Anonymous access to public pages** | (a) All public pages visible without login, (b) Login required to view any content, (c) Login-gated with preview cards | **Recommend (a)** — public topic/company pages should be indexable and accessible. Gate actions (save, follow, vote) behind login. |
| U2 | **SEO indexing policy** | (a) Index all public pages immediately, (b) Index only after manual review, (c) No-index until V4.3 | **Recommend (b)** — add `robots: noindex` by default, allow `index` via admin toggle after quality review |
| U3 | **GDPR data export/deletion** | (a) Full self-service export + delete, (b) Manual request only, (c) Defer to V4.3+ | **Recommend (a) for deletion, manual for export** — delete must be self-service Day 1; export can start manual |
| U4 | **Attribution model for shared briefs** | (a) Always show original author, (b) Author controls attribution, (c) Anonymous by default | **Recommend (a)** — author shown on public briefs, credit is non-negotiable for trust |
| U5 | **Forking/remixing of collections and briefs** | (a) Fork with attribution chain, (b) Fork without attribution, (c) No forking in V4.x | **Recommend (c)** — defer forking to V4.4+. Adds complexity without proven demand |
| U6 | **Content license for public objects** | (a) Default CC-BY, (b) Default all-rights-reserved, (c) Author chooses | **Recommend (a)** — CC-BY for public briefs encourages reuse while maintaining attribution |
| U7 | **User deletion cascade** | Soft-delete user → what happens to their public briefs/collections? | **Recommend**: Public objects remain but author shows "Former contributor". Private objects soft-deleted. |

---

## 3. Risks That Block V4.1

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | **USPTO data staleness** — public pages showing May 28 data look abandoned | CRITICAL | V4.1 must not launch until USPTO ingestion recovers AND latest pub date advances |
| R2 | **No private intelligence loop users** — building community features for 0 active users | HIGH | Require N active V3 users (≥10 weekly active) before V4.1 public launch |
| R3 | **Confidential disclosure legal exposure** — user posts trade secret, we're liable | HIGH | Disclosure warning + report flow + rapid takedown must all be live before any public content |
| R4 | **Moderation staffing** — no human moderator available | HIGH | Start with pre-moderation (all public objects require admin approval) if no moderator |
| R5 | **`entity_type` enrichment 0%** — company pages will look incomplete | MEDIUM | Acceptable if labeled "Enrichment pending". Not a launch blocker if honest. |
| R6 | **Resend email not in production** — passwordless auth broken outside local dev | HIGH | Production Resend required before any public launch (users must be able to sign up) |

---

## 4. Risks That Can Be Deferred

| # | Risk | Defer To | Why Safe |
|---|------|----------|----------|
| D1 | Reputation/gamification abuse | V4.4+ | No voting yet |
| D2 | Forked content quality dilution | V4.4+ | Forking deferred |
| D3 | Expert verification fraud | V4.5+ | Expert tier deferred |
| D4 | Collection spam | V4.2+ | Rate limits + auth gating sufficient for MVP |
| D5 | API key abuse for data export | V4.6 | API not built yet |
| D6 | Multi-language content moderation | V4.3+ | English-only MVP |

---

## 5. V4.1 Entry Criteria (ALL must be met)

| # | Criterion | Status |
|---|-----------|--------|
| C1 | V3 production stable + deployed | In progress |
| C2 | USPTO ingestion recovered — latest pub date > 2026-05-28 | ❌ Blocked by USPTO |
| C3 | Resend email in production (magic link works without log extraction) | ❌ Pending |
| C4 | `intelligence_items` + `evidence_items` migration applied (0040) | ❌ Not started |
| C5 | Confidential disclosure warning component built | ❌ Not started |
| C6 | Moderation: report flow + admin queue live | ❌ Not started |
| C7 | Admin pre-moderation toggle (all public = require approval) | ❌ Not started |
| C8 | `robots: noindex` on all public pages until manually approved | ❌ Not started |
| C9 | ≥10 weekly active V3 users (private intelligence loop validated) | ❌ Not measured |
| C10 | GDPR delete self-service working | ❌ Not started |

---

## 6. First Implementation Slice (V4.0-MVP)

**After V3 production stable AND USPTO ingestion recovered:**

### Migration 0040
```sql
-- intelligence_items (shared publishable object base)
-- evidence_items (required for public objects)
-- moderation_events (report → review → action)
-- No collections, no voting, no comments, no profiles yet
```

### Backend (3 new endpoints)
```
GET  /api/v1/public/topics/{slug}        — public topic overview (no auth required)
GET  /api/v1/public/companies/{slug}     — public company page (no auth required)
POST /api/v1/admin/moderation/events     — admin-only
GET  /api/v1/admin/moderation/queue      — admin-only
```

### Frontend (2 new routes)
```
/topics/{slug}     — public topic page (anonymous accessible)
/companies/{slug}  — public company page (anonymous accessible)
/admin/moderation  — admin dashboard (auth-gated)
```

### NOT in V4.0-MVP
- Public briefs, collections, comments, profiles
- Voting (feature or intelligence)
- Social follows, activity feeds, notifications
- SEO indexing (all pages `noindex` by default)

### V4.0-MVP Acceptance
- [ ] Unauthenticated user can browse `/topics/{slug}` and `/companies/{slug}`
- [ ] Pages show honest data (no fake enrichment, source lag labeled)
- [ ] No private user data exposed on public pages
- [ ] Every page shows confidential disclosure warning
- [ ] CTA to sign up / create private watchlist
- [ ] Admin can mark a public page as `robots: index` after quality review
- [ ] Report flow works end-to-end (user reports → admin reviews → action)
- [ ] GDPR delete self-service works
