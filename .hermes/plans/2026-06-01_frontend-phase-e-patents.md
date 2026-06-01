# Frontend Overhaul — Phase E: Patent Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the PatentCard component (used on every list page) to the dark/premium aesthetic, and decompose the 956-line `patents/[id]/page.tsx` into a clean Header + 4 tab components. Preserve all existing AI panels (AISummaryPanel, OpportunityBreakdown, etc.) inside the new structure.

**Architecture:** PatentCard becomes a glass-panel card with scan-hover and richer affordances. Patent detail page becomes an orchestrator (~120 lines) that loads data and renders Header + sticky TabBar + active tab component. Each tab is its own file (<200 lines) using existing AI panels as building blocks. Tab state is URL-driven via `?tab=` query param for shareability.

**Tech Stack:** React, Next.js App Router, the Phase A primitives, the existing AI panel components.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §5, §11.1 Phase E.

**Depends on:** Phase D gate passed.

---

## File Structure

```
frontend/src/components/patents/PatentCard.tsx                # MODIFY — full refresh
frontend/src/components/patents/PatentCard.test.tsx           # MODIFY/EXISTS — refresh assertions

frontend/src/components/patents/PatentDetailHeader.tsx        # NEW
frontend/src/components/patents/PatentDetailTabs.tsx          # EXISTING — refresh, keep as tab bar
frontend/src/components/patents/tabs/SummaryTab.tsx           # NEW
frontend/src/components/patents/tabs/OpportunityTab.tsx       # NEW
frontend/src/components/patents/tabs/FamilyTab.tsx            # NEW
frontend/src/components/patents/tabs/SourceTab.tsx            # NEW

frontend/src/app/(app)/patents/[id]/page.tsx                  # MODIFY — 956 → ~120 lines, orchestrator
frontend/src/app/(app)/patents/page.tsx                       # MODIFY — use new PatentCard

frontend/src/components/patents/FamilyPanel.tsx               # NEW (referenced by FamilyTab)
```

Existing AI panels stay where they are and are imported into the new tab files unchanged:
- `AISummaryPanel.tsx`
- `OpportunityBreakdown.tsx`
- `OpportunityNarrativePanel.tsx`
- `OpportunityScoreBadge.tsx`
- `WhyNowPanel.tsx`
- `ClaimsPanel.tsx`
- `RiskFlagsBadge.tsx`
- `TagsPanel.tsx`
- `TrendSnapshotPanel.tsx`
- `UsageSignalsPanel.tsx`
- `AssigneeIntelligencePanel.tsx`
- `ExternalPatentLinks.tsx`
- `LinkedInPostPanel.tsx`
- `LegalConfidenceBadge.tsx`
- `AISourceFooter.tsx`

---

## Tasks

### Task 1: Read the current patent detail file

**Files:**
- Read: `frontend/src/app/(app)/patents/[id]/page.tsx`

- [ ] **Step 1: Catalog the page structure**

```bash
wc -l frontend/src/app/\(app\)/patents/\[id\]/page.tsx
grep -n "^function\|^export\|^const " frontend/src/app/\(app\)/patents/\[id\]/page.tsx
```

Identify the major rendered sections in the existing file. They likely map to:
- Header (title, assignee, dates, action buttons)
- Summary section (AISummaryPanel, WhyNowPanel)
- Opportunity section (OpportunityBreakdown, RiskFlags, OpportunityNarrative)
- Family / citations
- Source / claims / drawings / external links

- [ ] **Step 2: Map sections to new tabs**

Produce a simple mapping in a scratch note:

```
Current page section | New tab
---|---
Header (title, etc.) | PatentDetailHeader (no tab)
AISummaryPanel | SummaryTab
WhyNowPanel | SummaryTab
TagsPanel | SummaryTab
OpportunityBreakdown | OpportunityTab
OpportunityNarrativePanel | OpportunityTab
RiskFlagsBadge | OpportunityTab
OpportunityScoreBadge | OpportunityTab + Header
TrendSnapshotPanel | OpportunityTab
UsageSignalsPanel | OpportunityTab
AssigneeIntelligencePanel | OpportunityTab
LinkedInPostPanel | OpportunityTab
LegalConfidenceBadge | Header + FamilyTab
Family / citations data | FamilyTab
ClaimsPanel | SourceTab
Drawings / figure | SourceTab + Header (thumb)
ExternalPatentLinks | SourceTab + Header
AISourceFooter | bottom of each tab
```

No commit needed — this is preparation.

---

### Task 2: PatentCard refresh

**Files:**
- Modify: `frontend/src/components/patents/PatentCard.tsx`
- Modify: `frontend/src/components/patents/PatentCard.test.tsx`

- [ ] **Step 1: Update tests to assert new design**

```typescript
import { render, screen } from "@testing-library/react";
import { PatentCard } from "./PatentCard";

const patent = {
  id: "p1",
  publication_number: "US12,345,678",
  office: "USPTO",
  title: "Autonomous battery thermal management",
  assignee: "NVIDIA",
  publication_date: "2026-04-12",
  opportunity_score: 92,
  figure_page_url: "https://example.com/fig",
  has_summary: true,
  expiry_date: "2041-04-12",
};

describe("PatentCard", () => {
  it("renders office badge", () => {
    render(<PatentCard patent={patent} />);
    expect(screen.getByText("USPTO")).toBeInTheDocument();
  });

  it("renders mono publication number", () => {
    const { container } = render(<PatentCard patent={patent} />);
    expect(container.querySelector(".font-mono")).toHaveTextContent("US12,345,678");
  });

  it("renders opportunity score chip", () => {
    render(<PatentCard patent={patent} />);
    expect(screen.getByText(/opp 92/i)).toBeInTheDocument();
  });

  it("renders affordances when present", () => {
    render(<PatentCard patent={patent} />);
    expect(screen.getByText(/figures/i)).toBeInTheDocument();
    expect(screen.getByText(/summary/i)).toBeInTheDocument();
    expect(screen.getByText(/expires/i)).toBeInTheDocument();
  });

  it("hides affordances when absent", () => {
    const minimal = { ...patent, figure_page_url: undefined, has_summary: false, expiry_date: undefined };
    render(<PatentCard patent={minimal} />);
    expect(screen.queryByText(/figures/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npm test -- PatentCard.test
```

- [ ] **Step 3: Implement new PatentCard**

```typescript
import Link from "next/link";
import { Pill } from "@/components/ui/Pill";
import type { PatentListItem } from "@/lib/types";

interface PatentCardProps {
  patent: PatentListItem;
}

const officeColors: Record<string, "signal" | "default" | "positive"> = {
  USPTO: "signal",
  EPO: "default",
  WIPO: "positive",
};

export function PatentCard({ patent }: PatentCardProps) {
  const officeTone = officeColors[patent.office] ?? "default";

  return (
    <Link href={`/patents/${patent.id}`} className="block group">
      <div className="rounded-xl bg-[var(--bg-glass)] backdrop-blur-md border border-[var(--border-subtle)] hover:border-[var(--signal-blue)]/40 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[var(--signal-blue)]/10 p-4 scan-hover relative overflow-hidden">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <Pill tone={officeTone}>{patent.office}</Pill>
            <span className="text-[11px] text-[var(--text-muted)] font-mono tabular-nums">
              {patent.publication_number}
            </span>
          </div>
          {typeof patent.opportunity_score === "number" && (
            <span className="rounded-md px-2 py-0.5 text-[10px] font-mono tabular-nums bg-gradient-to-br from-[var(--score-high)]/20 to-[var(--signal-blue)]/15 border border-[var(--score-high)]/30 text-[#86efac]">
              opp {patent.opportunity_score}
            </span>
          )}
        </div>
        <div className="text-sm font-semibold text-[var(--text-primary)] line-clamp-2 leading-snug">
          {patent.title}
        </div>
        <div className="mt-1 text-[11px] text-[var(--text-muted)]">
          {patent.assignee} · {patent.publication_date}
        </div>
        <div className="mt-2.5 flex items-center justify-between">
          <div className="flex gap-2 text-[10px] text-[#c4b5fd]">
            {patent.figure_page_url && <span>📷 figures</span>}
            {patent.has_summary && <span>📄 summary</span>}
            {patent.expiry_date && (
              <span>⏳ expires {new Date(patent.expiry_date).getFullYear()}</span>
            )}
          </div>
          <span className="text-[10px] text-[#a5b4fc] group-hover:text-[var(--text-primary)] transition-colors">
            View →
          </span>
        </div>
      </div>
    </Link>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- PatentCard.test
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/patents/PatentCard.tsx frontend/src/components/patents/PatentCard.test.tsx
git commit -m "refactor(frontend): PatentCard dark/premium with scan-hover + affordances"
```

---

### Task 3: PatentDetailHeader

**Files:**
- Create: `frontend/src/components/patents/PatentDetailHeader.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { Pill } from "@/components/ui/Pill";
import { Button } from "@/components/ui/Button";
import { OpportunityScoreBadge } from "./OpportunityScoreBadge";
import { LegalConfidenceBadge } from "./LegalConfidenceBadge";
import { FollowButton } from "@/components/companies/FollowButton";
import { normalizeCompanyName } from "@/lib/utils";
import type { PatentDetail } from "@/lib/types";

interface Props {
  patent: PatentDetail;
  onSaveToggle: () => void;
  isSaved: boolean;
}

export function PatentDetailHeader({ patent, onSaveToggle, isSaved }: Props) {
  return (
    <div className="mb-6">
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-[var(--text-primary)] leading-tight">
            {patent.title}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Pill tone="signal">{patent.office}</Pill>
            <span className="text-sm text-[var(--text-muted)] font-mono tabular-nums">
              {patent.publication_number}
            </span>
            {patent.status && <LegalConfidenceBadge status={patent.status} />}
          </div>
          <div className="mt-2 text-sm text-[var(--text-muted)]">
            {patent.assignee} · Filed {patent.filing_date} · Published {patent.publication_date}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant={isSaved ? "secondary" : "primary"} onClick={onSaveToggle} size="sm">
              {isSaved ? "✓ Saved" : "Save patent"}
            </Button>
            {patent.assignee && (
              <FollowButton
                displayName={patent.assignee}
                normalizedName={normalizeCompanyName(patent.assignee)}
                size="md"
              />
            )}
            {patent.external_url && (
              <a href={patent.external_url} target="_blank" rel="noreferrer">
                <Button variant="ghost" size="sm">View source ↗</Button>
              </a>
            )}
          </div>
        </div>
        {patent.figure_page_url && (
          <a href={patent.figure_page_url} target="_blank" rel="noreferrer" className="hidden md:block flex-shrink-0">
            <div className="w-44 h-44 rounded-lg bg-[var(--bg-glass)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--text-muted)] text-xs hover:border-[var(--signal-blue)]/40">
              View figures →
            </div>
          </a>
        )}
        {typeof patent.opportunity_score === "number" && (
          <div className="hidden md:block">
            <OpportunityScoreBadge score={patent.opportunity_score} size="lg" />
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/patents/PatentDetailHeader.tsx
git commit -m "feat(frontend): PatentDetailHeader extracted from monolith"
```

---

### Task 4: PatentDetailTabs (tab bar)

**Files:**
- Modify (or create if not present): `frontend/src/components/patents/PatentDetailTabs.tsx`

- [ ] **Step 1: Implement tab bar**

```typescript
"use client";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

export type TabKey = "summary" | "opportunity" | "family" | "source";

const TABS: { key: TabKey; label: string }[] = [
  { key: "summary", label: "Summary" },
  { key: "opportunity", label: "Opportunity" },
  { key: "family", label: "Family" },
  { key: "source", label: "Source" },
];

export function PatentDetailTabs({ active }: { active: TabKey }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const setTab = (key: TabKey) => {
    const newParams = new URLSearchParams(params);
    newParams.set("tab", key);
    router.push(`${pathname}?${newParams.toString()}`);
  };

  return (
    <nav className="sticky top-14 z-30 mb-6 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/80 backdrop-blur-xl">
      <div className="flex gap-1">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-3 text-sm transition-colors ${
              active === t.key
                ? "text-[var(--text-primary)] border-b-2 border-[var(--signal-blue)]"
                : "text-[var(--text-muted)] hover:text-[var(--text-secondary)] border-b-2 border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/patents/PatentDetailTabs.tsx
git commit -m "feat(frontend): PatentDetailTabs (Summary/Opportunity/Family/Source)"
```

---

### Task 5: SummaryTab

**Files:**
- Create: `frontend/src/components/patents/tabs/SummaryTab.tsx`

- [ ] **Step 1: Implement (compose existing panels)**

```typescript
import { AISummaryPanel } from "../AISummaryPanel";
import { WhyNowPanel } from "../WhyNowPanel";
import { ClaimsPanel } from "../ClaimsPanel";
import { TagsPanel } from "../TagsPanel";
import { AISourceFooter } from "../AISourceFooter";
import type { PatentDetail } from "@/lib/types";

export function SummaryTab({ patent }: { patent: PatentDetail }) {
  return (
    <div className="space-y-6">
      <AISummaryPanel patent={patent} />
      {patent.why_now && <WhyNowPanel patent={patent} />}
      {patent.tags && patent.tags.length > 0 && <TagsPanel tags={patent.tags} />}
      <ClaimsPanel patent={patent} preview />
      <AISourceFooter patent={patent} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/patents/tabs/SummaryTab.tsx
git commit -m "feat(frontend): SummaryTab composing existing AI panels"
```

---

### Task 6: OpportunityTab

**Files:**
- Create: `frontend/src/components/patents/tabs/OpportunityTab.tsx`

- [ ] **Step 1: Implement**

```typescript
import { OpportunityBreakdown } from "../OpportunityBreakdown";
import { OpportunityNarrativePanel } from "../OpportunityNarrativePanel";
import { RiskFlagsBadge } from "../RiskFlagsBadge";
import { TrendSnapshotPanel } from "../TrendSnapshotPanel";
import { UsageSignalsPanel } from "../UsageSignalsPanel";
import { AssigneeIntelligencePanel } from "../AssigneeIntelligencePanel";
import { LinkedInPostPanel } from "../LinkedInPostPanel";
import { AISourceFooter } from "../AISourceFooter";
import type { PatentDetail } from "@/lib/types";

export function OpportunityTab({ patent }: { patent: PatentDetail }) {
  return (
    <div className="space-y-6">
      <OpportunityBreakdown patent={patent} />
      <OpportunityNarrativePanel patent={patent} />
      {patent.risk_flags && patent.risk_flags.length > 0 && (
        <RiskFlagsBadge flags={patent.risk_flags} />
      )}
      <TrendSnapshotPanel patent={patent} />
      <UsageSignalsPanel patent={patent} />
      <AssigneeIntelligencePanel patent={patent} />
      <LinkedInPostPanel patent={patent} />
      <AISourceFooter patent={patent} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/patents/tabs/OpportunityTab.tsx
git commit -m "feat(frontend): OpportunityTab composing existing panels"
```

---

### Task 7: FamilyPanel + FamilyTab

**Files:**
- Create: `frontend/src/components/patents/FamilyPanel.tsx`
- Create: `frontend/src/components/patents/tabs/FamilyTab.tsx`

- [ ] **Step 1: Implement FamilyPanel**

```typescript
import { Card } from "@/components/ui/Card";
import type { PatentDetail } from "@/lib/types";

export function FamilyPanel({ patent }: { patent: PatentDetail }) {
  const family = patent.family_members ?? [];
  const fwdCitations = patent.forward_citations ?? [];
  const backCitations = patent.backward_citations ?? [];

  return (
    <div className="space-y-6">
      <Card variant="glass">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Family members</h3>
        {family.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No family members recorded for this patent yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {family.map(m => (
              <li key={m.publication_number} className="text-xs font-mono tabular-nums text-[var(--text-secondary)]">
                {m.publication_number} <span className="text-[var(--text-muted)]">· {m.office}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card variant="glass">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Forward citations ({fwdCitations.length})</h3>
        {fwdCitations.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No forward citations recorded.</p>
        ) : (
          <ul className="space-y-1.5">
            {fwdCitations.slice(0, 10).map(c => (
              <li key={c.publication_number} className="text-xs font-mono tabular-nums">{c.publication_number}</li>
            ))}
          </ul>
        )}
      </Card>
      <Card variant="glass">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Backward citations ({backCitations.length})</h3>
        {backCitations.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No backward citations recorded.</p>
        ) : (
          <ul className="space-y-1.5">
            {backCitations.slice(0, 10).map(c => (
              <li key={c.publication_number} className="text-xs font-mono tabular-nums">{c.publication_number}</li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Implement FamilyTab**

```typescript
import { FamilyPanel } from "../FamilyPanel";
import { AISourceFooter } from "../AISourceFooter";
import type { PatentDetail } from "@/lib/types";

export function FamilyTab({ patent }: { patent: PatentDetail }) {
  return (
    <div className="space-y-6">
      <FamilyPanel patent={patent} />
      <AISourceFooter patent={patent} />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/patents/FamilyPanel.tsx frontend/src/components/patents/tabs/FamilyTab.tsx
git commit -m "feat(frontend): FamilyPanel + FamilyTab with honest empty states"
```

---

### Task 8: SourceTab

**Files:**
- Create: `frontend/src/components/patents/tabs/SourceTab.tsx`

- [ ] **Step 1: Implement**

```typescript
import { Card } from "@/components/ui/Card";
import { ClaimsPanel } from "../ClaimsPanel";
import { ExternalPatentLinks } from "../ExternalPatentLinks";
import { AISourceFooter } from "../AISourceFooter";
import type { PatentDetail } from "@/lib/types";

export function SourceTab({ patent }: { patent: PatentDetail }) {
  return (
    <div className="space-y-6">
      <Card variant="glass">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Abstract</h3>
        {patent.abstract ? (
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{patent.abstract}</p>
        ) : (
          <p className="text-xs text-[var(--text-muted)]">No abstract available for this patent.</p>
        )}
      </Card>

      <ClaimsPanel patent={patent} full />

      {patent.figure_page_url && (
        <Card variant="glass">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Drawings</h3>
          <a href={patent.figure_page_url} target="_blank" rel="noreferrer" className="text-xs text-[#a5b4fc] underline">
            View official drawings ↗
          </a>
          <p className="mt-2 text-[10px] text-[var(--text-muted)]">
            Drawings link to the official source. We do not host or re-serve patent figures.
          </p>
        </Card>
      )}

      <ExternalPatentLinks patent={patent} />

      <AISourceFooter patent={patent} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/patents/tabs/SourceTab.tsx
git commit -m "feat(frontend): SourceTab (abstract / claims / drawings link / external)"
```

---

### Task 9: Rewrite patents/[id]/page.tsx as orchestrator

**Files:**
- Modify: `frontend/src/app/(app)/patents/[id]/page.tsx`

- [ ] **Step 1: Replace the 956-line file with the orchestrator**

```typescript
"use client";
import { useParams, useSearchParams } from "next/navigation";
import { usePatentDetail } from "@/lib/hooks/usePatents";  // existing
import { useWatchlistToggle } from "@/lib/hooks/useWatchlist";  // existing
import { PatentDetailHeader } from "@/components/patents/PatentDetailHeader";
import { PatentDetailTabs, type TabKey } from "@/components/patents/PatentDetailTabs";
import { SummaryTab } from "@/components/patents/tabs/SummaryTab";
import { OpportunityTab } from "@/components/patents/tabs/OpportunityTab";
import { FamilyTab } from "@/components/patents/tabs/FamilyTab";
import { SourceTab } from "@/components/patents/tabs/SourceTab";
import { Skeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";

const VALID_TABS: TabKey[] = ["summary", "opportunity", "family", "source"];

export default function PatentDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab") as TabKey | null;
  const activeTab: TabKey = requested && VALID_TABS.includes(requested) ? requested : "summary";

  const { patent, isLoading, error } = usePatentDetail(params.id);
  const { isSaved, toggle } = useWatchlistToggle(params.id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-12" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (error || !patent) {
    return (
      <div className="rounded-xl bg-[var(--bg-glass)] border border-red-500/30 p-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">Couldn't load this patent.</p>
      </div>
    );
  }

  return (
    <div>
      <FreshnessBanner updatedAt={patent.last_enriched_at} />
      <PatentDetailHeader patent={patent} onSaveToggle={toggle} isSaved={isSaved} />
      <PatentDetailTabs active={activeTab} />
      {activeTab === "summary" && <SummaryTab patent={patent} />}
      {activeTab === "opportunity" && <OpportunityTab patent={patent} />}
      {activeTab === "family" && <FamilyTab patent={patent} />}
      {activeTab === "source" && <SourceTab patent={patent} />}
    </div>
  );
}
```

- [ ] **Step 2: Verify line count**

```bash
wc -l frontend/src/app/\(app\)/patents/\[id\]/page.tsx
```

Expected: < 150 lines (target: ~120). If higher, something didn't decompose properly.

- [ ] **Step 3: Smoke-test in browser**

Visit `http://localhost:3000/patents/<real-id>`. All four tabs reachable via tab clicks. URL updates with `?tab=opportunity` etc.

- [ ] **Step 4: Try a few representative patents**

Pick 5 patents from the DB with varying data completeness:
- One with all fields (summary, claims, figures, family, citations, opportunity)
- One missing summary
- One missing claims
- One missing figures
- One with limited data overall

Verify each tab renders for each, with honest empty states where data is missing.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(app\)/patents/\[id\]/page.tsx
git commit -m "refactor(frontend): patents/[id] orchestrator (956 → ~120 lines)"
```

---

### Task 10: Update patents list page

**Files:**
- Modify: `frontend/src/app/(app)/patents/page.tsx`

- [ ] **Step 1: Update the list to use new PatentCard**

The PatentCard import is unchanged; just verify the list uses it. Replace any custom inline card markup with `<PatentCard patent={p} />`. Replace any `bg-white` background with dark-theme classes.

If filters are present, refresh their styling with the Phase A primitives.

- [ ] **Step 2: Smoke-test**

Visit `/patents`. List renders with dark/premium cards. Hover state shows scan-sweep and lift.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/patents/page.tsx
git commit -m "refactor(frontend): patents list uses refreshed PatentCard"
```

---

### Task 11: Phase E gate verification

- [ ] **Step 1: Verify decomposition**

```bash
wc -l frontend/src/components/patents/tabs/*.tsx frontend/src/components/patents/PatentDetailHeader.tsx frontend/src/app/\(app\)/patents/\[id\]/page.tsx
```

Expected: no file > 200 lines. Orchestrator < 150.

- [ ] **Step 2: Run 5 representative patents**

For each of the 5 patents from Task 9 Step 4, visit each of its 4 tabs. Note any tab that renders broken or with raw error.

- [ ] **Step 3: Test PatentCard hover state**

Visit `/patents` (or any list page). Hover a card. Verify scan-sweep visible, lift visible, gradient border visible.

- [ ] **Step 4: Test in /watchlist (uses PatentCard)**

Visit `/watchlist` with at least 1 saved patent. Cards render correctly.

- [ ] **Step 5: Run tests**

```bash
cd frontend && npm test
```

Expected: all pass.

- [ ] **Step 6: prefers-reduced-motion check**

Toggle reduced motion. Verify scan-sweep doesn't animate, lift doesn't transform.

- [ ] **Step 7: Write gate report**

`.hermes/plans/2026-06-01_frontend-phase-e-gate.md` with file-size verification, 5 representative-patent walkthrough results, test results.

- [ ] **Step 8: Hand off to Andy**

---

## Phase E Gate

Phase F does not begin until:
- [ ] All 11 tasks complete
- [ ] patents/[id]/page.tsx is < 150 lines (orchestrator only)
- [ ] No tab component > 200 lines
- [ ] 5 representative patents render correctly across all 4 tabs
- [ ] PatentCard hover state correct
- [ ] All tests pass
- [ ] prefers-reduced-motion respected
- [ ] Gate report exists and reviewed by Andy
- [ ] Andy gives go-ahead
