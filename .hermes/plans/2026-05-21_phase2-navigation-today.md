# Phase 2 — Navigation Rebuild + Today Page Implementation Plan

> **For Hermes:** Implement task-by-task, verifying at each step.

**Goal:** Replace the stats dashboard with an editorial Today page and reorganize nav to tell a product story.

**Architecture:** New `/today` page consuming existing hooks (useOpportunityList, useHotTrends, usePriorityWatch, useSuppliers, useFreshness). Nav restructuring in NavSidebar.tsx. Dashboard route redirects to /today.

**Tech Stack:** Next.js 15 App Router, SWR for data fetching, Tailwind CSS, existing hook/api layer.

**Data already available (no backend changes needed):**
- `useOpportunityList({ tab, sort, page_size })` — top scored patents
- `useHotTrends(surface, limit)` — hot trends with z-scores/growth
- `usePriorityWatch(bucket, pageSize)` — expiring_soon/recent/all
- `useSuppliers({ sort_by, page_size })` — top companies by score/activity
- `useFreshness()` — system freshness timestamps
- `useTrendsSummary()` — total trends/convergence/cliffs counts

---

## Task 1: Create Today page skeleton

**Objective:** Create the new `/today` route with header and FreshnessBanner, placeholder sections.

**Files:**
- Create: `frontend/src/app/today/page.tsx`

**Step 1: Create the page file**

```tsx
"use client";

import { FreshnessBanner } from "@/components/ui/FreshnessBanner";

export default function TodayPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Today</h1>
        <FreshnessBanner className="mt-2" />
        <p className="text-gray-600 mt-1">
          Your daily patent intelligence briefing
        </p>
      </div>

      <div className="space-y-8">
        {/* Section 1: Your Patent Pulse (placeholder) */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Patent Pulse</h2>
          <p className="text-sm text-gray-500">
            Saved topics and custom alerts will appear here. 
            Topics are coming in a future update.
          </p>
        </div>

        {/* Section 2: Top Opportunities */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Opportunities</h2>
          <p className="text-sm text-gray-400">Loading...</p>
        </div>

        {/* Section 3: Emerging Trends */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Emerging Trends</h2>
          <p className="text-sm text-gray-400">Loading...</p>
        </div>

        {/* Section 4: Expiring Opportunities */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Expiring Opportunities</h2>
          <p className="text-sm text-gray-400">Loading...</p>
        </div>

        {/* Section 5: Companies Moving */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Companies Moving</h2>
          <p className="text-sm text-gray-400">Loading...</p>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: builds successfully, `/today` appears in route list.

**Step 3: Verify page renders**

Run: `cd frontend && npm run dev`
Visit: http://localhost:3000/today
Expected: page renders with header and 5 placeholder sections

**Step 4: Commit**

```bash
git add frontend/src/app/today/page.tsx
git commit -m "feat: add Today page skeleton with placeholder sections"
```

---

## Task 2: Build Top Opportunities section

**Objective:** Show top 5 highest-scored patents with title, score, assignee, and link to patent detail.

**Files:**
- Modify: `frontend/src/app/today/page.tsx`

**Step 1: Add imports and data fetching**

Add at top of page:
```tsx
import Link from "next/link";
import { useOpportunityList } from "@/hooks/useOpportunity";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { Skeleton } from "@/components/ui/Skeleton";
```

Add hook call inside component:
```tsx
const { data: topOpps, isLoading: topOppsLoading } = useOpportunityList({
  tab: "top",
  sort: "opportunity_score",
  page_size: 5,
});
```

**Step 2: Replace placeholder with real content**

Replace the "Top Opportunities" placeholder section with:
```tsx
<section className="bg-white rounded-lg border border-gray-200 p-6">
  <div className="flex items-center justify-between mb-4">
    <h2 className="text-lg font-semibold text-gray-900">Top Opportunities</h2>
    <Link href="/opportunity" className="text-sm text-primary-600 hover:text-primary-800">
      View all →
    </Link>
  </div>

  {topOppsLoading ? (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded" />)}
    </div>
  ) : !topOpps?.items?.length ? (
    <p className="text-sm text-gray-400 text-center py-8">
      No opportunity data yet. Run opportunity scoring first.
    </p>
  ) : (
    <div className="space-y-2">
      {topOpps.items.slice(0, 5).map((item) => (
        <Link
          key={item.id}
          href={`/patents/${item.id}`}
          className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 truncate">
              {item.title || "Untitled patent"}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {item.assignees?.[0] || "Unknown"} · {item.doc_id}
            </p>
          </div>
          <OpportunityScoreBadge score={item.opportunity_score} size="sm" />
        </Link>
      ))}
    </div>
  )}
</section>
```

**Step 3: Verify**

Run: `cd frontend && npm run build`
Expected: no TypeScript errors, section type-checks against existing `useOpportunityList` types.

---

## Task 3: Build Emerging Trends section

**Objective:** Show top 5 hot trends with z-scores and surface badges.

**Files:**
- Modify: `frontend/src/app/today/page.tsx`

**Step 1: Add imports**

```tsx
import { useHotTrends } from "@/hooks/useTrends";
import { Badge } from "@/components/ui/Badge";
```

Add hook call:
```tsx
const { data: hotTrends, isLoading: trendsLoading } = useHotTrends(undefined, 5);
```

**Step 2: Replace the Emerging Trends placeholder**

Replace with:
```tsx
<section className="bg-white rounded-lg border border-gray-200 p-6">
  <div className="flex items-center justify-between mb-4">
    <h2 className="text-lg font-semibold text-gray-900">Emerging Trends</h2>
    <Link href="/trends" className="text-sm text-primary-600 hover:text-primary-800">
      View all →
    </Link>
  </div>

  {trendsLoading ? (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-14 w-full rounded" />)}
    </div>
  ) : !hotTrends?.items?.length ? (
    <p className="text-sm text-gray-400 text-center py-8">
      No trend data yet. Run weekly trend computation first.
    </p>
  ) : (
    <div className="space-y-2">
      {hotTrends.items.slice(0, 5).map((item) => (
        <div
          key={`${item.surface}-${item.key}`}
          className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Badge variant="default" size="sm">{item.surface}</Badge>
              <p className="text-sm font-medium text-gray-900 truncate">{item.key}</p>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              {item.count_4w} patents (4wk) · z-score {item.z_score.toFixed(1)}
            </p>
          </div>
          <div className={`text-sm font-semibold ${item.growth_pct > 0 ? "text-emerald-600" : "text-red-600"}`}>
            {item.growth_pct > 0 ? "+" : ""}{item.growth_pct.toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  )}
</section>
```

**Step 3: Verify**

Run: `cd frontend && npm run build`

---

## Task 4: Build Expiring Opportunities section

**Objective:** Show top 5 expiring patents with urgency.

**Files:**
- Modify: `frontend/src/app/today/page.tsx`

**Step 1: Add imports**

```tsx
import { usePriorityWatch } from "@/hooks/usePatents";
import { formatDate, pluralize } from "@/lib/utils";
```

Add hook:
```tsx
const { data: expiring, isLoading: expiringLoading } = usePriorityWatch("expiring_soon", 5);
```

**Step 2: Replace section**

```tsx
<section className="bg-white rounded-lg border border-gray-200 p-6">
  <div className="flex items-center justify-between mb-4">
    <h2 className="text-lg font-semibold text-gray-900">Expiring Opportunities</h2>
    <Link href="/expiry" className="text-sm text-primary-600 hover:text-primary-800">
      View all →
    </Link>
  </div>

  {expiringLoading ? (
    <div className="space-y-3">
      {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded" />)}
    </div>
  ) : !expiring?.items?.length ? (
    <p className="text-sm text-gray-400 text-center py-8">
      No expiring patents found in the 5-year window.
    </p>
  ) : (
    <div className="space-y-2">
      {expiring.items.slice(0, 5).map((item) => (
        <Link
          key={item.id}
          href={`/patents/${item.id}`}
          className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 truncate">
              {item.title || "Untitled patent"}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {item.assignees?.[0] || "Unknown"} ·{" "}
              {item.estimated_expiry_date ? (
                <>
                  Expires {formatDate(item.estimated_expiry_date)}
                  {item.days_until_expiry != null && (
                    <> · {item.days_until_expiry} {pluralize(item.days_until_expiry, "day")}</>
                  )}
                </>
              ) : (
                "No expiry data"
              )}
            </p>
          </div>
          {item.opportunity_score != null && (
            <OpportunityScoreBadge score={item.opportunity_score} size="sm" />
          )}
        </Link>
      ))}
    </div>
  )}
</section>
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`

---

## Task 5: Build Companies Moving section

**Objective:** Show top 5 companies by recent activity (patent count).

**Files:**
- Modify: `frontend/src/app/today/page.tsx`

**Step 1: Add import**

```tsx
import { useSuppliers } from "@/hooks/useSuppliers";
```

Add hook:
```tsx
const { data: companies, isLoading: companiesLoading } = useSuppliers({
  sort_by: "patent_count",
  sort_order: "desc",
  min_patent_count: 2,
  page_size: 5,
});
```

**Step 2: Replace section**

```tsx
<section className="bg-white rounded-lg border border-gray-200 p-6">
  <div className="flex items-center justify-between mb-4">
    <h2 className="text-lg font-semibold text-gray-900">Companies Moving</h2>
    <Link href="/companies" className="text-sm text-primary-600 hover:text-primary-800">
      View all →
    </Link>
  </div>

  {companiesLoading ? (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-14 w-full rounded" />)}
    </div>
  ) : !companies?.items?.length ? (
    <p className="text-sm text-gray-400 text-center py-8">
      No company data available yet.
    </p>
  ) : (
    <div className="space-y-2">
      {companies.items.slice(0, 5).map((item) => (
        <Link
          key={item.name}
          href={`/companies/${encodeURIComponent(item.name)}`}
          className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {item.active_patent_count} active · {item.technology_area_count} tech areas
              {item.country ? ` · ${item.country}` : ""}
            </p>
          </div>
          <span className={`text-sm font-semibold ${item.supplier_score >= 60 ? "text-green-600" : item.supplier_score >= 35 ? "text-yellow-600" : "text-gray-500"}`}>
            {item.supplier_score}
          </span>
        </Link>
      ))}
    </div>
  )}
</section>
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`

---

## Task 6: Polish Your Patent Pulse placeholder

**Objective:** Replace the bare placeholder with a more inviting one that points to future topics functionality.

**Files:**
- Modify: `frontend/src/app/today/page.tsx`

**Step 1: Replace the placeholder section**

Replace the first "Your Patent Pulse" section with:
```tsx
<section className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg border border-primary-200 p-6">
  <div className="flex items-start gap-4">
    <div className="p-3 bg-white rounded-lg shadow-sm">
      <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    </div>
    <div>
      <h2 className="text-lg font-semibold text-gray-900">Your Patent Pulse</h2>
      <p className="text-sm text-gray-600 mt-1">
        Custom topics, saved searches, and personalized alerts are coming soon. 
        When ready, your tracked technology areas and matched patents will appear here.
      </p>
    </div>
  </div>
</section>
```

**Step 2: Verify**

Run: `cd frontend && npm run build`

---

## Task 7: Rebuild navigation structure

**Objective:** Reorganize sidebar to reflect the product story.

**Files:**
- Modify: `frontend/src/app/NavSidebar.tsx`

**Step 1: Rewrite NAV_ITEMS**

Replace the entire `NAV_ITEMS` array with:
```tsx
const NAV_ITEMS = [
  {
    href: "/today",
    label: "Today",
    icon: "M13 10V3L4 14h7v7l9-11h-7z",
  },
  {
    href: "/opportunity",
    label: "Opportunities",
    icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
  },
  {
    href: "/trends",
    label: "Trends",
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  {
    href: "/expiry",
    label: "Expiring Patents",
    icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    href: "/companies",
    label: "Companies",
    icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  },
  {
    href: "/search",
    label: "Search",
    icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  },
  {
    href: "/themes",
    label: "Themes",
    icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z",
  },
  {
    href: "/patents",
    label: "Patents",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  },
  {
    href: "/watchlist",
    label: "Watchlist",
    icon: "M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z",
  },
  {
    href: "/about",
    label: "About / Limitations",
    icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];
```

**Step 2: Update active detection for /today**

The `isActive` function currently treats `/dashboard` as the root. Update it:
```tsx
const isActive = (href: string) => {
  if (href === "/today") return pathname === "/" || pathname === "/today";
  return pathname.startsWith(href);
};
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: no errors, all route links valid.

---

## Task 8: Add redirect from /dashboard to /today

**Objective:** Old /dashboard URL redirects to new /today.

**Files:**
- Modify: `frontend/next.config.ts`

**Step 1: Add redirect rule**

In the `redirects()` function, add:
```ts
{
  source: "/dashboard",
  destination: "/today",
  permanent: true,
},
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: builds cleanly, `/dashboard` redirects work.

---

## Task 9: Update root page to redirect

**Objective:** Landing at `/` goes to `/today` instead of `/dashboard`.

**Files:**
- Modify: `frontend/src/app/page.tsx`

**Step 1: Read current page.tsx**

Read the current root page to see if it's a redirect.

**Step 2: Make it a redirect or replace content**

If it's not a redirect, change to:
```tsx
import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/today");
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`

---

## Task 10: Responsive polish

**Objective:** Ensure Today page and nav work on tablet/mobile widths.

**Files:**
- Modify: `frontend/src/app/today/page.tsx` (verify section layouts)
- Verify: `frontend/src/app/layout.tsx` (check mobile sidebar behavior)

**Step 1: Audit Today page sections**

Each section already uses standard Tailwind grid/flex. The "Top Opportunities" rows use `flex` with `min-w-0` truncation — they will reflow naturally. No changes needed for sections.

**Step 2: Check layout for mobile sidebar**

Read `layout.tsx` and verify it handles narrow screens. If sidebar is always fixed, add a responsive class:
```tsx
// In layout.tsx sidebar wrapper
<div className="hidden lg:block">  {/* Only show sidebar on large screens */}
```

But this may already be handled. Inspect before changing.

**Step 3: Verify**

Run: `cd frontend && npm run build`
Then: `npm run dev` and test at 375px width in browser dev tools.

---

## Task 11: Full build + manual verification

**Objective:** Confirm everything builds, routes work, and the product flows naturally.

**Step 1: Full build**

```bash
cd frontend && npm run build
```
Expected: 0 errors, `/today` in route list.

**Step 2: Manual smoke test (if backend running)**

```bash
# Start backend if not running
cd backend && docker-compose up -d

# Start frontend
cd frontend && npm run dev
```

Visit and verify:
- `/today` — renders with 5 sections, data flowing
- `/` — redirects to `/today`
- `/dashboard` — redirects to `/today`
- Nav sidebar — correct order, all links work
- Click through to individual pages from Today page links

**Step 3: Commit**

```bash
git add frontend/src/app/today/page.tsx frontend/src/app/NavSidebar.tsx frontend/src/app/page.tsx frontend/next.config.ts
git commit -m "feat: Phase 2 — Today page with editorial dashboard and nav rebuild"
```

---

## Verification Checklist

- [ ] `/today` page renders with all 5 sections
- [ ] Top Opportunities shows real patents with scores, links work
- [ ] Emerging Trends shows hot trends with z-scores and growth %
- [ ] Expiring Opportunities shows soon-to-expire patents with days count
- [ ] Companies Moving shows top assignees with scores, links to company profiles
- [ ] All sections have loading skeletons
- [ ] All sections have empty states with guidance
- [ ] FreshnessBanner shows system timestamps
- [ ] Navigation order: Today → Opportunities → Trends → Expiring → Companies → Search → Themes → Patents → Watchlist → About
- [ ] `/` redirects to `/today`
- [ ] `/dashboard` redirects to `/today`
- [ ] All section "View all →" links go to the correct pages
- [ ] `npm run build` passes with 0 errors
