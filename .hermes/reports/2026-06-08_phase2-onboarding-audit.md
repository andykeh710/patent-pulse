# Phase 2 — Onboarding Audit

**Date:** 2026-06-08
**Investigator:** Hermes Agent
**Source:** `.hermes/plans/2026-06-04_v3-roadmap.md` Part I, Section 3
**Scope:** Investigation only — no code changes, no production access

---

## Symptom Restated

A first-time visitor lands on `/today` with zero context and zero saved
interests, then bounces. This is the conversion killer. Phase 2 exists
because the product has substance (64K+ patents, AI narratives, expiry,
trends) but a new user sees none of it.

**The core thesis**: Day-1 retention fails not because the product is
weak, but because the first-run experience doesn't deliver a win fast
enough. A user who signs up should see something relevant within 30
seconds. Today they see an onboarding prompt — good start — but there's
no wizard to seed their interests, no persona to shape the briefing,
and no tour to explain what they're looking at.

---

## Marketing Landing Audit

**File**: `frontend/src/app/(marketing)/page.tsx` (590 lines)

**Grade: B+**

| Element | Present? | Quality |
|---------|----------|---------|
| Above-the-fold value prop | Yes | Good — crisp headline, readable subhead |
| Hero stat (patent count) | Yes | "64,231 patents" in data strip |
| CTA prominence | Yes | Primary CTA "Explore the Index" → /login |
| CTA friction | Medium | Goes to /login (magic link) — no social auth, no demo |
| Social proof | No | No testimonials, no user counts, no logos |
| Demo video | No | BriefingPreview component renders a static card, not a video |
| Screenshots | Partial | BriefingPreview is the only visual preview |
| Value props (4 cards) | Yes | Filing Trends, Company Moves, Notable Patents, Expiry — well-written |
| Pricing section | Yes | 4 tiers with feature comparison table |
| Trust block | Yes | "We show our work" — honest about limitations |
| Use cases (3 personas) | Yes | Attorneys, corporate IP, founders/investors |
| How-it-works (3 steps) | Yes | Topics → Briefings → Drill in |

**What's good:**
- Clean dark aesthetic, well-structured sections
- Honest messaging ("We label every estimate", "Not legal advice")
- Enterprise-grade trust signals
- Strong value-prop card copy

**What's missing (blocking conversion):**
- **No hero number / anchor stat** above the fold — the data strip with
  "64,231 patents" sits below the hero CTA. A new visitor scrolls past
  the CTA before seeing any proof of scale.
- **No social proof** — zero testimonials, zero logos, zero "trusted by"
  indicators. Competitors (PatSnap, IPlytics) all feature customer logos.
- **BriefingPreview is a static card** — it's actually titled "Static
  Briefing Preview Component" in its own file. It doesn't animate,
  doesn't rotate, doesn't demonstrate real data. It looks placeholder-ish.
- **CTA copy is abstract** — "Explore the Index" doesn't say what
  happens next. Better: "Start tracking patent signals →" or
  "See today's invention signals →"
- **No urgency** — no "Updated today", no live counter, no "X new
  patents this week" above the fold

**Suggested improvements (not implementing now):**
- Move hero stat into the hero section itself (not buried in a strip below)
- Replace BriefingPreview with a 30-second auto-play demo of the actual
  product (Loom/screen recording GIF)
- Add a "Used by patent attorneys, investors, and founders" social proof
  line (can be aspirational until real logos exist)
- Change CTA to "See today's signals →" (concrete, implies instant value)

---

## Post-Signup Flow Audit

**Flow traced:**
1. `/login` → enter email → click "Send magic link" (1 friction: no
   passwordless awareness copy)
2. Email arrives → click link → `/auth/login/verify?token=...`
3. Verify page shows spinner → on success: `router.push("/today")`
4. `/today` loads → detects `isFirstTime` (no themes + no watchlist) →
   renders `FirstTimeOnboarding` component

**What works:**
- Magic-link auth is smooth — one input, no password
- The verify → redirect → today flow has no interstitials (good)
- `FirstTimeOnboarding` is a well-designed welcome card with:
  - "Welcome to Invention Index 8" heading
  - StarterTopics component (pre-built topic packs)
  - Two action cards: "Browse all patents" + "Explore trends"

**What's broken / missing:**
- **No wizard between verify and /today.** The roadmap calls for a
  3-question first-run wizard (role, industry, example patent). This
  doesn't exist. The user is dumped onto /today with a welcome card
  but no guided path.
- **Persona is never captured.** The backend has `PUT /account/persona`
  and the model stores it, but the frontend never asks for it. No
  persona-aware briefing exists.
- **StarterTopics creates topics, but doesn't personalize.** The
  same 6 topics are shown to every user regardless of their interests.
- **After creating a topic, the user stays on /today but there's no
  immediate payoff** — topic matching runs async and may take minutes.
  The user creates a topic and sees "Your Topics" with 0 patents matched.

**Clicks from landing → first insight:**
1. Landing → /login (1 click)
2. Enter email → submit (1 action)
3. Open email → click link (2 actions, out-of-app)
4. Auto-redirected to /today (0 clicks)
5. Create a topic via StarterTopics (2 clicks)
6. Wait for topic matching to complete (unknown delay — could be minutes
   or never if Celery isn't running/backed up)
7. Click into topic to see matched patents (1 click)

**Total: 5 clicks + email roundtrip + async wait.**
To reach "first useful insight" could be 3-5 minutes. This is too long.

---

## Empty-State Catalog

| # | Page | File:Line | Copy | Grade | Suggestion |
|---|------|-----------|------|-------|------------|
| 1 | `/` (marketing) | `(marketing)/page.tsx` | N/A — no empty state, always renders full page | N/A | — |
| 2 | `/today` (first-time) | `(app)/today/page.tsx:182-221` | "Welcome to Invention Index 8. Track patent filings, spot expiring opportunities... Start by creating a topic below." + StarterTopics + 2 action cards | **A-** — good welcome card, clear CTA, contextual | Wired but needs the wizard before it. |
| 3 | `/companies` | `(app)/companies/page.tsx:248` | "No companies found for the selected filters." | **D** — vague, no guidance, no link to create/follow, no explanation of what companies ARE | Add: "Companies are derived from patent assignees. Follow companies to track their R&D activity. [Browse assignees →]" |
| 4 | `/themes` | `(app)/themes/page.tsx:213-233` | "Your patent intelligence starts here. Choose a starter topic below or create your own..." + StarterTopics + "Or create your own topic" button | **A** — best empty state in the app. Emoji, clear value prop, action buttons | Near-perfect. Only missing: persona-driven topic suggestions (e.g. "You're an investor — try these:") |
| 5 | `/watchlist` | `(app)/watchlist/page.tsx:58-67` | "No patents saved yet. Bookmark patents from any page to build your personal watchlist. Saved patents will also appear in your Today briefing." + links to /patents and /opportunity | **A-** — clear, actionable, explains the value | Could add: "Here are 3 popular patents to get started →" |
| 6 | `/opportunity` | `(app)/opportunity/page.tsx:358-364` | "No opportunities match these filters yet. Try widening the cohort or recompute opportunity scores via Admin → AI Runs." | **C** — addresses admins but NOT end users. A non-admin user sees a dead end pointing to admin tools they can't access | For non-admin users: "Opportunity data is still indexing. Check back soon or browse [all patents →]." |
| 7 | `/expiry` | `(app)/expiry/page.tsx` | Multiple empty messages per tab (6 different ones) — all clear and accurate: "No patents currently flagged as expiring within your filter window." etc. | **B+** — accurate and honest. Multiple states handled well. | Good. Just needs a first-time user hint: "New to expiry analysis? [Learn how it works →]" |
| 8 | `/search` (pre-query) | `(app)/search/page.tsx:153-167` | "Enter keywords to search patents" (fulltext) / "Describe the technology you're looking for" (semantic/hybrid) + min chars hint | **B** — clean, mode-aware. Good use of context | Add example queries as clickable chips: "battery thermal management", "CRISPR delivery", etc. |
| 9 | `/trends` | `(app)/trends/page.tsx:251-253` | "No trend data available yet. Run the weekly trend computation first." | **D** — admin-only language, no user path | "Trend data is still being computed. In the meantime, browse [hot technology areas →] or [recent patents →]" |

**Summary**: 2 As, 3 Bs, 1 C, 2 Ds. The themes and watchlist empty states are excellent. Companies, trends, and opportunity empty states read like admin debug messages rather than user-facing guidance.

---

## Persona Usage

**The field exists**: `User.persona` — `String(16)`, nullable, added in
Round 6 migration. Valid values: `"operator"`, `"investor"`, `"curious"`.

**Backend**: `PUT /api/v1/account/persona` — accepts and stores persona.
`GET /api/v1/account/persona` — returns stored persona (not found in
the audit but inferred from the set endpoint pattern).

**Frontend**: No UI to set persona. No signup wizard asks for it. No
account settings page exposes it.

**Usage in briefing/recommendations**: **ZERO.** The persona field is
stored and retrievable but nothing reads it. Not the Today briefing
pipeline, not the weekly digest fan-out, not the for-you recommendations,
not the StarterTopics component.

**Gap**: The roadmap calls for "Persona-aware Today briefing" in Phase 2.
This requires:
1. A UI to capture persona (wizard or account page)
2. Logic to filter/weight Today content based on persona
   (e.g., "investor" → emphasize expiry opportunities;
   "operator" → emphasize company moves; "curious" → balanced)

---

## In-App Tour / Help

**No tour exists.** Zero. No help modals, contextual hints, tooltips,
walkthrough, or "Take a tour" button.

**What's recommended (per roadmap — no driver.js bloat):**
- A single `TourModal` component reusable across pages
- A "Take a tour" button in the top nav (visible to new users,
  dismissable)
- Per-page tour content: 2-3 slides explaining what the page does and
  how to get value from it
- Dismissal stored in localStorage — don't show again once dismissed
- Trigger automatically on first visit (after signup) OR via button

**Effort**: ~3 hours for component + content, ~1 hour per page for
tour slides.

---

## First-Action Friction Summary

**Path**: Landing → /login → email → verify → /today → create topic →
wait for matching → click topic → see first patent.

**Time to first insight**: 3-5 minutes (dominated by email roundtrip +
  async topic matching delay).

**Friction points:**
1. Email roundtrip is inherent to magic-link auth — acceptable for
   B2B/SaaS but could add a "check your email" interstitial with a
   countdown and tips ("While you wait: here's what Invention Index
   tracks →")
2. Topic matching is async and invisible — the user clicks "create
   topic" and sees a topic card with "0 patents" for an unknown period.
   Fix: show an estimated time ("Matching usually completes within 2 min")
   or pre-seed topics with immediate results from cached data.
3. No guidance after topic creation — user is back on /today with
   no next step highlighted.

---

## Recommended Phase 2 PR Breakdown

Ordered by impact ÷ effort. Recommend shipping in this sequence:

| PR | Description | Effort | Depends on |
|----|-------------|--------|------------|
| **PR 1** | First-run wizard (3 questions → seed companies + themes + persona) | 4h | — |
| **PR 2** | Empty-state copy pass (companies, trends, opportunity, search) | 2h | — |
| **PR 3** | Persona-aware Today briefing + persona capture UI | 3h | PR 1 |
| **PR 4** | In-app tour modal + "Take a tour" in nav | 3h | PR 2 (needs good empty states) |
| **PR 5** | Marketing landing copy refresh (hero stat, CTA, social proof placeholder) | 2h | — |

**Total: ~14 hours (~2 days of focused work)**

### Rationale for ordering:

1. **PR 1 first** — The wizard is the highest-impact single change.
   It captures persona + seeds topics/companies, which immediately
   populates /today with relevant content. This closes the biggest
   gap between signup and first insight.

2. **PR 2 next** — Low effort, high impact. The D-grade empty states
   (companies, trends) actively confuse users. Fixing copy requires
   no backend changes.

3. **PR 3 after wizard** — Once persona is captured, the briefing can
   actually use it. Without PR 1, persona-aware briefing has nothing
   to be aware OF.

4. **PR 4 after copy pass** — The tour modal should reference pages
   that already have good empty states. Ship the copy fix first.

5. **PR 5 last** — The landing page already works (B+). The
   improvements are polish, not blockers. If time-constrained, skip
   or defer.

---

## Open Questions for Andy

1. **Wizard questions** — the roadmap says "your role, your industry,
   one example patent you care about." Is this the final set, or do you
   want different questions? (Suggestion: Role → Industry/technology
   area → What problem are you trying to solve? — less intimidating
   than "example patent you care about" which assumes patent knowledge.)

2. **Persona-aware briefing** — what should "investor" vs "operator"
   vs "curious" actually change? My suggested weights:
   - Investor: 40% expiry opportunities, 30% company moves, 20% trends,
     10% notable patents
   - Operator: 40% company moves, 30% trends, 20% notable patents,
     10% expiry
   - Curious: balanced 25% each
   Does this match your intent?

3. **Topic seeding from wizard** — should the wizard auto-create topics
   from the user's answers, or just suggest them? Auto-create is faster
   but risks creating topics the user didn't intend.

4. **Tour modal content** — do you want to write the tour copy yourself
   (you know the product best) or should I draft it? Recommend you
   write the final copy; I'll build the component and wire it up.

5. **Marketing landing** — the "social proof" gap is real but filling
   it with real logos/testimonials requires customers. Should we ship
   with placeholder social proof ("Trusted by patent professionals")
   or leave it absent until we have real logos?

6. **Magic-link friction** — the email roundtrip adds ~60 seconds to
   signup. Is this acceptable for the target audience, or should we
   explore Google/GitHub OAuth as a faster path? (Not a Phase 2 item,
   just flagging.)

---

## Doc Maintenance

Update this report when:
- Phase 2 PRs ship (mark each done with date)
- Wizard questions/structure changes
- Persona weights are calibrated
- Tour copy is written
