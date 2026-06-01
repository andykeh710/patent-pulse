# Frontend Overhaul — Phase F: Remaining Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the dark/premium aesthetic to every remaining authenticated surface so no white/generic-SaaS interior remains (admin excepted). Add the mandatory data-freshness components per spec §3.6. Differentiate /opportunity content from /expiry. Account page: real changes. Billing: dark theme only.

**Architecture:** Each surface is a visual refresh on top of its existing data flow — no new endpoints, no data-shape changes. The repeated pattern: replace `bg-white` with `bg-[var(--bg-base)]`, replace `border-gray-*` with `border-[var(--border-subtle)]`, replace chip pills with `<Pill>`, swap `bg-blue-100 text-blue-700` with token-based pills, ensure FreshnessBanner + SourceAttribution + LegalConfidenceBadge are present where spec §3.6 requires them.

**Tech Stack:** React, Next.js App Router, the Phase A primitives, existing data hooks.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §6, §3.6, §11.1 Phase F.

**Depends on:** Phase E gate passed.

---

## File Structure

```
frontend/src/app/(app)/trends/page.tsx                    # MODIFY
frontend/src/app/(app)/trends/[surface]/page.tsx          # MODIFY
frontend/src/app/(app)/trends/[surface]/[key]/page.tsx    # MODIFY
frontend/src/app/(app)/expiry/page.tsx                    # MODIFY
frontend/src/app/(app)/opportunity/page.tsx               # MODIFY
frontend/src/app/(app)/themes/page.tsx                    # MODIFY
frontend/src/app/(app)/themes/[id]/page.tsx               # MODIFY
frontend/src/app/(app)/companies/page.tsx                 # MODIFY (already partly from Phase C)
frontend/src/app/(app)/companies/[name]/page.tsx          # MODIFY (already from Phase C)
frontend/src/app/(app)/watchlist/page.tsx                 # MODIFY
frontend/src/app/(app)/search/page.tsx                    # MODIFY
frontend/src/app/(app)/account/page.tsx                   # MODIFY (already partly from Phase C)
frontend/src/app/(app)/account/billing/page.tsx           # MODIFY (dark theme only)
frontend/src/app/(auth)/login/page.tsx                    # MODIFY (light touch)
frontend/src/app/(auth)/login/verify/page.tsx             # MODIFY (light touch)
frontend/src/app/(auth)/unsubscribed/page.tsx             # MODIFY (light touch)

frontend/src/components/trends/TrendCard.tsx              # NEW (used on /trends + nested)
frontend/src/components/trends/MomentumSparkline.tsx      # NEW (small inline sparkline)
```

---

## Tasks

### Task 1: TrendCard + MomentumSparkline components

**Files:**
- Create: `frontend/src/components/trends/TrendCard.tsx`
- Create: `frontend/src/components/trends/MomentumSparkline.tsx`

- [ ] **Step 1: Implement MomentumSparkline (CSS-only, no D3)**

```typescript
interface Props {
  points: number[];  // weekly counts, oldest first
}

export function MomentumSparkline({ points }: Props) {
  if (points.length < 2) return null;
  const max = Math.max(...points, 1);
  const w = 80;
  const h = 24;
  const step = w / (points.length - 1);
  const path = points
    .map((v, i) => `${i === 0 ? "M" : "L"} ${i * step} ${h - (v / max) * h}`)
    .join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <path d={path} fill="none" stroke="var(--signal-blue)" strokeWidth="1.5" />
      <circle cx={(points.length - 1) * step} cy={h - (points[points.length - 1] / max) * h} r="2" fill="var(--signal-glow)" />
    </svg>
  );
}
```

- [ ] **Step 2: Implement TrendCard**

```typescript
import Link from "next/link";
import { Pill } from "@/components/ui/Pill";
import { MomentumSparkline } from "./MomentumSparkline";

interface Props {
  trend: {
    surface: string;
    key: string;
    label: string;
    count_4w: number;
    momentum_score: number;
    z_score?: number;
    top_assignees?: string[];
    weekly_counts?: number[];
  };
}

export function TrendCard({ trend }: Props) {
  return (
    <Link href={`/trends/${trend.surface}/${trend.key}`} className="block">
      <div className="rounded-xl bg-[var(--bg-glass)] backdrop-blur-md border border-[var(--border-subtle)] hover:border-[var(--signal-blue)]/40 p-4 transition-all hover:-translate-y-0.5">
        <div className="flex items-start justify-between mb-2">
          <Pill tone="signal">{trend.surface}</Pill>
          {trend.weekly_counts && <MomentumSparkline points={trend.weekly_counts} />}
        </div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)] line-clamp-2">{trend.label}</h3>
        <div className="mt-2 text-xs text-[var(--text-muted)]">
          {trend.count_4w} patents (4wk) · momentum {trend.momentum_score.toFixed(1)}
          {trend.z_score && <> · z={trend.z_score.toFixed(1)}</>}
        </div>
        {trend.top_assignees && trend.top_assignees.length > 0 && (
          <div className="mt-1 text-[10px] text-[var(--text-muted)] truncate">
            Top: {trend.top_assignees.slice(0, 3).join(", ")}
          </div>
        )}
      </div>
    </Link>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/trends/TrendCard.tsx frontend/src/components/trends/MomentumSparkline.tsx
git commit -m "feat(frontend): TrendCard + CSS-only MomentumSparkline"
```

---

### Task 2: Trends pages refresh

**Files:**
- Modify: `frontend/src/app/(app)/trends/page.tsx`
- Modify: `frontend/src/app/(app)/trends/[surface]/page.tsx`
- Modify: `frontend/src/app/(app)/trends/[surface]/[key]/page.tsx`

- [ ] **Step 1: Refresh trends index**

In `frontend/src/app/(app)/trends/page.tsx`:
- Replace existing trend list with grid of `<TrendCard>` components
- Add `<FreshnessBanner>` at top showing when trends were last computed
- Add `<SourceAttribution source="Computed from indexed patents" />` near results
- Replace any `bg-white` / `text-gray-*` with token-based classes
- Filter pills become `<Pill>` instances

- [ ] **Step 2: Refresh /trends/[surface]**

Same pattern. Surface-specific trends in a grid.

- [ ] **Step 3: Refresh /trends/[surface]/[key]**

Detail page for a single trend. Use PatentDetailHeader-like pattern (no tabs needed). Show:
- Trend label + metadata
- MomentumSparkline (large version)
- Top assignees as pill chips
- Patents in this trend as `<PatentCard>` grid
- FreshnessBanner + SourceAttribution

- [ ] **Step 4: Smoke-test**

Visit `/trends`, then `/trends/g06t`, then `/trends/g06t/specific-key`. All render with dark/premium aesthetic.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(app\)/trends/
git commit -m "refactor(frontend): trends pages dark/premium + TrendCard"
```

---

### Task 3: Expiry Radar refresh

**Files:**
- Modify: `frontend/src/app/(app)/expiry/page.tsx`

- [ ] **Step 1: Refresh layout**

- Header with title "Expiry Radar" + freshness banner
- **MANDATORY caveat banner** (per spec §3.6 + §6): "Verify with official registers before relying on expiry status." Always visible, non-collapsible. Use `Card variant="elevated"` with amber border.

```typescript
<Card variant="elevated" className="mb-6 border-[var(--warning)]/40">
  <div className="flex items-start gap-3">
    <span className="text-[var(--warning)]">⚠️</span>
    <p className="text-sm text-[var(--text-secondary)]">
      Verify with official registers before relying on expiry status. Invention Index 8 surfaces patterns from indexed data; it does not provide legal opinions.
    </p>
  </div>
</Card>
```

- Filter pills (status, confidence, etc.) become `<Pill>` instances
- Result cards: `bg-[var(--bg-glass)]` glass panel
- Add LegalConfidenceBadge on each result row

- [ ] **Step 2: Differentiate sections**

Per spec §6, Expiry has sections:
- Expiring Soon (90d)
- Recently Expired
- Likely Lapsed
- Revival Candidates
- High-Opportunity (filter view, links to /opportunity for the standalone)
- Needs Legal Verification

Use a tabbed nav at top (similar to patent detail tabs pattern).

- [ ] **Step 3: Smoke-test**

Visit `/expiry`. Caveat banner visible. Filter pills dark-themed. Results in glass-panel cards.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/expiry/page.tsx
git commit -m "refactor(frontend): Expiry Radar dark/premium + mandatory caveat banner"
```

---

### Task 4: Opportunity page differentiation

**Files:**
- Modify: `frontend/src/app/(app)/opportunity/page.tsx`

Per spec §6 + §2.1 decision 1 from earlier IA brainstorming: Opportunity = signal-driven, Expiry = timing-driven. The two must look and feel different.

- [ ] **Step 1: Reframe content**

Page header: "Opportunities" not "Opportunity scores".
Subtitle: "Commercial signals, market gaps, and emerging fields — independent of patent expiry."
Sort default: opportunity_score DESC.
Filters emphasize: commercial signal indicators (e.g., assignee filing surge, cross-industry potential, market whitespace) rather than expiry status.

- [ ] **Step 2: Visual differentiation**

- Trend snapshot panel showing top categories by opportunity score
- Result cards use `<PatentCard>` but with a different visual treatment for the opp score chip (maybe larger, more prominent)
- Optional: a "View timing-based opportunities →" link to /expiry to make the differentiation explicit

- [ ] **Step 3: Refresh styling**

Standard dark/premium pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/opportunity/page.tsx
git commit -m "refactor(frontend): Opportunity = signal-driven (differentiated from Expiry)"
```

---

### Task 5: Themes pages refresh

**Files:**
- Modify: `frontend/src/app/(app)/themes/page.tsx`
- Modify: `frontend/src/app/(app)/themes/[id]/page.tsx`

- [ ] **Step 1: Refresh themes index**

- Theme cards: `<Card variant="glass" interactive>` with theme name, patent count, "Following" indicator
- Use StarterTopics empty state for first-time users (already refreshed in Phase A)
- Subscribe button → "Follow Topic" (toggle)

- [ ] **Step 2: Refresh theme detail**

- Header with topic name + freshness + follow button
- Patents in this topic as `<PatentCard>` grid
- Related trends panel (top trends within this topic)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/themes/
git commit -m "refactor(frontend): themes (Topics) pages dark/premium refresh"
```

---

### Task 6: Companies index final polish

**Files:**
- Modify: `frontend/src/app/(app)/companies/page.tsx`

(Most of this work happened in Phase C. This task is final visual polish.)

- [ ] **Step 1: Verify dark theme applied throughout**

```bash
grep -E "bg-(white|gray)" frontend/src/app/\(app\)/companies/page.tsx
```

Expected: no output.

- [ ] **Step 2: Add freshness + source**

At the top:
```typescript
<FreshnessBanner updatedAt={lastIndexedAt} />
<SourceAttribution source="Computed from indexed patent data" />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/companies/page.tsx
git commit -m "refactor(frontend): companies index final polish (freshness + source)"
```

---

### Task 7: Companies detail final polish

**Files:**
- Modify: `frontend/src/app/(app)/companies/[name]/page.tsx`

- [ ] **Step 1: Header refresh**

Apply detail-page pattern (similar to PatentDetailHeader):
- Large company name + Follow button (already there from Phase C)
- Stats row: total patents, recent filings, top topics
- Tabs (optional): Recent / Top Opportunities / By Topic

- [ ] **Step 2: Patent list uses new PatentCard**

Already gets this benefit since PatentCard is the shared component.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/companies/\[name\]/page.tsx
git commit -m "refactor(frontend): company detail page dark/premium"
```

---

### Task 8: Watchlist refresh

**Files:**
- Modify: `frontend/src/app/(app)/watchlist/page.tsx`

- [ ] **Step 1: Apply dark theme + use PatentCard**

- Page header: "Saved patents"
- List of saved patents rendered as `<PatentCard>` grid
- Empty state from `<EmptyState>` (refreshed in Phase A) with brand voice
- Bulk actions (remove all, export) styled with `<Button>`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(app\)/watchlist/page.tsx
git commit -m "refactor(frontend): watchlist dark/premium"
```

---

### Task 9: Search refresh

**Files:**
- Modify: `frontend/src/app/(app)/search/page.tsx`

- [ ] **Step 1: Apply dark theme**

- Search input: large, glass-panel surface, focus-visible ring with `--signal-glow`
- Filters pane on left: pills + dropdowns dark-themed
- Results: `<PatentCard>` grid
- Empty/no-results state: brand-voice copy from COPY

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(app\)/search/page.tsx
git commit -m "refactor(frontend): search dark/premium + new PatentCard"
```

---

### Task 10: Account page final polish

**Files:**
- Modify: `frontend/src/app/(app)/account/page.tsx`

(Persona field already from Phase C. This task is general polish.)

- [ ] **Step 1: Apply dark form styling**

- All inputs: `bg-[var(--bg-glass)] border border-[var(--border-subtle)] text-[var(--text-primary)]`
- Labels: `text-[var(--text-muted)]` uppercase tracking-wider
- Save buttons: primary variant

- [ ] **Step 2: Add follows summary section**

```typescript
<div className="mt-8">
  <h3 className="text-sm font-semibold mb-3">Your follows</h3>
  <div className="grid grid-cols-2 gap-4">
    <Card variant="glass">
      <div className="text-xs text-[var(--text-muted)] mb-2">Topics</div>
      {/* List or count of followed topics */}
      <Link href="/themes" className="text-xs text-[#a5b4fc] underline">Manage on Topics page →</Link>
    </Card>
    <Card variant="glass">
      <div className="text-xs text-[var(--text-muted)] mb-2">Companies</div>
      {/* List or count of followed companies */}
      <Link href="/companies" className="text-xs text-[#a5b4fc] underline">Manage on Companies page →</Link>
    </Card>
  </div>
</div>
```

- [ ] **Step 3: GDPR "Delete account" section**

If not already present, ensure the GDPR deletion endpoint (L3 from earlier) is exposed via a button on this page, with confirmation dialog:

```typescript
<Card variant="elevated" className="mt-8 border-red-500/30">
  <h3 className="text-sm font-semibold text-red-300 mb-2">Delete account</h3>
  <p className="text-xs text-[var(--text-muted)] mb-3">
    Permanently delete your account and all associated data. This cannot be undone.
  </p>
  <Button variant="danger" onClick={confirmAndDelete}>Delete my account</Button>
</Card>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/account/page.tsx
git commit -m "refactor(frontend): account page dark form + follows summary + GDPR delete"
```

---

### Task 11: Billing page — dark theme only

**Files:**
- Modify: `frontend/src/app/(app)/account/billing/page.tsx`

Per spec §2.1 decision 10: dark theme only, no new UI, no fake state.

- [ ] **Step 1: Replace light styling tokens with dark**

- Background: `bg-[var(--bg-base)]`
- Cards/sections: glass panel
- Subscription details (current tier, next billing date, etc.) — preserve existing data flow, just re-skin
- Manage Subscription button → still calls Stripe portal

- [ ] **Step 2: Do not add new UI**

Do NOT add fake invoices, fake usage charts, fake tier comparison UI, or anything that implies billing functionality that doesn't already exist on the backend.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/account/billing/page.tsx
git commit -m "refactor(frontend): billing page dark theme only (no new UI)"
```

---

### Task 12: Auth pages light touch

**Files:**
- Modify: `frontend/src/app/(auth)/login/page.tsx`
- Modify: `frontend/src/app/(auth)/login/verify/page.tsx`
- Modify: `frontend/src/app/(auth)/unsubscribed/page.tsx`

- [ ] **Step 1: Apply dark base**

- Background `bg-[var(--bg-base)]`
- Centered card on the page using `<Card variant="elevated">`
- Logo via `<BrandMark>` at top
- Inputs styled as in account page
- Submit buttons primary variant

Each file is small (~50-100 lines). Light touch is sufficient.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(auth\)/
git commit -m "refactor(frontend): auth pages dark theme (light touch)"
```

---

### Task 13: Verify no white surfaces remain (except admin)

- [ ] **Step 1: Grep for light-mode signatures**

```bash
grep -rn "bg-white\|bg-gray-50\|bg-gray-100\|text-gray-90" frontend/src/app/\(app\)/ frontend/src/app/\(auth\)/ frontend/src/app/\(marketing\)/ 2>/dev/null | grep -v ".test.tsx" | grep -v admin
```

Expected: zero matches in non-admin paths. The marketing pages may have intentional white surfaces (preserve those — per §13 out-of-scope).

- [ ] **Step 2: Visit every authenticated route in browser**

```
/today, /patents, /patents/<id>, /trends, /trends/g06t, /expiry, /opportunity, /themes, /themes/<id>, /companies, /companies/<name>, /watchlist, /search, /account, /account/billing
```

Verify each is dark/premium. No surprise white surfaces.

- [ ] **Step 3: Document any remaining light-theme leaks**

Some shared components may still have light-theme defaults. List them; fix or note for Phase G polish.

---

### Task 14: Phase F gate verification

- [ ] **Step 1: Honesty audit on every surface**

For each surface visited in Task 13 Step 2:
- Does it have FreshnessBanner where data is displayed?
- Does it have SourceAttribution where appropriate?
- For Expiry: caveat banner present and prominent?
- For Opportunity: differentiated content from Expiry?
- No fake data anywhere?

- [ ] **Step 2: All tests pass**

```bash
cd frontend && npm test
docker compose exec backend pytest backend/tests/
```

- [ ] **Step 3: Build clean**

```bash
cd frontend && npm run build
```

Expected: no TS errors, no warnings beyond pre-existing.

- [ ] **Step 4: Write gate report**

`.hermes/plans/2026-06-01_frontend-phase-f-gate.md` with surface-by-surface checklist, honesty audit results, test results, build result.

- [ ] **Step 5: Hand off to Andy**

---

## Phase F Gate

Phase G does not begin until:
- [ ] All 14 tasks complete
- [ ] No light-mode signatures (`bg-white`, etc.) in non-admin authenticated paths
- [ ] Every data surface has Freshness + Source visible
- [ ] Expiry has mandatory caveat banner
- [ ] Opportunity content differentiated from Expiry
- [ ] No fake data on any surface
- [ ] All tests pass, build clean
- [ ] Gate report exists and reviewed by Andy
- [ ] Andy gives go-ahead
