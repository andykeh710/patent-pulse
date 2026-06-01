# Frontend Overhaul — Phase G: Polish + Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Final polish and quality gates. Mobile responsiveness audit, prefers-reduced-motion across the entire surface area, accessibility (WCAG AA + keyboard nav + screen reader), Lighthouse targets, component + E2E tests, and the final honesty audit. Produce a comprehensive V1 verification report.

**Architecture:** No new features. Audit-and-fix passes across every surface built in Phases A–F.

**Tech Stack:** Lighthouse CLI, axe-core (or @axe-core/playwright if available), Jest, Playwright (if available from preflight), the existing test infrastructure.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §14 Quality bars, §11.1 Phase G.

**Depends on:** Phase F gate passed.

---

## File Structure

```
.hermes/plans/2026-06-01_frontend-v1-verification-report.md   # NEW — final report
frontend/tests/e2e/onboarding-to-watchlist.spec.ts             # NEW — E2E test (if Playwright available)
```

Most changes in this phase are small fixes applied to existing files identified during the audits, not new files.

---

## Tasks

### Task 1: Mobile responsiveness audit at 375px

- [ ] **Step 1: Test every authenticated route at iPhone X viewport**

Open Chrome DevTools, set viewport to 375x812 (iPhone X). For each of these routes, capture screenshot or describe layout behavior:

```
/today, /patents, /patents/<id> (all 4 tabs), /trends, /trends/g06t, /expiry, /opportunity, /themes, /themes/<id>, /companies, /companies/<name>, /watchlist, /search, /account, /account/billing, /login
```

- [ ] **Step 2: Identify breakpoints that fail**

Common failures to look for:
- Grid stays at 4 columns when it should stack
- Sidebar widgets overflow horizontally
- Stat tile values truncate ("64,231" becomes "...")
- Top nav items don't fit, get clipped
- Patent detail tabs overflow horizontally
- Buttons sit on top of each other

- [ ] **Step 3: Fix each breakage**

For each failure, apply Tailwind responsive classes. Common patterns:

```typescript
// Stats row: stack 2x2 on mobile, 4-across on desktop
className="grid grid-cols-2 md:grid-cols-4 gap-3"

// Today grid: single column on mobile, sidebar at lg
className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6"

// Patent detail tabs: scrollable horizontally on mobile
className="flex gap-1 overflow-x-auto"

// Top nav: collapse to hamburger or hide nav items below sm
className="hidden md:flex" (for nav items)
```

For top nav on mobile, add a hamburger menu trigger that opens a drawer. Use `useState` + a fixed overlay.

- [ ] **Step 4: Commit responsive fixes**

```bash
git add frontend/src/components/nav/TopNav.tsx frontend/src/app/\(app\)/today/page.tsx frontend/src/components/today/StatsRow.tsx
git commit -m "fix(frontend): mobile responsive across all surfaces (375px)"
```

---

### Task 2: Tablet responsiveness audit at 768px

- [ ] **Step 1: Repeat audit at 768x1024 viewport**

Most layouts at this size should be acceptable with the mobile fixes from Task 1. Verify:
- 2-column layouts (e.g., stats row 2-across or 4-across) look intentional
- Patent detail page is usable
- Top nav has enough room for all 7 items

- [ ] **Step 2: Apply any md: breakpoint fixes needed**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "fix(frontend): tablet responsive audit (768px) fixes"
```

---

### Task 3: prefers-reduced-motion final sweep

- [ ] **Step 1: Toggle reduced motion in DevTools, visit every route**

Same route list as Task 1 (mobile audit). For each route, verify:
- No background drift animations
- No scan-sweep animations
- No counter count-up (jumps to final value)
- No signal-pulse animations
- Hover states still work (border/opacity changes only, no transforms)

- [ ] **Step 2: Identify offenders**

```bash
grep -rn "animate-\|transition-transform" frontend/src/components frontend/src/app | grep -v motion-reduce
```

For each match, verify the animation has a `motion-reduce:` escape or is otherwise gated.

- [ ] **Step 3: Add motion-reduce overrides where missing**

```typescript
// Example: a card that lifts on hover
className="transition-transform hover:-translate-y-0.5 motion-reduce:transition-none motion-reduce:hover:translate-y-0"
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "fix(frontend): prefers-reduced-motion respected across all primitives + surfaces"
```

---

### Task 4: Accessibility audit (keyboard navigation)

- [ ] **Step 1: Tab through every interactive element on /today**

Press Tab repeatedly. Verify:
- Every link, button, dropdown, input is reachable
- Focus indicator is always visible (`focus-visible:ring`)
- Focus order is logical (top to bottom, left to right)
- No focus traps (you can Tab out of any region)

- [ ] **Step 2: Repeat for /patents/<id> (all 4 tabs)**

Particularly verify:
- Tab keys allow switching between Summary/Opportunity/Family/Source
- Action buttons (Save, Follow) reachable
- External links reachable

- [ ] **Step 3: Test keyboard navigation through PersonaWizard**

- Step 1 persona cards: Tab through 3 options, Enter to select, Tab to Continue
- Step 2 topics: Tab through chips, Space to toggle
- Step 3 companies: Tab through follow buttons, Enter to click

- [ ] **Step 4: Fix any keyboard reachability issues**

Common issues:
- Custom button-styled `<div>` elements that aren't focusable → change to `<button>` or add `role="button" tabIndex={0}`
- Missing focus-visible styles → add `focus-visible:ring-2 focus-visible:ring-[var(--signal-glow)]`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "fix(frontend): keyboard navigation + focus-visible across all surfaces"
```

---

### Task 5: Accessibility audit (screen reader / ARIA)

- [ ] **Step 1: Run axe-core in DevTools**

Open DevTools → Lighthouse → Accessibility audit. Or install the axe DevTools extension and run on each route.

- [ ] **Step 2: Fix Critical and Serious issues**

Common issues:
- Missing `alt` on images → add or `aria-hidden`
- Buttons without accessible name → add `aria-label` or visible text
- Icon-only buttons (search, alerts) → add `aria-label="Search"` etc.
- Form inputs without `<label>` → add label or `aria-label`
- Low color contrast → adjust the token value or use a different combination

- [ ] **Step 3: Document non-fixable issues**

Some issues are inherent to design choices (e.g., glass-panel low contrast on hover). Document with rationale.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "fix(frontend): accessibility — aria-labels, labels, contrast adjustments"
```

---

### Task 6: Color contrast verification (WCAG AA)

- [ ] **Step 1: Verify body text contrast**

Body text: `--text-primary` (`#E8ECF7`) on `--bg-base` (`#0A0E27`).
Calculate ratio: should be ≥ 4.5:1.
Use https://webaim.org/resources/contrastchecker/ or DevTools color picker.

Expected ratio: ~14:1 (passes).

- [ ] **Step 2: Verify muted text**

`--text-muted` (`#94A3B8`) on `--bg-base`.
Expected: ~7:1 (passes).

- [ ] **Step 3: Verify low-contrast cases**

Briefing item subtext, freshness indicators, "View →" link text on glass panels — these are likely the lowest contrast spots. Verify each meets:
- ≥ 4.5:1 for body text
- ≥ 3:1 for "large text" (≥ 18.5px or ≥ 14px bold)

- [ ] **Step 4: Adjust tokens if any contrast fails**

Brighten `--text-muted` slightly if needed: `#A0A8C0` instead of `#94A3B8`. Update `tokens.css` and propagate.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/tokens.css
git commit -m "fix(frontend): color contrast adjustments for WCAG AA compliance"
```

---

### Task 7: Loading state polish

- [ ] **Step 1: Audit loading states across surfaces**

For each major surface, throttle network in DevTools (Slow 3G) and observe loading state. Verify:
- Skeleton uses brand voice loading copy from `COPY` (loadingIndexing, loadingScanning, loadingMapping, loadingRanking)
- Skeleton shimmer is subtle (low opacity)
- Skeleton matches the shape of the final content (so layout doesn't jump)

- [ ] **Step 2: Apply branded loading text**

Where a loading spinner exists, add a rotating brand-voice phrase below it:

```typescript
const LOADING_MESSAGES = [
  COPY.loadingIndexing,
  COPY.loadingScanning,
  COPY.loadingMapping,
  COPY.loadingRanking,
];

const [msgIndex, setMsgIndex] = useState(0);
useEffect(() => {
  const i = setInterval(() => setMsgIndex(n => (n + 1) % LOADING_MESSAGES.length), 1500);
  return () => clearInterval(i);
}, []);

return <p>{LOADING_MESSAGES[msgIndex]}</p>;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "polish(frontend): branded loading states with rotating COPY messages"
```

---

### Task 8: Error state polish

- [ ] **Step 1: Audit error states**

Block each backend endpoint in DevTools Network tab. Observe the error state on each surface.

Verify:
- Error message is brand-voice (not "Error 500" or stack trace)
- Retry button present
- "Report issue" link to support email (mailto:support@inventionindex8.com)
- Error doesn't break the rest of the page (uses `<ErrorBoundary>` if isolation is needed)

- [ ] **Step 2: Polish copy**

Replace any "Error" / "Something went wrong" with brand-voice equivalents:
- "Couldn't load your briefing right now. Try again in a moment."
- "Patent data unavailable temporarily. Verify with official source."
- etc.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "polish(frontend): brand-voice error states across all surfaces"
```

---

### Task 9: Lighthouse audit on key surfaces

- [ ] **Step 1: Run Lighthouse on /today**

```bash
npx lighthouse https://inventionindex8.com/today --view --preset=desktop --only-categories=accessibility,performance,best-practices
```

Or if running locally:
```bash
npx lighthouse http://localhost:3000/today --view --preset=desktop
```

- [ ] **Step 2: Run Lighthouse on /patents/<id>**

Pick a representative patent.

- [ ] **Step 3: Run Lighthouse on / (landing)**

- [ ] **Step 4: Verify targets per spec §14**

- Accessibility ≥ 90 on all three
- Performance ≥ 80 on /today (deeper pages may score lower; that's acceptable per spec)
- Best Practices ≥ 80

- [ ] **Step 5: Fix lowest-hanging items**

Common low-hanging Lighthouse wins:
- Missing meta tags
- Images without dimensions
- Unused CSS / JS (small wins from removing dead code)
- Cumulative Layout Shift (CLS) — fix by reserving space in skeletons

- [ ] **Step 6: Save Lighthouse reports**

Save the JSON reports to `.hermes/plans/lighthouse-reports/`:

```bash
mkdir -p .hermes/plans/lighthouse-reports
npx lighthouse http://localhost:3000/today --output=json --output-path=.hermes/plans/lighthouse-reports/today.json --preset=desktop
npx lighthouse http://localhost:3000/patents/<id> --output=json --output-path=.hermes/plans/lighthouse-reports/patent-detail.json --preset=desktop
npx lighthouse http://localhost:3000/ --output=json --output-path=.hermes/plans/lighthouse-reports/landing.json --preset=desktop
```

- [ ] **Step 7: Commit any fixes**

```bash
git add frontend/src/
git commit -m "polish(frontend): Lighthouse fixes for accessibility/performance targets"
```

---

### Task 10: Component test coverage

- [ ] **Step 1: Run full frontend test suite**

```bash
cd frontend && npm test -- --coverage
```

- [ ] **Step 2: Identify gaps**

Components that lack tests after Phases A–F:
- BrandMark, AccountDropdown, TopNav, all 5 Today widgets, FollowButton, all 4 patent tabs, TrendCard, all onboarding steps

For each gap, write a minimal smoke test (renders without crashing, key props produce expected output).

Example for TopNav:

```typescript
import { render, screen } from "@testing-library/react";
import { TopNav } from "@/components/nav/TopNav";

// Mock the hooks used inside
jest.mock("@/lib/AuthContext", () => ({ useAuth: () => ({ user: { email: "x@y.com" } }) }));
jest.mock("next/navigation", () => ({ usePathname: () => "/today" }));

describe("TopNav", () => {
  it("renders all 7 nav items", () => {
    render(<TopNav />);
    ["Today","Patents","Expiry","Opportunities","Trends","Topics","Companies"].forEach(label => {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 3: Run tests until target met**

Target: ≥ 60% statement coverage on all new components. Don't chase 100% — focus on the most-used and most-likely-to-break.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "test(frontend): component test coverage for Phase A-F additions"
```

---

### Task 11: E2E test — signup to watchlist

**Files:**
- Create: `frontend/tests/e2e/onboarding-to-watchlist.spec.ts` (if Playwright available)

If Playwright wasn't available per Phase 0 preflight, this task is a manual test instead.

- [ ] **Step 1: Write the test (or run manually)**

```typescript
import { test, expect } from "@playwright/test";

test("new user → wizard → today → save a patent → watchlist", async ({ page }) => {
  // 1. Sign up / log in as a fresh user
  await page.goto("/login");
  await page.fill('input[type="email"]', "e2e-test@inventionindex8.com");
  // ... magic link flow (use a test bypass in dev)

  // 2. Wizard appears
  await expect(page.locator('text=What brings you here?')).toBeVisible();

  // 3. Step 1: pick Operator
  await page.click('text=Builder / Operator');
  await page.click('button:has-text("Continue")');

  // 4. Step 2: pick 2 topics
  await page.click('text=AI / ML');
  await page.click('text=Batteries');
  await page.click('button:has-text("Continue")');

  // 5. Step 3: follow 1 company
  await page.click('button:has-text("+ Follow")').first();
  await page.click('button:has-text("Finish")');

  // 6. Arrive at Today
  await expect(page).toHaveURL(/\/today/);
  await expect(page.locator('text=Good morning')).toBeVisible();
  await expect(page.locator('text=2 topics · 1 companies')).toBeVisible();

  // 7. Click into a patent from briefing
  await page.locator('a[href*="/patents/"]').first().click();
  await expect(page).toHaveURL(/\/patents\//);

  // 8. Save to watchlist
  await page.click('button:has-text("Save patent")');
  await expect(page.locator('text=✓ Saved')).toBeVisible();

  // 9. Go to watchlist
  await page.click('text=Watchlist');  // via account dropdown
  await expect(page).toHaveURL(/\/watchlist/);
  // The patent we just saved should appear
});
```

- [ ] **Step 2: Run the test**

```bash
cd frontend && npx playwright test onboarding-to-watchlist.spec.ts
```

Expected: passes.

- [ ] **Step 3: If Playwright unavailable: do this manually**

Walk through the same 9 steps in a browser. Document each in the verification report.

- [ ] **Step 4: Commit**

```bash
git add frontend/tests/e2e/
git commit -m "test(frontend): E2E signup → wizard → today → save → watchlist"
```

---

### Task 12: Final honesty audit

This is the most important audit of Phase G. The whole "evidence-first" positioning depends on it.

- [ ] **Step 1: Walk through every briefing item on /today**

For each rendered item:
- Does it have a `reason` field visible?
- Does it have a `source` field visible (or in tooltip)?
- Does it have a `freshness` line visible?
- If it has `confidence`, is the caveat visible?

If ANY item is missing ANY of these fields, that's a backend bug — go fix it in /api/v1/today/briefing.

- [ ] **Step 2: Verify no fake content**

Walk through:
- /today briefing — no fake patent records, no fake news, no "AI" claims on foryou card
- /companies/[name] — only shows real companies from indexed data
- /trends — trends are real-computed, not synthetic
- /expiry — caveat banner is visible everywhere expiry data appears
- /opportunity — opportunity scores are real, with caveats
- /account/billing — no fake subscription state, no fake invoices

If ANY surface has fabricated content, that's a critical bug. Remove it immediately and replace with honest empty state.

- [ ] **Step 3: Verify forbidden language**

```bash
grep -rEn "free to use|public domain|safe to build|guaranteed|definitive intelligence|directional intelligence signals" frontend/src
```

Expected: zero matches in user-facing strings (matches in code comments are acceptable but should be reviewed).

- [ ] **Step 4: Verify For You honesty**

Visit the foryou item on /today. Confirm:
- Label is "For you — early personalization" (NOT "AI For You" or "✨ AI")
- Footer/subtext mentions "Full AI recommendations are coming later"
- The `reason` field names which follow triggered it

- [ ] **Step 5: Verify news slot honesty**

Visit the news item on /today. Confirm:
- Label includes "V1.1" indicating it's a placeholder
- No fake headlines, no fake "why this matters" content

- [ ] **Step 6: Document the audit**

In the verification report, paste:
- A list of every briefing-item type with reason/source/freshness/confidence verification
- Confirmation no fake content was found
- Forbidden-language grep result
- Foryou + news honesty confirmation

---

### Task 13: Write the V1 verification report

**Files:**
- Create: `.hermes/plans/2026-06-01_frontend-v1-verification-report.md`

- [ ] **Step 1: Compose the report**

The report should include sections for every Phase G task, summarizing what was tested, what was fixed, and the outcome:

```markdown
# Frontend V1 Verification Report

**Date:** 2026-XX-XX  (date Phase G completes)
**Sprint:** Frontend Overhaul V1 (Phases 0 → G)
**Status:** Complete

## Coverage

- Phase 0: preflight report referenced at .hermes/plans/2026-06-01_frontend-overhaul-preflight.md
- Phase A gate report: .hermes/plans/2026-06-01_frontend-phase-a-gate.md
- Phase B gate report: ...
- (each phase gate)

## Mobile responsiveness

[Per-route notes from Task 1]

## prefers-reduced-motion

[Audit results from Task 3]

## Accessibility

[axe results, contrast verification, keyboard navigation, Lighthouse scores]

## Lighthouse

| Surface | Accessibility | Performance | Best Practices |
|---|---|---|---|
| / | XX | XX | XX |
| /today | XX | XX | XX |
| /patents/<id> | XX | XX | XX |

## Tests

- Frontend: N component tests, M E2E tests, all passing
- Backend: 341 baseline + N new = X passing, 0 failures

## Honesty audit

- All briefing items have reason / source / freshness / confidence ✓
- No fake content found ✓
- Forbidden language grep clean ✓
- For You labelled "early personalization", not "AI" ✓
- News slot labelled V1.1 placeholder ✓

## Known remaining issues

[Anything you didn't get to fix, with severity]

## V1 status

**SHIP** or **HOLD on [reason]**
```

- [ ] **Step 2: Commit**

```bash
git add .hermes/plans/2026-06-01_frontend-v1-verification-report.md
git commit -m "docs: V1 frontend overhaul verification report"
```

---

### Task 14: Final hand-off to Andy

- [ ] **Step 1: Send a summary message to Andy**

Include:
- Path to verification report
- Top 3 highlights of what was delivered
- Top 3 known issues (if any)
- Explicit ship/hold recommendation

- [ ] **Step 2: Wait for Andy's decision**

If Andy approves: V1 is complete. Phase H buffer is available for any post-ship fixes Andy wants.

If Andy holds: go back to specific tasks to address the holds. Do not push V1.1 work in parallel.

---

## Phase G Gate (V1 SHIP gate)

V1 is complete and ready for production when:
- [ ] All 14 tasks complete
- [ ] Mobile + tablet + desktop layouts work
- [ ] prefers-reduced-motion respected
- [ ] WCAG AA color contrast verified
- [ ] Keyboard navigation works everywhere
- [ ] Screen reader / ARIA audit clean
- [ ] Lighthouse: accessibility ≥ 90, performance ≥ 80 on /today
- [ ] All component + E2E tests pass
- [ ] Final honesty audit clean — no fake content, all required fields present
- [ ] Verification report at `.hermes/plans/2026-06-01_frontend-v1-verification-report.md`
- [ ] Andy approves SHIP

After ship: Phase H buffer is reserved for post-launch fixes. V1.1 (AI engine, news integration, follow inventors, email customization) work happens after V1 lands in production and you've observed real usage.
