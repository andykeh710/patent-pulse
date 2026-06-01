# Frontend Overhaul — Phase C: Onboarding + Follow Companies UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the persona-based onboarding wizard (3 steps), the FollowButton component wired to the Phase B endpoints, and integrate both into the relevant existing surfaces. After this phase a new user can sign up → wizard → arrive with persona + topics + followed companies persisted in the DB and influencing future feed responses.

**Architecture:** Three React components orchestrated by a `PersonaWizard` that manages step state. The wizard triggers on first visit when `user.persona === null` via a Next.js client-side check in the (app) layout. FollowButton is a small stateful component reusable on companies list rows, companies detail header, and (later in Phase E) patent detail headers. SWR hooks wrap the Phase B endpoints with optimistic updates.

**Tech Stack:** React, Next.js App Router, SWR, TypeScript, the Phase A primitives.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §7, §11.1 Phase C.

**Depends on:** Phase B gate passed. /api/v1/account/persona, /api/v1/account/companies (POST/DELETE/GET), /api/v1/account/companies/suggested all live and tested.

---

## File Structure

```
frontend/src/lib/hooks/usePersona.ts                              # NEW — SWR wrapper for persona GET/PUT
frontend/src/lib/hooks/useFollowedCompanies.ts                    # NEW — SWR wrapper for follows CRUD
frontend/src/lib/hooks/useSuggestedCompanies.ts                   # NEW — SWR for suggested

frontend/src/components/companies/FollowButton.tsx                # NEW
frontend/src/components/companies/FollowButton.test.tsx           # NEW

frontend/src/components/onboarding/PersonaWizard.tsx              # NEW — orchestrator
frontend/src/components/onboarding/Step1Persona.tsx               # NEW
frontend/src/components/onboarding/Step2Topics.tsx                # NEW
frontend/src/components/onboarding/Step3Companies.tsx             # NEW
frontend/src/components/onboarding/PersonaWizard.test.tsx         # NEW

frontend/src/app/(app)/layout.tsx                                 # MODIFY — add wizard trigger
frontend/src/app/(app)/companies/page.tsx                         # MODIFY — Follow column, My follows tab
frontend/src/app/(app)/companies/[name]/page.tsx                  # MODIFY — Follow button in header
frontend/src/app/(app)/account/page.tsx                           # MODIFY — Persona editable field

frontend/src/lib/types.ts                                         # MODIFY — Persona enum + FollowedCompany type
```

---

## Tasks

### Task 1: usePersona hook

**Files:**
- Create: `frontend/src/lib/hooks/usePersona.ts`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add Persona type**

In `frontend/src/lib/types.ts`:

```typescript
export type Persona = "operator" | "investor" | "curious";

export interface PersonaResponse {
  persona: Persona | null;
}
```

- [ ] **Step 2: Implement hook**

`frontend/src/lib/hooks/usePersona.ts`:

```typescript
"use client";
import useSWR, { mutate } from "swr";
import { api } from "@/lib/api";
import type { Persona, PersonaResponse } from "@/lib/types";

const KEY = "/api/v1/account/persona";

export function usePersona() {
  const { data, error, isLoading } = useSWR<PersonaResponse>(KEY, api.get);
  return {
    persona: data?.persona ?? null,
    isLoading,
    error,
  };
}

export async function setPersona(persona: Persona): Promise<void> {
  await api.put(KEY, { persona });
  await mutate(KEY);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/hooks/usePersona.ts frontend/src/lib/types.ts
git commit -m "feat(frontend): usePersona hook + Persona type"
```

---

### Task 2: useFollowedCompanies hook

**Files:**
- Create: `frontend/src/lib/hooks/useFollowedCompanies.ts`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Add type**

In `frontend/src/lib/types.ts`:

```typescript
export interface FollowedCompany {
  company_normalized_name: string;
  display_name: string;
  patent_count_in_topics?: number | null;
}
```

- [ ] **Step 2: Implement hook**

`frontend/src/lib/hooks/useFollowedCompanies.ts`:

```typescript
"use client";
import useSWR, { mutate } from "swr";
import { api } from "@/lib/api";
import type { FollowedCompany } from "@/lib/types";

const KEY = "/api/v1/account/companies";

export function useFollowedCompanies() {
  const { data, error, isLoading } = useSWR<FollowedCompany[]>(KEY, api.get);
  return {
    companies: data ?? [],
    isLoading,
    error,
    isFollowing: (normalized: string) => (data ?? []).some(c => c.company_normalized_name === normalized),
  };
}

export async function followCompany(displayName: string): Promise<FollowedCompany> {
  const result = await api.post<FollowedCompany>(KEY, { company_name: displayName });
  await mutate(KEY);
  return result;
}

export async function unfollowCompany(normalizedName: string): Promise<void> {
  await api.delete(`${KEY}/${encodeURIComponent(normalizedName)}`);
  await mutate(KEY);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/hooks/useFollowedCompanies.ts frontend/src/lib/types.ts
git commit -m "feat(frontend): useFollowedCompanies hook"
```

---

### Task 3: useSuggestedCompanies hook

**Files:**
- Create: `frontend/src/lib/hooks/useSuggestedCompanies.ts`

- [ ] **Step 1: Implement**

```typescript
"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { FollowedCompany, Persona } from "@/lib/types";

export function useSuggestedCompanies(persona: Persona | null) {
  const key = persona ? `/api/v1/account/companies/suggested?persona=${persona}` : null;
  const { data, error, isLoading } = useSWR<FollowedCompany[]>(key, api.get);
  return { suggestions: data ?? [], isLoading, error };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/hooks/useSuggestedCompanies.ts
git commit -m "feat(frontend): useSuggestedCompanies hook for onboarding step 3"
```

---

### Task 4: FollowButton component

**Files:**
- Create: `frontend/src/components/companies/FollowButton.tsx`
- Create: `frontend/src/components/companies/FollowButton.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FollowButton } from "./FollowButton";

// Mock the hooks
jest.mock("@/lib/hooks/useFollowedCompanies", () => ({
  useFollowedCompanies: () => ({
    isFollowing: (n: string) => n === "apple",
    companies: [],
  }),
  followCompany: jest.fn().mockResolvedValue({}),
  unfollowCompany: jest.fn().mockResolvedValue(undefined),
}));

describe("FollowButton", () => {
  it("renders + Follow when not following", () => {
    render(<FollowButton displayName="NVIDIA" normalizedName="nvidia" />);
    expect(screen.getByRole("button", { name: /\+ Follow/ })).toBeInTheDocument();
  });

  it("renders ✓ Following when followed", () => {
    render(<FollowButton displayName="Apple Inc." normalizedName="apple" />);
    expect(screen.getByRole("button", { name: /Following/ })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npm test -- FollowButton.test
```

Expected: FAIL.

- [ ] **Step 3: Implement**

```typescript
"use client";
import { useState } from "react";
import { useFollowedCompanies, followCompany, unfollowCompany } from "@/lib/hooks/useFollowedCompanies";

interface FollowButtonProps {
  displayName: string;
  normalizedName: string;
  size?: "sm" | "md";
}

export function FollowButton({ displayName, normalizedName, size = "sm" }: FollowButtonProps) {
  const { isFollowing } = useFollowedCompanies();
  const [busy, setBusy] = useState(false);
  const following = isFollowing(normalizedName);

  const handleClick = async () => {
    setBusy(true);
    try {
      if (following) {
        await unfollowCompany(normalizedName);
      } else {
        await followCompany(displayName);
      }
    } finally {
      setBusy(false);
    }
  };

  const sizes = { sm: "text-[10px] px-2 py-1", md: "text-xs px-3 py-1.5" };

  return (
    <button
      onClick={handleClick}
      disabled={busy}
      className={`rounded-md transition-colors disabled:opacity-50 ${sizes[size]} ${
        following
          ? "bg-[var(--score-high)]/15 text-[#86efac] border border-[var(--score-high)]/30"
          : "bg-[var(--bg-glass)] text-[#a5b4fc] hover:bg-[var(--bg-glass-strong)] border border-[var(--border-subtle)]"
      }`}
    >
      {following ? "✓ Following" : "+ Follow"}
    </button>
  );
}
```

- [ ] **Step 4: Run to verify pass**

```bash
cd frontend && npm test -- FollowButton.test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/companies/FollowButton.tsx frontend/src/components/companies/FollowButton.test.tsx
git commit -m "feat(frontend): FollowButton with optimistic state"
```

---

### Task 5: Step1Persona component

**Files:**
- Create: `frontend/src/components/onboarding/Step1Persona.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import type { Persona } from "@/lib/types";

const PERSONAS: { value: Persona; label: string; desc: string }[] = [
  {
    value: "operator",
    label: "Builder / Operator",
    desc: "Track what's being built in your space, find inspiration, learn from prior art",
  },
  {
    value: "investor",
    label: "Investor / Scout",
    desc: "Identify trends, emerging companies, technology shifts before they're obvious",
  },
  {
    value: "curious",
    label: "Curious / Researcher",
    desc: "Patent intelligence the way you read Stratechery — discover, briefing, highlights",
  },
];

interface Step1Props {
  selected: Persona | null;
  onSelect: (p: Persona) => void;
  onContinue: () => void;
}

export function Step1Persona({ selected, onSelect, onContinue }: Step1Props) {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[#a5b4fc]">Step 1 of 3</div>
        <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">What brings you here?</h2>
      </div>
      <div className="space-y-3">
        {PERSONAS.map(p => (
          <button
            key={p.value}
            onClick={() => onSelect(p.value)}
            className={`w-full text-left rounded-xl p-4 border transition-all ${
              selected === p.value
                ? "border-[var(--signal-blue)] bg-[var(--signal-blue)]/10"
                : "border-[var(--border-subtle)] bg-[var(--bg-glass)] hover:border-[var(--signal-blue)]/40"
            }`}
          >
            <div className="text-sm font-medium text-[var(--text-primary)]">{p.label}</div>
            <div className="mt-1 text-xs text-[var(--text-muted)]">{p.desc}</div>
          </button>
        ))}
      </div>
      <Button variant="primary" disabled={!selected} onClick={onContinue}>Continue</Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/onboarding/Step1Persona.tsx
git commit -m "feat(frontend): Step1Persona onboarding screen"
```

---

### Task 6: Step2Topics component

**Files:**
- Create: `frontend/src/components/onboarding/Step2Topics.tsx`

- [ ] **Step 1: Implement (reuse existing StarterTopics)**

```typescript
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { STARTER_TOPICS } from "@/lib/starterTopics";

interface Step2Props {
  selectedTopics: string[];
  onToggle: (topic: string) => void;
  onContinue: () => void;
  onSkip: () => void;
}

export function Step2Topics({ selectedTopics, onToggle, onContinue, onSkip }: Step2Props) {
  const [custom, setCustom] = useState("");

  return (
    <div className="space-y-6">
      <div>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[#a5b4fc]">Step 2 of 3</div>
        <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">Pick a few topics</h2>
      </div>
      <div className="flex flex-wrap gap-2">
        {STARTER_TOPICS.map(t => {
          const active = selectedTopics.includes(t.name);
          return (
            <button
              key={t.name}
              onClick={() => onToggle(t.name)}
              className={`rounded-full px-3 py-1.5 text-xs border transition-colors ${
                active
                  ? "bg-[var(--signal-blue)]/20 border-[var(--signal-blue)] text-[var(--text-primary)]"
                  : "bg-[var(--bg-glass)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--signal-blue)]/40"
              }`}
            >
              {active ? "✓ " : ""}{t.name}
            </button>
          );
        })}
        <button
          className="rounded-full px-3 py-1.5 text-xs border border-dashed border-[var(--signal-violet)]/40 text-[#a5b4fc]"
          onClick={() => custom && onToggle(custom)}
        >
          + Custom topic
        </button>
      </div>
      <p className="text-xs text-[var(--text-muted)]">Pick 1–5. You can change these anytime.</p>
      <div className="flex gap-3">
        <Button variant="primary" disabled={selectedTopics.length === 0} onClick={onContinue}>Continue</Button>
        <Button variant="ghost" onClick={onSkip}>Skip for now</Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/onboarding/Step2Topics.tsx
git commit -m "feat(frontend): Step2Topics onboarding screen"
```

---

### Task 7: Step3Companies component

**Files:**
- Create: `frontend/src/components/onboarding/Step3Companies.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { Button } from "@/components/ui/Button";
import { FollowButton } from "@/components/companies/FollowButton";
import { useSuggestedCompanies } from "@/lib/hooks/useSuggestedCompanies";
import type { Persona } from "@/lib/types";
import { normalizeCompanyName } from "@/lib/utils";

interface Step3Props {
  persona: Persona;
  onFinish: () => void;
  onSkip: () => void;
}

export function Step3Companies({ persona, onFinish, onSkip }: Step3Props) {
  const { suggestions, isLoading } = useSuggestedCompanies(persona);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-[10px] uppercase tracking-[0.12em] text-[#a5b4fc]">Step 3 of 3</div>
        <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">Follow some companies</h2>
        <p className="mt-2 text-xs text-[var(--text-muted)]">Suggested for your persona and selected topics.</p>
      </div>

      {isLoading && <p className="text-xs text-[var(--text-muted)]">Loading suggestions…</p>}

      <div className="space-y-2">
        {suggestions.map(s => (
          <div
            key={s.display_name}
            className="flex items-center justify-between rounded-md bg-[var(--bg-glass)] border border-[var(--border-subtle)] px-3 py-2"
          >
            <div>
              <div className="text-sm text-[var(--text-primary)]">{s.display_name}</div>
              <div className="text-[10px] text-[var(--text-muted)]">
                {s.patent_count_in_topics ?? 0} patents in your topics · last 12mo
              </div>
            </div>
            <FollowButton
              displayName={s.display_name}
              normalizedName={normalizeCompanyName(s.display_name)}
            />
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <Button variant="primary" onClick={onFinish}>Finish</Button>
        <Button variant="ghost" onClick={onSkip}>Skip for now</Button>
      </div>
    </div>
  );
}
```

Also add `normalizeCompanyName` to `frontend/src/lib/utils.ts` (mirror the backend regex):

```typescript
export function normalizeCompanyName(name: string): string {
  return name
    .replace(/[ ,.]+(inc|corp|ltd|llc|gmbh|sa|ag|co)\.?$/i, "")
    .trim()
    .toLowerCase();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/onboarding/Step3Companies.tsx frontend/src/lib/utils.ts
git commit -m "feat(frontend): Step3Companies onboarding screen + normalizeCompanyName util"
```

---

### Task 8: PersonaWizard orchestrator

**Files:**
- Create: `frontend/src/components/onboarding/PersonaWizard.tsx`

- [ ] **Step 1: Implement**

```typescript
"use client";
import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Step1Persona } from "./Step1Persona";
import { Step2Topics } from "./Step2Topics";
import { Step3Companies } from "./Step3Companies";
import { setPersona } from "@/lib/hooks/usePersona";
import { api } from "@/lib/api";
import type { Persona } from "@/lib/types";

interface PersonaWizardProps {
  onComplete: () => void;
}

export function PersonaWizard({ onComplete }: PersonaWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [persona, setSelectedPersona] = useState<Persona | null>(null);
  const [topics, setTopics] = useState<string[]>([]);

  const toggleTopic = (t: string) =>
    setTopics(s => s.includes(t) ? s.filter(x => x !== t) : [...s, t]);

  const handleStep1Continue = async () => {
    if (!persona) return;
    await setPersona(persona);
    setStep(2);
  };

  const handleStep2Continue = async () => {
    if (topics.length > 0) {
      await api.post("/api/v1/topics/bulk", { topics });
    }
    setStep(3);
  };

  const handleStep2Skip = () => setStep(3);

  const handleStep3Finish = () => onComplete();

  return (
    <div className="fixed inset-0 z-50 bg-[var(--bg-base)]/95 backdrop-blur-md flex items-center justify-center p-6">
      <Card variant="elevated" className="w-full max-w-2xl">
        {step === 1 && (
          <Step1Persona
            selected={persona}
            onSelect={setSelectedPersona}
            onContinue={handleStep1Continue}
          />
        )}
        {step === 2 && (
          <Step2Topics
            selectedTopics={topics}
            onToggle={toggleTopic}
            onContinue={handleStep2Continue}
            onSkip={handleStep2Skip}
          />
        )}
        {step === 3 && persona && (
          <Step3Companies persona={persona} onFinish={handleStep3Finish} onSkip={handleStep3Finish} />
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/onboarding/PersonaWizard.tsx
git commit -m "feat(frontend): PersonaWizard orchestrator (3 steps)"
```

---

### Task 9: Wire wizard trigger in (app) layout

**Files:**
- Modify: `frontend/src/app/(app)/layout.tsx`

- [ ] **Step 1: Add wizard trigger**

```typescript
"use client";  // if not already
import { useState, useEffect } from "react";
import { usePersona } from "@/lib/hooks/usePersona";
import { PersonaWizard } from "@/components/onboarding/PersonaWizard";
// ... existing imports ...

export default function AppLayout({ children }: { children: ReactNode }) {
  const { persona, isLoading } = usePersona();
  const [wizardDismissed, setWizardDismissed] = useState(false);
  const showWizard = !isLoading && !persona && !wizardDismissed;

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      <TopNav />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
      {showWizard && <PersonaWizard onComplete={() => setWizardDismissed(true)} />}
    </div>
  );
}
```

- [ ] **Step 2: Smoke-test in browser**

Visit `http://localhost:3000/today` as a user whose persona is null (drop column value in DB first to test):

```bash
docker compose exec db psql -U patent -d patent_pulse -c "UPDATE users SET persona = NULL WHERE email = 'andy@web3r.tech';"
```

Refresh. Wizard should appear. Click through. On Step 1 select → API call → step 2. Etc. After Step 3 Finish, wizard dismisses.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/layout.tsx
git commit -m "feat(frontend): trigger PersonaWizard on first visit when persona is null"
```

---

### Task 10: Add FollowButton to companies surfaces

**Files:**
- Modify: `frontend/src/app/(app)/companies/page.tsx`
- Modify: `frontend/src/app/(app)/companies/[name]/page.tsx`

- [ ] **Step 1: Companies list — add Follow column**

In `frontend/src/app/(app)/companies/page.tsx`, in the rendered list:

```typescript
import { FollowButton } from "@/components/companies/FollowButton";
import { normalizeCompanyName } from "@/lib/utils";

// In the row rendering, add:
<FollowButton
  displayName={company.assignee}
  normalizedName={normalizeCompanyName(company.assignee)}
/>
```

- [ ] **Step 2: Companies detail — add Follow button in header**

In `frontend/src/app/(app)/companies/[name]/page.tsx`:

```typescript
import { FollowButton } from "@/components/companies/FollowButton";
import { normalizeCompanyName } from "@/lib/utils";

// Near the company name header:
<div className="flex items-center gap-3">
  <h1>{company.assignee}</h1>
  <FollowButton
    displayName={company.assignee}
    normalizedName={normalizeCompanyName(company.assignee)}
    size="md"
  />
</div>
```

- [ ] **Step 3: Smoke-test**

Visit `/companies` → click + Follow on a row → row shows ✓ Following. Refresh page → still shows ✓ Following (persisted via backend).
Visit `/companies/[name]` → header button shows correct state for that company.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/companies/page.tsx frontend/src/app/\(app\)/companies/\[name\]/page.tsx
git commit -m "feat(frontend): FollowButton on companies index + detail header"
```

---

### Task 11: "My follows" tab on /companies

**Files:**
- Modify: `frontend/src/app/(app)/companies/page.tsx`

- [ ] **Step 1: Add tab toggle**

Above the list, add:

```typescript
const [filter, setFilter] = useState<"all" | "follows">("all");
const { companies: followed } = useFollowedCompanies();

// Tabs UI
<div className="flex gap-2 mb-4">
  <button onClick={() => setFilter("all")} className={filter === "all" ? "..." : "..."}>All companies</button>
  <button onClick={() => setFilter("follows")} className={filter === "follows" ? "..." : "..."}>My follows ({followed.length})</button>
</div>

// Filter logic:
const filteredList = filter === "all"
  ? allCompanies
  : allCompanies.filter(c => followed.some(f => f.company_normalized_name === normalizeCompanyName(c.assignee)));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(app\)/companies/page.tsx
git commit -m "feat(frontend): My follows filter tab on /companies"
```

---

### Task 12: Account page — Persona editable field

**Files:**
- Modify: `frontend/src/app/(app)/account/page.tsx`

- [ ] **Step 1: Add persona dropdown**

In `frontend/src/app/(app)/account/page.tsx`:

```typescript
"use client";
import { usePersona, setPersona } from "@/lib/hooks/usePersona";
import type { Persona } from "@/lib/types";

// ...

const { persona, isLoading } = usePersona();

// In the form section:
<div>
  <label className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Persona</label>
  <select
    value={persona ?? ""}
    onChange={(e) => setPersona(e.target.value as Persona)}
    disabled={isLoading}
    className="mt-1 block w-full rounded-md bg-[var(--bg-glass)] border border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-primary)]"
  >
    <option value="" disabled>Select…</option>
    <option value="operator">Builder / Operator</option>
    <option value="investor">Investor / Scout</option>
    <option value="curious">Curious / Researcher</option>
  </select>
</div>
```

Also add a section listing followed companies + topics, with "Manage on Companies page →" and "Manage on Topics page →" links.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(app\)/account/page.tsx
git commit -m "feat(frontend): Persona editable field + follows summary on account page"
```

---

### Task 13: Phase C gate verification

- [ ] **Step 1: End-to-end signup flow test**

1. Clear a test user's persona: `UPDATE users SET persona=NULL`
2. Log in. Wizard appears.
3. Step 1: select Operator. Click Continue. Backend records persona.
4. Step 2: select 3 topics. Click Continue. Backend records topics.
5. Step 3: follow 2 suggested companies. Click Finish. Backend records follows.
6. Arrive at /today. Wizard dismissed.
7. Refresh /today. Wizard does NOT reappear.

- [ ] **Step 2: Follow toggle on /companies works**

1. Visit /companies. Click + Follow on a row. Row shows ✓ Following.
2. Click ✓ Following. Row reverts to + Follow.
3. Refresh page. State persists.

- [ ] **Step 3: /account persona edit works**

1. Visit /account. Persona dropdown shows current value.
2. Change to a different persona. Backend records.
3. Refresh page. New value persists.

- [ ] **Step 4: Briefing endpoint response reflects new follows**

After following a few companies, hit `GET /api/v1/today/briefing`. Verify the response includes items where the reason references followed companies (e.g., "Shown because you follow NVIDIA").

- [ ] **Step 5: Run all tests**

```bash
cd frontend && npm test
docker compose exec backend pytest backend/tests/
```

Expected: all pass.

- [ ] **Step 6: Write gate report**

`.hermes/plans/2026-06-01_frontend-phase-c-gate.md` with all the above verifications + GO/BLOCKED for Phase D.

- [ ] **Step 7: Hand off to Andy**

Wait for go-ahead before Phase D.

---

## Phase C Gate

Phase D does not begin until:
- [ ] All 13 tasks complete
- [ ] Wizard appears for new users, doesn't reappear after completion
- [ ] FollowButton works on /companies index + detail
- [ ] /account persona edit works
- [ ] /today/briefing response reflects follows (reason field references them)
- [ ] All tests pass
- [ ] Gate report exists and reviewed by Andy
- [ ] Andy gives go-ahead
