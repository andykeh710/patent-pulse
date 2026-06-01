# Frontend Overhaul — Phase D: Today Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Today command center on the Phase A/B/C substrate. Hybrid layout: stats row + briefing feed (left) + right sidebar (My Follows / Quick Actions / Saved Patents). All 6 item types render with required fields. First-time and sparse states handled. Loading and error states branded.

**Architecture:** Today is composed of three top-level sections (StatsRow, BriefingFeed, Sidebar) inside a grid. BriefingFeed consumes `/api/v1/today/briefing` and renders BriefingItems. Sidebar widgets each consume their own SWR hook so failures don't cascade. State machine: loading → ready → empty (sparse) → error.

**Tech Stack:** React, Next.js client components, SWR, the Phase A primitives, the Phase B endpoints.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §4, §11.1 Phase D.

**Depends on:** Phase C gate passed.

---

## File Structure

```
frontend/src/lib/hooks/useTodayBriefing.ts          # NEW
frontend/src/lib/hooks/useWatchlistRecent.ts        # NEW (uses existing /api/v1/watchlist with limit)

frontend/src/components/today/StatsRow.tsx          # NEW
frontend/src/components/today/BriefingFeed.tsx      # NEW
frontend/src/components/today/MyFollowsWidget.tsx   # NEW
frontend/src/components/today/QuickActionsWidget.tsx # NEW
frontend/src/components/today/SavedPatentsWidget.tsx # NEW
frontend/src/components/today/TodayHeader.tsx       # NEW

frontend/src/app/(app)/today/page.tsx               # MODIFY — full rewrite
```

---

## Tasks

### Task 1: useTodayBriefing hook

**Files:**
- Create: `frontend/src/lib/hooks/useTodayBriefing.ts`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add types**

In `frontend/src/lib/types.ts`:

```typescript
export type BriefingItemType = "trend" | "notable" | "company" | "expiring" | "foryou" | "news";

export interface Freshness {
  updated_at: string;  // ISO
  relative: string;    // e.g., "2h ago"
}

export interface Confidence {
  level: "high" | "medium" | "low";
  caveat?: string;
}

export interface BriefingItem {
  type: BriefingItemType;
  label: string;
  title: string;
  subtext?: string;
  reason: string;
  source: string;
  freshness: Freshness;
  confidence?: Confidence;
  href?: string;
}

export interface BriefingResponse {
  items: BriefingItem[];
  total: number;
  generated_at: string;
}
```

- [ ] **Step 2: Implement hook**

```typescript
"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { BriefingResponse } from "@/lib/types";

export function useTodayBriefing() {
  const { data, error, isLoading } = useSWR<BriefingResponse>(
    "/api/v1/today/briefing",
    api.get,
    { refreshInterval: 5 * 60 * 1000 }  // refresh every 5 min
  );
  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    generatedAt: data?.generated_at,
    isLoading,
    error,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/hooks/useTodayBriefing.ts frontend/src/lib/types.ts
git commit -m "feat(frontend): useTodayBriefing hook + BriefingItem types"
```

---

### Task 2: useWatchlistRecent hook

**Files:**
- Create: `frontend/src/lib/hooks/useWatchlistRecent.ts`

- [ ] **Step 1: Implement**

```typescript
"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

interface WatchlistItem {
  id: string;
  publication_number: string;
  assignee: string;
  title: string;
}

export function useWatchlistRecent(limit = 3) {
  const { data, error, isLoading } = useSWR<{ items: WatchlistItem[]; total: number }>(
    `/api/v1/watchlist?limit=${limit}`,
    api.get
  );
  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/hooks/useWatchlistRecent.ts
git commit -m "feat(frontend): useWatchlistRecent hook for Today sidebar"
```

---

### Task 3: TodayHeader component

**Files:**
- Create: `frontend/src/components/today/TodayHeader.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { useAuth } from "@/lib/AuthContext";
import { usePersona } from "@/lib/hooks/usePersona";
import { useFollowedCompanies } from "@/lib/hooks/useFollowedCompanies";
import { useThemes } from "@/lib/hooks/useThemes";  // existing hook
import { LiveIndicator } from "@/components/ui/LiveIndicator";

export function TodayHeader({ lastScanRelative }: { lastScanRelative?: string }) {
  const { user } = useAuth();
  const { persona } = usePersona();
  const { companies } = useFollowedCompanies();
  const { themes } = useThemes();

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const firstName = user?.email?.split("@")[0] ?? "there";
  const personaLabel = persona === "operator" ? "Operator" : persona === "investor" ? "Investor" : persona === "curious" ? "Curious" : null;

  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[#a5b4fc]">{today}</div>
        <div className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
          Good morning, {firstName}
        </div>
        <div className="mt-0.5 text-xs text-[var(--text-muted)]">
          Filtered by your {themes.length} topics, {companies.length} companies
          {personaLabel ? `, and ${personaLabel} persona` : ""}
        </div>
      </div>
      <LiveIndicator status="live" label={lastScanRelative ? `last scan ${lastScanRelative}` : undefined} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/today/TodayHeader.tsx
git commit -m "feat(frontend): TodayHeader greeting + filter line + live indicator"
```

---

### Task 4: StatsRow component

**Files:**
- Create: `frontend/src/components/today/StatsRow.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { StatTile } from "@/components/ui/StatTile";
import { usePatentStats } from "@/lib/hooks/usePatents";  // existing
import { useFollowedCompanies } from "@/lib/hooks/useFollowedCompanies";
import { useThemes } from "@/lib/hooks/useThemes";

export function StatsRow() {
  const { stats } = usePatentStats();
  const { companies } = useFollowedCompanies();
  const { themes } = useThemes();

  const totalFollows = companies.length + themes.length;
  const weekDelta = stats?.patents_this_week ?? 0;
  const totalIndex = stats?.total_patents ?? 0;
  const expiringCount = stats?.expiring_90d_count ?? 0;

  return (
    <div className="grid grid-cols-4 gap-3 mb-6">
      <StatTile label="Index size" value={totalIndex} subtext="USPTO · EPO · WIPO" />
      <StatTile label="New this week" value={weekDelta} accent="signal" subtext="filings" />
      <StatTile label="Your follows" value={totalFollows} subtext={`${themes.length} topics · ${companies.length} companies`} />
      <StatTile label="Expiring 90d" value={expiringCount} accent="warning" subtext="high-opp in your topics" />
    </div>
  );
}
```

Note: `expiring_90d_count` may need to be added to the existing patent stats endpoint. If not present, add it in the backend (small follow-up to Phase B).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/today/StatsRow.tsx
git commit -m "feat(frontend): StatsRow with 4 stat tiles"
```

---

### Task 5: BriefingFeed component

**Files:**
- Create: `frontend/src/components/today/BriefingFeed.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { BriefingItem as BriefingItemComponent } from "@/components/ui/BriefingItem";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useTodayBriefing } from "@/lib/hooks/useTodayBriefing";
import { COPY } from "@/lib/brand";

export function BriefingFeed() {
  const { items, total, isLoading, error } = useTodayBriefing();

  if (isLoading) {
    return (
      <div>
        <SectionHeader label="Your briefing" />
        <div className="space-y-3">
          {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-20" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <SectionHeader label="Your briefing" />
        <div className="rounded-xl bg-[var(--bg-glass)] border border-red-500/30 p-6 text-center">
          <p className="text-sm text-[var(--text-secondary)]">Couldn't load your briefing.</p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">Try again in a moment.</p>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div>
        <SectionHeader label="Your briefing" />
        <div className="rounded-xl bg-[var(--bg-glass)] border border-[var(--border-subtle)] p-6 text-center">
          <p className="text-sm text-[var(--text-secondary)]">{COPY.emptyThreshold}</p>
        </div>
      </div>
    );
  }

  // Sparse state: 1-4 items
  const sparse = items.length <= 4;

  return (
    <div>
      <SectionHeader label="Your briefing" meta={`${total} items · weighted by relevance to your follows`} />
      <div className="space-y-3">
        {items.map((item, i) => (
          <BriefingItemComponent key={`${item.type}-${i}`} {...item} />
        ))}
      </div>
      {sparse && (
        <div className="mt-6 border-t border-[var(--border-subtle)] pt-4 text-center">
          <p className="text-[10px] uppercase tracking-[0.12em] text-[var(--text-muted)]">More to come</p>
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            Your briefing will grow as patents are filed and indexed against your follows. New items appear daily.
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/today/BriefingFeed.tsx
git commit -m "feat(frontend): BriefingFeed with loading/error/empty/sparse states"
```

---

### Task 6: MyFollowsWidget

**Files:**
- Create: `frontend/src/components/today/MyFollowsWidget.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { useFollowedCompanies } from "@/lib/hooks/useFollowedCompanies";
import { useThemes } from "@/lib/hooks/useThemes";

export function MyFollowsWidget() {
  const { companies } = useFollowedCompanies();
  const { themes } = useThemes();

  return (
    <Card variant="glass">
      <div className="text-[10px] uppercase tracking-[0.1em] text-[#a5b4fc] mb-3">My follows</div>

      <div className="mb-3">
        <div className="text-[10px] text-[var(--text-muted)] mb-1">Topics</div>
        <div className="flex flex-wrap gap-1.5">
          {themes.slice(0, 4).map(t => (
            <Link key={t.id} href={`/themes/${t.id}`}>
              <Pill tone="signal">{t.name}</Pill>
            </Link>
          ))}
          {themes.length > 4 && <Pill tone="muted">+{themes.length - 4}</Pill>}
        </div>
      </div>

      <div className="mb-3">
        <div className="text-[10px] text-[var(--text-muted)] mb-1">Companies</div>
        <div className="flex flex-wrap gap-1.5">
          {companies.slice(0, 4).map(c => (
            <Link key={c.company_normalized_name} href={`/companies/${encodeURIComponent(c.display_name)}`}>
              <Pill tone="default">{c.display_name}</Pill>
            </Link>
          ))}
          {companies.length > 4 && <Pill tone="muted">+{companies.length - 4}</Pill>}
        </div>
      </div>

      <Link href="/companies" className="text-[10px] text-[#a5b4fc] underline">+ Follow more</Link>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/today/MyFollowsWidget.tsx
git commit -m "feat(frontend): MyFollowsWidget (Today right sidebar)"
```

---

### Task 7: QuickActionsWidget

**Files:**
- Create: `frontend/src/components/today/QuickActionsWidget.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { usePersona } from "@/lib/hooks/usePersona";
import type { Persona } from "@/lib/types";

const ACTIONS_BY_PERSONA: Record<Persona, { href: string; label: string }[]> = {
  operator: [
    { href: "/expiry", label: "Explore expiring in your topics" },
    { href: "/trends", label: "View all trends" },
    { href: "/search", label: "Search prior art" },
  ],
  investor: [
    { href: "/trends", label: "View momentum charts" },
    { href: "/companies", label: "See company breakouts" },
    { href: "/trends", label: "Browse trends" },
  ],
  curious: [
    { href: "/patents", label: "This week's notable patents" },
    { href: "/patents", label: "Surprising filings" },
    { href: "/trends", label: "Trend explorer" },
  ],
};

export function QuickActionsWidget() {
  const { persona } = usePersona();
  const actions = ACTIONS_BY_PERSONA[persona ?? "operator"];

  return (
    <Card variant="glass">
      <div className="text-[10px] uppercase tracking-[0.1em] text-[#a5b4fc] mb-3">Quick actions</div>
      <div className="space-y-2">
        {actions.map((a, i) => (
          <Link key={i} href={a.href} className="block text-xs text-[#c7d2fe] hover:text-[var(--text-primary)]">
            → {a.label}
          </Link>
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/today/QuickActionsWidget.tsx
git commit -m "feat(frontend): QuickActionsWidget with persona-driven actions"
```

---

### Task 8: SavedPatentsWidget

**Files:**
- Create: `frontend/src/components/today/SavedPatentsWidget.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { useWatchlistRecent } from "@/lib/hooks/useWatchlistRecent";

export function SavedPatentsWidget() {
  const { items, total, isLoading } = useWatchlistRecent(3);

  return (
    <Card variant="glass">
      <div className="text-[10px] uppercase tracking-[0.1em] text-[#a5b4fc] mb-3">Saved patents</div>
      {isLoading && <div className="text-xs text-[var(--text-muted)]">Loading…</div>}
      {!isLoading && items.length === 0 && (
        <div className="text-xs text-[var(--text-muted)]">
          Patents you save will appear here. <Link href="/patents" className="text-[#a5b4fc] underline">Browse patents</Link>
        </div>
      )}
      {items.length > 0 && (
        <>
          <div className="space-y-2">
            {items.map(p => (
              <Link key={p.id} href={`/patents/${p.id}`} className="block py-1.5 border-t border-[var(--border-subtle)] first:border-t-0">
                <div className="text-xs text-[var(--text-primary)] font-mono tabular-nums">{p.publication_number}</div>
                <div className="text-[10px] text-[var(--text-muted)]">{p.assignee}</div>
                <div className="text-[10px] text-[var(--text-muted)] line-clamp-1">{p.title}</div>
              </Link>
            ))}
          </div>
          {total > 3 && (
            <Link href="/watchlist" className="block mt-3 text-[10px] text-[#a5b4fc] underline">
              View all {total} →
            </Link>
          )}
        </>
      )}
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/today/SavedPatentsWidget.tsx
git commit -m "feat(frontend): SavedPatentsWidget (Today right sidebar)"
```

---

### Task 9: Today page composition (full rewrite)

**Files:**
- Modify: `frontend/src/app/(app)/today/page.tsx`

- [ ] **Step 1: Replace existing page**

```typescript
"use client";
import { TodayHeader } from "@/components/today/TodayHeader";
import { StatsRow } from "@/components/today/StatsRow";
import { BriefingFeed } from "@/components/today/BriefingFeed";
import { MyFollowsWidget } from "@/components/today/MyFollowsWidget";
import { QuickActionsWidget } from "@/components/today/QuickActionsWidget";
import { SavedPatentsWidget } from "@/components/today/SavedPatentsWidget";

export default function TodayPage() {
  return (
    <div>
      <TodayHeader />
      <StatsRow />
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
        <div>
          <BriefingFeed />
        </div>
        <aside className="space-y-4">
          <MyFollowsWidget />
          <QuickActionsWidget />
          <SavedPatentsWidget />
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Smoke-test in browser**

Visit `http://localhost:3000/today` with an authenticated user who has topics and companies followed.

Expected:
- Header with greeting + freshness indicator
- 4 stat tiles with counters counting up
- Left: briefing feed with N items, each showing reason/source/freshness
- Right: 3 widgets visible

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/today/page.tsx
git commit -m "feat(frontend): Today page composed of new Phase D components"
```

---

### Task 10: Verify all 6 item types render correctly

- [ ] **Step 1: Visit /today and observe item types**

In the rendered briefing feed, identify which item types are present. Expected at least:
- 1 filing trend (if any trend has momentum in user's topics)
- 1 expiring opportunity
- 1 notable patent
- 1 company move (if a followed company has filing surge)
- 1 foryou stub (always renders)
- 1 news placeholder (always renders)

- [ ] **Step 2: Verify required fields are visible**

For each item, confirm in the DOM:
- `reason` line is visible
- `freshness.relative` is visible
- `source` is visible (or in tooltip)
- `confidence.caveat` is visible if non-high (especially on expiring items: "Verify with official registers")

If any item is missing a required field, that's a backend bug — go back to Phase B Task 9 to fix.

- [ ] **Step 3: Verify "For you" copy is honest**

The foryou item should NOT say "AI" anywhere. It should say "For you — early personalization" and "Full AI recommendations are coming later."

- [ ] **Step 4: Verify news slot is placeholder, not fake content**

The news item should explicitly say "V1.1 — news linking slot reserved" or equivalent honest placeholder copy. No fabricated headlines.

- [ ] **Step 5: Document findings**

If all 6 types render correctly and honestly: PASS.

If any fail: log a bug for Phase G to address. Don't proceed until critical (reason / source / freshness missing, or fake content) issues are fixed.

---

### Task 11: First-time user experience

- [ ] **Step 1: Verify wizard still triggers correctly**

Create a fresh test user (or null out persona/topics/companies). Log in.

Expected: PersonaWizard appears (from Phase C). After completion → arrive at Today with personalized briefing.

- [ ] **Step 2: Verify "no follows yet" sparse-but-not-broken state**

User finishes wizard but skips topics + companies (i.e., picks persona only).

Expected: Today renders with:
- Stats row showing 0 follows
- Briefing feed shows system-default items (top trends, top expirations across all data — not per-topic)
- "You haven't picked topics yet — pick topics to make this yours" CTA banner above briefing

Update BriefingFeed if needed:

```typescript
{themes.length === 0 && (
  <div className="mb-4 rounded-xl bg-[var(--signal-blue)]/10 border border-[var(--signal-blue)]/30 p-4 text-sm text-[var(--text-secondary)]">
    Pick topics to make this yours. <Link href="/themes" className="underline">Browse topics →</Link>
  </div>
)}
```

- [ ] **Step 3: Commit any updates**

```bash
git add frontend/src/components/today/BriefingFeed.tsx
git commit -m "feat(frontend): first-time CTA banner when user has no topics"
```

---

### Task 12: Mobile / responsive audit

- [ ] **Step 1: Test at 375px width**

Open browser dev tools, set viewport to 375x812 (iPhone X). Visit /today.

Expected:
- Stats row stacks 2x2 (not all 4 in a row)
- Sidebar moves below main feed (not right side)
- Briefing items stay readable

Likely fixes if not working:
- Change `grid-cols-4` to `grid-cols-2 md:grid-cols-4`
- Change `lg:grid-cols-[1fr_280px]` correctly handles mobile (single column by default)

- [ ] **Step 2: Test at 768px width (tablet)**

Sidebar can stay on right at this width. Stats can be 4 in a row.

- [ ] **Step 3: Commit any responsive fixes**

```bash
git add frontend/src/app/\(app\)/today/page.tsx frontend/src/components/today/StatsRow.tsx
git commit -m "fix(frontend): Today mobile/tablet responsive layout"
```

---

### Task 13: prefers-reduced-motion audit

- [ ] **Step 1: Toggle reduced motion in DevTools and visit /today**

Expected:
- Counters jump to final value (no count-up)
- LiveIndicator scanning state does not pulse
- Any briefing-item hover transitions are still
- No background drift animations

- [ ] **Step 2: Fix any motion violations**

Common fix: add `motion-reduce:animate-none` to animated elements.

- [ ] **Step 3: Commit**

```bash
git commit -m "fix(frontend): prefers-reduced-motion respect across Today screen"
```

---

### Task 14: Phase D gate verification

- [ ] **Step 1: Honesty audit**

Walk through every briefing item visible on /today. Each must have:
- `reason` visible
- `source` visible or in tooltip
- `freshness.relative` visible
- If expiring: caveat visible
- No fake content (no fabricated patents, news, or "AI" language on foryou)

If any item fails, it's a backend or copy bug. Fix and re-verify.

- [ ] **Step 2: All states reachable**

- [ ] Loading state (open with slow network throttle, see skeletons)
- [ ] Error state (block /api/v1/today/briefing in network tab, see error panel)
- [ ] Empty state (clear all topics + follows from DB, see CTA banner)
- [ ] Sparse state (only 1-4 items, see "More to come" divider)
- [ ] Normal state (5+ items)
- [ ] First-time state (persona null → wizard)

- [ ] **Step 3: Tests**

```bash
cd frontend && npm test
```

Expected: all pass.

- [ ] **Step 4: Lighthouse on /today**

```bash
npx lighthouse http://localhost:3000/today --view --preset=desktop --only-categories=accessibility,performance
```

Expected: accessibility ≥ 90, performance ≥ 80.

- [ ] **Step 5: Write gate report**

`.hermes/plans/2026-06-01_frontend-phase-d-gate.md` with honesty audit results, all states reachable, test results, Lighthouse scores. GO/BLOCKED for Phase E.

- [ ] **Step 6: Hand off to Andy**

---

## Phase D Gate

Phase E does not begin until:
- [ ] All 14 tasks complete
- [ ] All 6 briefing item types render with required fields
- [ ] No fake content anywhere (no AI claims on foryou, no fake news)
- [ ] All states reachable (loading / error / empty / sparse / normal / first-time)
- [ ] Mobile and tablet layouts work
- [ ] prefers-reduced-motion respected
- [ ] Lighthouse accessibility ≥ 90, performance ≥ 80
- [ ] Gate report exists and reviewed by Andy
- [ ] Andy gives go-ahead
