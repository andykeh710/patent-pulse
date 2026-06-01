# Frontend Overhaul — Phase A: Foundation + Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the design foundation — color tokens, Geist typography, 8 new UI primitives, 6 refreshed components, and a dark/premium app shell with new nav — so every subsequent phase has a stable visual base to build on.

**Architecture:** A two-layer design system. CSS variables in `tokens.css` are the single source of truth and are consumable from anywhere (SVG, CSS modules, inline styles). Tailwind config mirrors them so utility classes stay ergonomic. Primitives in `frontend/src/components/ui/` each have one responsibility, take typed props, and follow a consistent file shape. The app shell at `(app)/layout.tsx` is dark by default; every page beneath inherits.

**Tech Stack:** Next.js 15 App Router, Tailwind CSS, TypeScript, Geist Sans + Geist Mono via `next/font/google`, IntersectionObserver for animated counters, no new dependencies beyond Geist.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §3, §11.1 Phase A.

**Depends on:** Phase 0 preflight report exists, all blockers cleared, Andy has given go-ahead.

---

## File Structure

```
frontend/src/styles/tokens.css                              # NEW — design tokens
frontend/src/app/layout.tsx                                 # MODIFY — import tokens.css, set Geist fonts
frontend/src/app/globals.css                                # MODIFY — import tokens.css, audit component classes
frontend/src/app/(app)/layout.tsx                           # MODIFY — dark shell + new nav
frontend/tailwind.config.ts                                 # MODIFY — confirm tokens mirror tokens.css

frontend/src/components/ui/Card.tsx                         # NEW — glass-panel surface
frontend/src/components/ui/StatTile.tsx                     # NEW — Today stats row tile
frontend/src/components/ui/BriefingItem.tsx                 # NEW — feed item wrapper
frontend/src/components/ui/Counter.tsx                      # NEW — animated number
frontend/src/components/ui/Pill.tsx                         # NEW — inline chip
frontend/src/components/ui/Button.tsx                       # NEW — refresh if present, gradient primary
frontend/src/components/ui/LiveIndicator.tsx                # NEW — pulsing-dot status
frontend/src/components/ui/SectionHeader.tsx                # NEW — page section heading

frontend/src/components/ui/Badge.tsx                        # MODIFY — dark-theme audit
frontend/src/components/ui/EmptyState.tsx                   # MODIFY — brand voice from COPY
frontend/src/components/ui/Skeleton.tsx                     # MODIFY — dark-theme variant
frontend/src/components/ui/StarterTopics.tsx                # MODIFY — dark-theme refresh
frontend/src/components/ui/FreshnessBanner.tsx              # MODIFY — dark-theme refresh
frontend/src/components/ui/SourceAttribution.tsx            # MODIFY — dark-theme refresh

frontend/src/components/nav/TopNav.tsx                      # NEW — top bar with logo + nav items
frontend/src/components/nav/AccountDropdown.tsx             # NEW — user dropdown
frontend/src/components/nav/BrandMark.tsx                   # NEW — "InventionIndex8" + 8 pill

frontend/src/app/(app)/dev/components/page.tsx              # NEW — dev showcase page for primitive review
```

Each component file is ~50–150 lines, one responsibility, typed props. No file should exceed 200 lines in this phase.

---

## Tasks

### Task 1: Create tokens.css

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/app/layout.tsx` (import the tokens file)

- [ ] **Step 1: Create the tokens file**

Write `frontend/src/styles/tokens.css` with this exact content:

```css
/* Invention Index 8 — design tokens. Single source of truth for colors. */

:root {
  /* Base surfaces */
  --bg-base: #0A0E27;
  --bg-elevated: #11162A;
  --bg-glass: rgba(255, 255, 255, 0.04);
  --bg-glass-strong: rgba(255, 255, 255, 0.06);
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.16);

  /* Text */
  --text-primary: #E8ECF7;
  --text-secondary: #C7D2FE;
  --text-muted: #94A3B8;
  --text-disabled: #64748B;

  /* Signal */
  --signal-blue: #6366F1;
  --signal-violet: #8B5CF6;
  --signal-cyan: #06B6D4;
  --signal-glow: #818CF8;

  /* Semantic */
  --score-high: #34D399;
  --score-medium: #F59E0B;
  --score-low: #94A3B8;
  --warning: #F59E0B;

  /* Briefing item-type accents */
  --type-trend: var(--signal-blue);
  --type-notable: var(--score-high);
  --type-company: #7DD3FC;
  --type-expiring: var(--warning);
  --type-foryou: var(--signal-violet);
  --type-news: var(--signal-violet);
}
```

- [ ] **Step 2: Import tokens.css in the root layout**

Open `frontend/src/app/layout.tsx`. At the top, add the import after the existing `globals.css` import:

```typescript
import "@/styles/tokens.css";
```

If `globals.css` is not yet imported at the root layout, also add `import "./globals.css";`.

- [ ] **Step 3: Verify the file loads in dev**

Run:
```bash
docker compose up -d frontend
# wait 10s
curl -s http://localhost:3000 | grep -o "tokens" || echo "tokens.css not in HTML head"
```

The class file should appear in the rendered HTML's `<head>`. If not, the import path is wrong.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/tokens.css frontend/src/app/layout.tsx
git commit -m "feat(frontend): add design tokens (tokens.css) for II8 dark/premium palette"
```

(Reminder per memory rule: Andy commits, not Hermes. Hermes prepares the diff; Andy runs the commit. The command above is the suggested message format for Andy.)

---

### Task 2: Set up Geist Sans + Geist Mono

**Files:**
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Add Geist imports**

In `frontend/src/app/layout.tsx`, add at the top:

```typescript
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
```

- [ ] **Step 2: Install Geist package if not present**

Run:
```bash
cd frontend
cat package.json | grep -q "\"geist\":" || npm install geist
```

(Andy: pre-approved per spec §12 — Geist is the only allowed new dep.)

- [ ] **Step 3: Apply font variables to root html**

In the same file, modify the root `<html>` element:

```typescript
return (
  <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
    <body>{children}</body>
  </html>
);
```

- [ ] **Step 4: Wire the CSS variables into globals.css**

Open `frontend/src/app/globals.css`. After the existing imports, add:

```css
@layer base {
  html {
    font-family: var(--font-geist-sans), system-ui, sans-serif;
  }
  .font-mono, code, kbd, samp, pre {
    font-family: var(--font-geist-mono), ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
  }
}
```

- [ ] **Step 5: Verify rendering in browser**

Restart frontend container. Visit `http://localhost:3000`. Open browser devtools → Computed font on body. Expected: `Geist`, not `system-ui`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): wire Geist Sans + Geist Mono via next/font/google"
```

---

### Task 3: Card component

**Files:**
- Create: `frontend/src/components/ui/Card.tsx`
- Create: `frontend/src/components/ui/Card.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/Card.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>hello</Card>);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("applies glass variant by default", () => {
    const { container } = render(<Card>x</Card>);
    expect(container.firstChild).toHaveClass("backdrop-blur-md");
  });

  it("adds scan-hover class when interactive", () => {
    const { container } = render(<Card interactive>x</Card>);
    expect(container.firstChild).toHaveClass("scan-hover");
  });

  it("applies elevated variant when passed", () => {
    const { container } = render(<Card variant="elevated">x</Card>);
    expect(container.firstChild).toHaveClass("bg-[var(--bg-elevated)]");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- Card.test`
Expected: FAIL with "Cannot find module './Card'"

- [ ] **Step 3: Implement Card**

Create `frontend/src/components/ui/Card.tsx`:

```typescript
import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  variant?: "default" | "glass" | "elevated";
  interactive?: boolean;
  className?: string;
}

export function Card({
  children,
  variant = "glass",
  interactive = false,
  className = "",
}: CardProps) {
  const base = "rounded-xl border p-4";
  const variants = {
    default: "bg-[var(--bg-base)] border-[var(--border-subtle)]",
    glass: "bg-[var(--bg-glass)] backdrop-blur-md border-[var(--border-subtle)]",
    elevated: "bg-[var(--bg-elevated)] border-[var(--border-strong)]",
  };
  const interactiveClasses = interactive
    ? "scan-hover gradient-border-hover cursor-pointer transition-transform hover:-translate-y-0.5 duration-200"
    : "";

  return (
    <div className={`${base} ${variants[variant]} ${interactiveClasses} ${className}`}>
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- Card.test`
Expected: PASS, 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Card.tsx frontend/src/components/ui/Card.test.tsx
git commit -m "feat(frontend): add Card primitive (glass / default / elevated variants)"
```

---

### Task 4: StatTile component

**Files:**
- Create: `frontend/src/components/ui/StatTile.tsx`
- Create: `frontend/src/components/ui/StatTile.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/StatTile.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { StatTile } from "./StatTile";

describe("StatTile", () => {
  it("renders label, value, and subtext", () => {
    render(<StatTile label="Index size" value={64231} subtext="USPTO · EPO · WIPO" />);
    expect(screen.getByText("Index size")).toBeInTheDocument();
    expect(screen.getByText("USPTO · EPO · WIPO")).toBeInTheDocument();
  });

  it("uses tabular-nums for the value", () => {
    const { container } = render(<StatTile label="x" value={100} />);
    expect(container.querySelector(".tabular-nums")).toBeInTheDocument();
  });

  it("applies signal accent border when accent=signal", () => {
    const { container } = render(<StatTile label="x" value={1} accent="signal" />);
    expect(container.firstChild).toHaveClass("border-[var(--signal-blue)]");
  });

  it("applies warning accent border when accent=warning", () => {
    const { container } = render(<StatTile label="x" value={1} accent="warning" />);
    expect(container.firstChild).toHaveClass("border-[var(--warning)]");
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm test -- StatTile.test`
Expected: FAIL.

- [ ] **Step 3: Implement StatTile**

Create `frontend/src/components/ui/StatTile.tsx`:

```typescript
import { Counter } from "./Counter";

interface StatTileProps {
  label: string;
  value: number;
  subtext?: string;
  accent?: "default" | "signal" | "warning";
}

export function StatTile({ label, value, subtext, accent = "default" }: StatTileProps) {
  const accentBorder = {
    default: "border-[var(--border-subtle)]",
    signal: "border-[var(--signal-blue)]/40",
    warning: "border-[var(--warning)]/40",
  }[accent];

  return (
    <div
      className={`rounded-xl bg-[var(--bg-glass)] backdrop-blur-md border ${accentBorder} p-4`}
    >
      <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-muted)]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-[var(--text-primary)] font-mono tabular-nums">
        <Counter value={value} duration={1200} />
      </div>
      {subtext && (
        <div className="mt-0.5 text-xs text-[var(--text-muted)]">{subtext}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

Note: StatTile depends on Counter (Task 6). Run with stub or wait until after Task 6 implementation.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/StatTile.tsx frontend/src/components/ui/StatTile.test.tsx
git commit -m "feat(frontend): add StatTile primitive for Today stats row"
```

---

### Task 5: BriefingItem component

**Files:**
- Create: `frontend/src/components/ui/BriefingItem.tsx`
- Create: `frontend/src/components/ui/BriefingItem.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/BriefingItem.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { BriefingItem } from "./BriefingItem";

describe("BriefingItem", () => {
  const base = {
    type: "trend" as const,
    label: "Filing trend · momentum",
    title: "G06T image processing",
    reason: "Shown because you follow NVIDIA",
    source: "USPTO direct",
    freshness: { updated_at: "2026-06-01T08:30:00Z", relative: "2h ago" },
  };

  it("renders title and label", () => {
    render(<BriefingItem {...base} />);
    expect(screen.getByText("G06T image processing")).toBeInTheDocument();
    expect(screen.getByText(/Filing trend/)).toBeInTheDocument();
  });

  it("displays the reason field (required for every item)", () => {
    render(<BriefingItem {...base} />);
    expect(screen.getByText(/Shown because you follow NVIDIA/)).toBeInTheDocument();
  });

  it("displays freshness", () => {
    render(<BriefingItem {...base} />);
    expect(screen.getByText("2h ago")).toBeInTheDocument();
  });

  it("applies trend type accent border", () => {
    const { container } = render(<BriefingItem {...base} type="trend" />);
    expect(container.firstChild).toHaveClass("border-l-[var(--type-trend)]");
  });

  it("applies expiring type accent border", () => {
    const { container } = render(<BriefingItem {...base} type="expiring" />);
    expect(container.firstChild).toHaveClass("border-l-[var(--type-expiring)]");
  });

  it("uses dashed border for news type (V1.1 placeholder)", () => {
    const { container } = render(<BriefingItem {...base} type="news" />);
    expect(container.firstChild).toHaveClass("border-dashed");
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm test -- BriefingItem.test`
Expected: FAIL.

- [ ] **Step 3: Implement BriefingItem**

Create `frontend/src/components/ui/BriefingItem.tsx`:

```typescript
import Link from "next/link";

export type BriefingItemType =
  | "trend"
  | "notable"
  | "company"
  | "expiring"
  | "foryou"
  | "news";

interface BriefingItemProps {
  type: BriefingItemType;
  label: string;
  title: string;
  subtext?: string;
  reason: string;
  source: string;
  freshness: { updated_at: string; relative: string };
  confidence?: { level: "high" | "medium" | "low"; caveat?: string };
  href?: string;
}

const typeStyles: Record<BriefingItemType, { border: string; bg: string; text: string }> = {
  trend: {
    border: "border-l-[var(--type-trend)]",
    bg: "bg-[var(--signal-blue)]/4",
    text: "text-[#a5b4fc]",
  },
  notable: {
    border: "border-l-[var(--type-notable)]",
    bg: "bg-[var(--score-high)]/4",
    text: "text-[#86efac]",
  },
  company: {
    border: "border-l-[var(--type-company)]",
    bg: "bg-[#7dd3fc]/4",
    text: "text-[#7dd3fc]",
  },
  expiring: {
    border: "border-l-[var(--type-expiring)]",
    bg: "bg-[var(--warning)]/4",
    text: "text-[#fcd34d]",
  },
  foryou: {
    border: "border-l-[var(--type-foryou)]",
    bg: "bg-gradient-to-br from-[var(--signal-violet)]/8 to-[var(--signal-blue)]/5",
    text: "text-[#c4b5fd]",
  },
  news: {
    border: "border-l-[var(--type-news)] border-dashed",
    bg: "bg-[var(--signal-violet)]/3",
    text: "text-[#c4b5fd]",
  },
};

export function BriefingItem(props: BriefingItemProps) {
  const s = typeStyles[props.type];
  const inner = (
    <div
      className={`border-l-[3px] ${s.border} ${s.bg} pl-3.5 pr-3 py-2.5 rounded-r-lg`}
    >
      <div className={`text-[9px] uppercase tracking-[0.1em] ${s.text}`}>
        {props.label}
      </div>
      <div className="mt-1 text-sm font-medium text-[var(--text-primary)]">
        {props.title}
      </div>
      {props.subtext && (
        <div className="mt-0.5 text-xs text-[var(--text-muted)]">{props.subtext}</div>
      )}
      <div className="mt-1 text-[11px] text-[var(--text-muted)]">{props.reason}</div>
      <div className="mt-1 flex items-center gap-2 text-[10px] text-[var(--text-disabled)]">
        <span>{props.freshness.relative}</span>
        <span>·</span>
        <span>{props.source}</span>
        {props.confidence && props.confidence.level !== "high" && (
          <>
            <span>·</span>
            <span className="text-[var(--warning)]">
              {props.confidence.caveat ?? props.confidence.level}
            </span>
          </>
        )}
      </div>
    </div>
  );

  return props.href ? <Link href={props.href}>{inner}</Link> : inner;
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- BriefingItem.test`
Expected: PASS, 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/BriefingItem.tsx frontend/src/components/ui/BriefingItem.test.tsx
git commit -m "feat(frontend): add BriefingItem with required reason/source/freshness fields"
```

---

### Task 6: Counter component

**Files:**
- Create: `frontend/src/components/ui/Counter.tsx`
- Create: `frontend/src/components/ui/Counter.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/Counter.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { Counter } from "./Counter";

describe("Counter", () => {
  it("renders the final value immediately when prefers-reduced-motion", () => {
    // Mock matchMedia for reduced motion
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        matches: query.includes("reduce"),
        addEventListener: () => {},
        removeEventListener: () => {},
      }),
    });
    render(<Counter value={64231} duration={1200} />);
    expect(screen.getByText("64,231")).toBeInTheDocument();
  });

  it("formats with commas (US locale)", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: () => ({ matches: true, addEventListener: () => {}, removeEventListener: () => {} }),
    });
    render(<Counter value={1247} duration={0} />);
    expect(screen.getByText("1,247")).toBeInTheDocument();
  });

  it("accepts a number prefix and suffix", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: () => ({ matches: true, addEventListener: () => {}, removeEventListener: () => {} }),
    });
    render(<Counter value={12} duration={0} prefix="+" />);
    expect(screen.getByText("+12")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm test -- Counter.test`
Expected: FAIL.

- [ ] **Step 3: Implement Counter**

Create `frontend/src/components/ui/Counter.tsx`:

```typescript
"use client";

import { useEffect, useRef, useState } from "react";

interface CounterProps {
  value: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
}

export function Counter({ value, duration = 1200, prefix = "", suffix = "" }: CounterProps) {
  const [display, setDisplay] = useState<number>(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasRun = useRef(false);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduced || duration === 0) {
      setDisplay(value);
      hasRun.current = true;
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasRun.current) {
          hasRun.current = true;
          const start = performance.now();
          const tick = (now: number) => {
            const elapsed = now - start;
            const t = Math.min(1, elapsed / duration);
            // ease-out cubic-bezier(0.16, 1, 0.3, 1)
            const eased = 1 - Math.pow(1 - t, 3);
            setDisplay(Math.round(value * eased));
            if (t < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.1 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [value, duration]);

  return (
    <span ref={ref}>
      {prefix}
      {display.toLocaleString("en-US")}
      {suffix}
    </span>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- Counter.test`
Expected: PASS, 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Counter.tsx frontend/src/components/ui/Counter.test.tsx
git commit -m "feat(frontend): add Counter primitive (IntersectionObserver + reduced-motion respect)"
```

---

### Task 7: Pill component

**Files:**
- Create: `frontend/src/components/ui/Pill.tsx`
- Create: `frontend/src/components/ui/Pill.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
import { render, screen } from "@testing-library/react";
import { Pill } from "./Pill";

describe("Pill", () => {
  it("renders label", () => {
    render(<Pill>Active</Pill>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies signal tone", () => {
    const { container } = render(<Pill tone="signal">x</Pill>);
    expect(container.firstChild).toHaveClass("text-[#a5b4fc]");
  });

  it("uses mono font when mono prop", () => {
    const { container } = render(<Pill mono>x</Pill>);
    expect(container.firstChild).toHaveClass("font-mono");
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm test -- Pill.test`
Expected: FAIL.

- [ ] **Step 3: Implement Pill**

```typescript
import { ReactNode } from "react";

interface PillProps {
  children: ReactNode;
  tone?: "default" | "signal" | "positive" | "warning" | "muted";
  mono?: boolean;
  size?: "sm" | "md";
}

export function Pill({ children, tone = "default", mono = false, size = "sm" }: PillProps) {
  const tones = {
    default: "bg-[var(--bg-glass-strong)] text-[var(--text-secondary)]",
    signal: "bg-[var(--signal-blue)]/15 text-[#a5b4fc]",
    positive: "bg-[var(--score-high)]/15 text-[#86efac]",
    warning: "bg-[var(--warning)]/15 text-[#fcd34d]",
    muted: "bg-[var(--bg-glass)] text-[var(--text-muted)]",
  };
  const sizes = { sm: "text-[10px] px-2 py-0.5", md: "text-xs px-3 py-1" };
  const monoClass = mono ? "font-mono tabular-nums" : "";

  return (
    <span
      className={`inline-block rounded-md uppercase tracking-[0.06em] ${sizes[size]} ${tones[tone]} ${monoClass}`}
    >
      {children}
    </span>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- Pill.test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Pill.tsx frontend/src/components/ui/Pill.test.tsx
git commit -m "feat(frontend): add Pill primitive replacing ad-hoc chip classes"
```

---

### Task 8: Button component

**Files:**
- Create or refactor: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Button.test.tsx`

- [ ] **Step 1: Check if Button already exists; back up if so**

Run: `ls frontend/src/components/ui/Button.tsx 2>/dev/null && echo EXISTS || echo NEW`

If EXISTS, read its current API and preserve any consuming-component signatures.

- [ ] **Step 2: Write the failing test**

```typescript
import { render, screen } from "@testing-library/react";
import { Button } from "./Button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("applies primary gradient by default", () => {
    const { container } = render(<Button>x</Button>);
    expect(container.firstChild).toHaveClass("bg-gradient-to-r");
  });

  it("applies secondary variant", () => {
    const { container } = render(<Button variant="secondary">x</Button>);
    expect(container.firstChild).toHaveClass("border");
  });

  it("has focus-visible ring", () => {
    const { container } = render(<Button>x</Button>);
    expect(container.firstChild).toHaveClass("focus-visible:ring-2");
  });
});
```

- [ ] **Step 3: Run test to verify fail**

Run: `cd frontend && npm test -- Button.test`
Expected: FAIL (or, if Button exists with different signature, fail with classname assertions).

- [ ] **Step 4: Implement Button**

```typescript
import { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: ButtonProps) {
  const variants = {
    primary:
      "bg-gradient-to-r from-[var(--signal-blue)] to-[var(--signal-violet)] text-white hover:shadow-lg hover:shadow-[var(--signal-violet)]/20",
    secondary:
      "bg-transparent border border-[var(--border-strong)] text-[var(--text-primary)] hover:bg-[var(--bg-glass)]",
    ghost:
      "bg-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]",
    danger:
      "bg-red-500/15 border border-red-500/30 text-red-300 hover:bg-red-500/25",
  };
  const sizes = {
    sm: "text-xs px-3 py-1.5",
    md: "text-sm px-4 py-2",
    lg: "text-base px-6 py-3",
  };

  return (
    <button
      className={`rounded-lg font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--signal-glow)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)] disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 5: Run test to verify pass**

Run: `cd frontend && npm test -- Button.test`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ui/Button.tsx frontend/src/components/ui/Button.test.tsx
git commit -m "feat(frontend): Button variants (primary gradient / secondary / ghost / danger)"
```

---

### Task 9: LiveIndicator component

**Files:**
- Create: `frontend/src/components/ui/LiveIndicator.tsx`
- Create: `frontend/src/components/ui/LiveIndicator.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
import { render, screen } from "@testing-library/react";
import { LiveIndicator } from "./LiveIndicator";

describe("LiveIndicator", () => {
  it("renders live state", () => {
    render(<LiveIndicator status="live" />);
    expect(screen.getByText(/Live/i)).toBeInTheDocument();
  });

  it("renders scanning state", () => {
    render(<LiveIndicator status="scanning" />);
    expect(screen.getByText(/Scanning/i)).toBeInTheDocument();
  });

  it("renders relative timestamp when label provided", () => {
    render(<LiveIndicator status="live" label="last scan 2m ago" />);
    expect(screen.getByText(/last scan 2m ago/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm test -- LiveIndicator.test`
Expected: FAIL.

- [ ] **Step 3: Implement LiveIndicator**

```typescript
type Status = "live" | "scanning" | "stale" | "offline";

interface LiveIndicatorProps {
  status: Status;
  label?: string;
}

const config: Record<Status, { dot: string; text: string; defaultLabel: string }> = {
  live: {
    dot: "bg-[var(--score-high)] shadow-[0_0_8px_var(--score-high)]",
    text: "text-[#86efac]",
    defaultLabel: "Live",
  },
  scanning: {
    dot: "bg-[var(--signal-blue)] shadow-[0_0_8px_var(--signal-blue)] animate-pulse",
    text: "text-[#a5b4fc]",
    defaultLabel: "Scanning…",
  },
  stale: {
    dot: "bg-[var(--text-muted)]",
    text: "text-[var(--text-muted)]",
    defaultLabel: "Stale",
  },
  offline: {
    dot: "bg-[var(--text-disabled)]",
    text: "text-[var(--text-disabled)]",
    defaultLabel: "Offline",
  },
};

export function LiveIndicator({ status, label }: LiveIndicatorProps) {
  const c = config[status];
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-glass)] px-3 py-1 ${c.text}`}
    >
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${c.dot}`} aria-hidden />
      <span className="text-[10px]">{label ?? c.defaultLabel}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- LiveIndicator.test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/LiveIndicator.tsx frontend/src/components/ui/LiveIndicator.test.tsx
git commit -m "feat(frontend): LiveIndicator (live / scanning / stale / offline states)"
```

---

### Task 10: SectionHeader component

**Files:**
- Create: `frontend/src/components/ui/SectionHeader.tsx`

- [ ] **Step 1: Implement SectionHeader directly (single-purpose, no test needed)**

```typescript
import { ReactNode } from "react";

interface SectionHeaderProps {
  label: string;
  meta?: ReactNode;
  className?: string;
}

export function SectionHeader({ label, meta, className = "" }: SectionHeaderProps) {
  return (
    <div className={`flex items-baseline justify-between mb-3 ${className}`}>
      <div className="text-[11px] uppercase tracking-[0.12em] text-[#a5b4fc]">
        {label}
      </div>
      {meta && <div className="text-[10px] text-[var(--text-muted)]">{meta}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Verify it imports cleanly**

Run:
```bash
cd frontend && npx tsc --noEmit
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/SectionHeader.tsx
git commit -m "feat(frontend): SectionHeader for page-level section labels"
```

---

### Task 11: Refresh Badge for dark theme

**Files:**
- Modify: `frontend/src/components/ui/Badge.tsx`

- [ ] **Step 1: Read current Badge**

```bash
cat frontend/src/components/ui/Badge.tsx
```

Identify light-theme assumptions (e.g., `bg-blue-100`, `text-blue-700`).

- [ ] **Step 2: Replace light classes with dark tokens**

Replace any `bg-{color}-100` with `bg-[var(--bg-glass-strong)]` or a tone-specific token. Replace `text-{color}-700` with one of `text-[#a5b4fc]` (signal), `text-[#86efac]` (positive), `text-[#fcd34d]` (warning), or `text-[var(--text-secondary)]` (default).

If Badge has variant prop, map each variant:
- default → muted glass
- primary → signal blue
- success → positive green
- warning → warning amber
- error → red

- [ ] **Step 3: Verify no light-mode classes remain**

Run:
```bash
grep -E "bg-(blue|gray|red|green|yellow|indigo|violet)-(50|100|200)" frontend/src/components/ui/Badge.tsx
```

Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/Badge.tsx
git commit -m "refactor(frontend): Badge to dark theme using II8 tokens"
```

---

### Task 12: Refresh EmptyState with brand voice

**Files:**
- Modify: `frontend/src/components/ui/EmptyState.tsx`

- [ ] **Step 1: Read current EmptyState**

```bash
cat frontend/src/components/ui/EmptyState.tsx
```

- [ ] **Step 2: Replace generic copy with COPY references**

Import the COPY object from brand:

```typescript
import { COPY } from "@/lib/brand";
```

Replace any hardcoded empty-state strings with `COPY.emptyExpiry`, `COPY.emptyThreshold`, etc. Where the existing component takes a `title` and `description` prop, set defaults from COPY.

- [ ] **Step 3: Refresh visual styling to dark theme**

Replace `bg-white` / `text-gray-*` with `bg-[var(--bg-glass)]` / `text-[var(--text-muted)]`. Add a subtle border `border-[var(--border-subtle)]`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/EmptyState.tsx
git commit -m "refactor(frontend): EmptyState dark theme + brand-voice COPY defaults"
```

---

### Task 13: Refresh Skeleton for dark theme

**Files:**
- Modify: `frontend/src/components/ui/Skeleton.tsx`

- [ ] **Step 1: Replace shimmer base color**

Replace `bg-gray-200` (or whatever the current base is) with `bg-[var(--bg-glass)]`. Shimmer overlay uses `bg-[var(--bg-glass-strong)]` for the moving highlight.

- [ ] **Step 2: Verify the shimmer animation respects prefers-reduced-motion**

Wrap the shimmer animation in a CSS media query check OR use Tailwind's `motion-reduce:animate-none` modifier.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/Skeleton.tsx
git commit -m "refactor(frontend): Skeleton dark theme + reduced-motion respect"
```

---

### Task 14: Refresh StarterTopics for dark theme

**Files:**
- Modify: `frontend/src/components/ui/StarterTopics.tsx`

- [ ] **Step 1: Audit current styles**

```bash
grep -E "bg-(white|gray|blue)" frontend/src/components/ui/StarterTopics.tsx
```

- [ ] **Step 2: Replace with token-based styling**

Topic cards: `bg-[var(--bg-glass)] border border-[var(--border-subtle)] hover:border-[var(--signal-blue)]/40`. Selected state: `border-[var(--signal-blue)] bg-[var(--signal-blue)]/10`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/StarterTopics.tsx
git commit -m "refactor(frontend): StarterTopics dark theme refresh"
```

---

### Task 15: Refresh FreshnessBanner for dark theme

**Files:**
- Modify: `frontend/src/components/ui/FreshnessBanner.tsx`

- [ ] **Step 1: Read current FreshnessBanner**

```bash
cat frontend/src/components/ui/FreshnessBanner.tsx
```

- [ ] **Step 2: Replace light styling with dark tokens**

Banner: `bg-[var(--bg-glass)] border border-[var(--border-subtle)] text-[var(--text-secondary)]`. Use mono font for timestamps.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/FreshnessBanner.tsx
git commit -m "refactor(frontend): FreshnessBanner dark theme + mono timestamps"
```

---

### Task 16: Refresh SourceAttribution for dark theme

**Files:**
- Modify: `frontend/src/components/ui/SourceAttribution.tsx`

- [ ] **Step 1: Replace styling tokens**

`text-[var(--text-muted)] text-[10px]`. Icon color: `text-[var(--signal-blue)]`. Hover: `text-[var(--text-secondary)]`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui/SourceAttribution.tsx
git commit -m "refactor(frontend): SourceAttribution dark theme refresh"
```

---

### Task 17: Build BrandMark logo component

**Files:**
- Create: `frontend/src/components/nav/BrandMark.tsx`

- [ ] **Step 1: Implement BrandMark**

```typescript
import Link from "next/link";
import { BRAND } from "@/lib/brand";

export function BrandMark() {
  return (
    <Link
      href="/today"
      className="flex items-center gap-1.5 group"
      aria-label={`${BRAND.name} — 8 invention signals tracked daily`}
      title="8 invention signals tracked daily"
    >
      <span className="font-semibold text-[var(--text-primary)]">Invention</span>
      <span className="font-medium text-[var(--text-secondary)]">Index</span>
      <span className="ml-0.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-[var(--signal-violet)] text-white text-xs font-bold shadow-[0_0_12px_var(--signal-violet)] group-hover:animate-pulse">
        8
      </span>
    </Link>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/nav/BrandMark.tsx
git commit -m "feat(frontend): BrandMark with Invention Index 8 logo + glowing 8 pill"
```

---

### Task 18: Build AccountDropdown component

**Files:**
- Create: `frontend/src/components/nav/AccountDropdown.tsx`

- [ ] **Step 1: Implement AccountDropdown**

```typescript
"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";

export function AccountDropdown() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        aria-haspopup="true"
        aria-expanded={open}
        className="w-8 h-8 rounded-full bg-[var(--bg-glass)] border border-[var(--border-subtle)] text-[var(--text-primary)] text-xs hover:bg-[var(--bg-glass-strong)]"
      >
        {user.email[0].toUpperCase()}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-44 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] shadow-xl py-1 z-50">
          <Link href="/watchlist" className="block px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]">Watchlist</Link>
          <Link href="/account" className="block px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]">Account</Link>
          <Link href="/account/billing" className="block px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]">Billing</Link>
          {user.is_staff && (
            <Link href="/admin" className="block px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]">Admin</Link>
          )}
          <button
            onClick={logout}
            className="block w-full text-left px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/nav/AccountDropdown.tsx
git commit -m "feat(frontend): AccountDropdown (watchlist/account/billing/admin/logout)"
```

---

### Task 19: Build TopNav component

**Files:**
- Create: `frontend/src/components/nav/TopNav.tsx`

- [ ] **Step 1: Implement TopNav**

```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "./BrandMark";
import { AccountDropdown } from "./AccountDropdown";

const NAV_ITEMS = [
  { href: "/today", label: "Today" },
  { href: "/patents", label: "Patents" },
  { href: "/expiry", label: "Expiry" },
  { href: "/opportunity", label: "Opportunities" },
  { href: "/trends", label: "Trends" },
  { href: "/themes", label: "Topics" },
  { href: "/companies", label: "Companies" },
] as const;

export function TopNav() {
  const pathname = usePathname();
  return (
    <nav className="sticky top-0 z-40 border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-8">
            <BrandMark />
            <div className="flex items-center gap-1">
              {NAV_ITEMS.map(({ href, label }) => {
                const active = pathname?.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      active
                        ? "text-[var(--text-primary)] bg-[var(--bg-glass)]"
                        : "text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]"
                    }`}
                  >
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/search"
              aria-label="Search"
              className="w-8 h-8 rounded-md hover:bg-[var(--bg-glass)] flex items-center justify-center text-[var(--text-muted)]"
            >
              🔍
            </Link>
            <button
              aria-label="Alerts"
              className="w-8 h-8 rounded-md hover:bg-[var(--bg-glass)] flex items-center justify-center text-[var(--text-muted)] relative"
            >
              🔔
            </button>
            <AccountDropdown />
          </div>
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/nav/TopNav.tsx
git commit -m "feat(frontend): TopNav with 7-item navigation + search/alerts/account"
```

---

### Task 20: Refactor (app)/layout.tsx to dark shell

**Files:**
- Modify: `frontend/src/app/(app)/layout.tsx`

- [ ] **Step 1: Read current layout**

```bash
cat frontend/src/app/\(app\)/layout.tsx
```

Identify any light-theme classes, old nav imports, sidebar imports.

- [ ] **Step 2: Replace shell**

Rewrite as:

```typescript
import { ReactNode } from "react";
import { TopNav } from "@/components/nav/TopNav";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      <TopNav />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
    </div>
  );
}
```

Remove any old nav/sidebar references that are now in TopNav.

- [ ] **Step 3: Verify build is clean**

Run:
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TS errors, build succeeds.

- [ ] **Step 4: Verify rendering**

Run `docker compose up frontend` (if not running). Visit `http://localhost:3000/today`. Expected: dark background, new top nav visible. Existing page content inside `<main>` may still render in light styles — that's fine, surfaces are overhauled in later phases.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(app\)/layout.tsx
git commit -m "refactor(frontend): (app) layout dark shell + new TopNav"
```

---

### Task 21: prefers-reduced-motion audit + dev showcase page

**Files:**
- Create: `frontend/src/app/(app)/dev/components/page.tsx`

- [ ] **Step 1: Build a dev showcase page**

Create `frontend/src/app/(app)/dev/components/page.tsx`:

```typescript
import { Card } from "@/components/ui/Card";
import { StatTile } from "@/components/ui/StatTile";
import { BriefingItem } from "@/components/ui/BriefingItem";
import { Pill } from "@/components/ui/Pill";
import { Button } from "@/components/ui/Button";
import { LiveIndicator } from "@/components/ui/LiveIndicator";
import { SectionHeader } from "@/components/ui/SectionHeader";

export default function DevComponentsPage() {
  return (
    <div className="space-y-12">
      <SectionHeader label="Cards" meta="3 variants" />
      <div className="grid grid-cols-3 gap-4">
        <Card>default glass</Card>
        <Card variant="elevated">elevated</Card>
        <Card interactive>interactive</Card>
      </div>

      <SectionHeader label="StatTiles" meta="4 examples" />
      <div className="grid grid-cols-4 gap-3">
        <StatTile label="Index size" value={64231} subtext="USPTO · EPO · WIPO" />
        <StatTile label="This week" value={1247} accent="signal" subtext="↑ 12%" />
        <StatTile label="Follows" value={7} subtext="4 topics · 3 cos" />
        <StatTile label="Expiring 90d" value={47} accent="warning" subtext="high-opp" />
      </div>

      <SectionHeader label="Pills" />
      <div className="flex flex-wrap gap-2">
        <Pill>Default</Pill>
        <Pill tone="signal">USPTO</Pill>
        <Pill tone="positive" mono>opp 92</Pill>
        <Pill tone="warning">Expiring</Pill>
      </div>

      <SectionHeader label="Buttons" />
      <div className="flex flex-wrap gap-3">
        <Button variant="primary">Primary CTA</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
      </div>

      <SectionHeader label="LiveIndicator" />
      <div className="flex gap-3">
        <LiveIndicator status="live" label="last scan 2m ago" />
        <LiveIndicator status="scanning" />
        <LiveIndicator status="stale" />
      </div>

      <SectionHeader label="BriefingItems" meta="6 types" />
      <div className="space-y-3">
        {(["trend", "notable", "company", "expiring", "foryou", "news"] as const).map((t) => (
          <BriefingItem
            key={t}
            type={t}
            label={`${t} · sample`}
            title={`Sample ${t} item`}
            subtext="subtext line"
            reason={`Shown because of ${t}`}
            source="USPTO direct"
            freshness={{ updated_at: "2026-06-01T08:30:00Z", relative: "2h ago" }}
          />
        ))}
      </div>
    </div>
  );
}
```

This page is for visual review of all primitives in one place during dev. Per spec §12 "no fake data" rule, this is acceptable because it's a clearly-labeled dev showcase, not user-facing content.

- [ ] **Step 2: Audit motion respect**

Visit `http://localhost:3000/dev/components`. Enable `prefers-reduced-motion: reduce` in DevTools (Rendering tab → Emulate CSS media feature → reduce).

Verify:
- Counter jumps to final value (no count-up)
- LiveIndicator scanning state does not pulse
- Any background drift animations are still
- Hover transitions still work (opacity/border) but no transforms

- [ ] **Step 3: Document any motion violations**

If any primitive animates under reduced-motion, fix it inline. Common fix: add `motion-reduce:animate-none motion-reduce:transition-none` to the offending element.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/dev/components/page.tsx
git commit -m "feat(frontend): dev showcase page at /dev/components for primitive review"
```

---

### Task 22: Phase A gate verification

- [ ] **Step 1: Run full tests**

Run:
```bash
cd frontend && npm test -- --passWithNoTests
```

Expected: all primitive tests pass.

- [ ] **Step 2: Run build**

Run:
```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds, no TS errors.

- [ ] **Step 3: Run lint**

Run:
```bash
cd frontend && npm run lint
```

Expected: clean or only pre-existing warnings (catalog them in the gate report).

- [ ] **Step 4: Visit /dev/components and screenshot or describe each primitive**

Use whichever method was confirmed in Phase 0 (real screenshots if Playwright/Puppeteer is available, structural HTML inspection if not).

- [ ] **Step 5: Visit every existing authenticated route**

Run:
```bash
for route in today patents trends expiry opportunity themes companies watchlist search; do
  curl -s -o /dev/null -w "$route: %{http_code}\n" http://localhost:3000/$route
done
```

Expected: 200 (possibly 401 redirect-to-login if not authed; that's fine). No 500s. No crashes from missing components after the layout refactor.

- [ ] **Step 6: Write the Phase A gate report**

Create `.hermes/plans/2026-06-01_frontend-phase-a-gate.md` with:
- Test results
- Build result
- Lint result
- /dev/components observations (per primitive)
- Authenticated route HTTP status grid
- Known issues / regressions / things to address in Phase B
- "Phase A is GO" or "Phase A is BLOCKED on [X]" decision

- [ ] **Step 7: Hand off to Andy**

Send Andy a summary message including:
- Path to gate report
- Top 3 most important findings
- Confirmation of GO/BLOCKED for Phase B

Wait for Andy's go-ahead before Phase B starts.

---

## Phase A Gate

Phase B does not begin until:
- [ ] All 22 tasks complete
- [ ] All component tests pass
- [ ] `npm run build` clean, no TS errors
- [ ] `npm run lint` clean (or only pre-existing warnings)
- [ ] /dev/components page renders with all primitives visible
- [ ] All existing authenticated routes return non-500 status
- [ ] prefers-reduced-motion respected by all primitives
- [ ] Gate report exists and is reviewed by Andy
- [ ] Andy gives explicit go-ahead
