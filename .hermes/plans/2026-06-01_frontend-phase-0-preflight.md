# Frontend Overhaul — Phase 0: Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a written preflight report that resolves all open questions and unknowns before any frontend implementation begins. Zero code changes in this phase.

**Architecture:** No code. This is an orientation pass — Hermes inventories the current state of the codebase, resolves route/naming ambiguities, reproduces known bugs, and confirms tooling capability. The output is a single report document at `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` that Andy reviews before Phase A begins.

**Tech Stack:** bash, grep, git, curl, the project's existing tooling.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §11.1 Phase 0 and §2.1 Decision Register.

---

## File Structure

```
.hermes/plans/2026-06-01_frontend-overhaul-preflight.md   # the deliverable report
```

No source files created or modified. Hermes only reads from the existing codebase and writes the report.

---

## Tasks

### Task 1: Initialize the preflight report file

**Files:**
- Create: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md`

- [ ] **Step 1: Create report skeleton**

Write the file with this exact content:

```markdown
# Frontend Overhaul — Preflight Report

**Date:** 2026-06-01
**Reporter:** Hermes
**Status:** In progress

This is the preflight report for the Frontend Overhaul. It resolves all open questions from `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §11.1 Phase 0 before Phase A implementation begins.

---

## 1. Route inventory
[Filled by Task 2]

## 2. Route naming resolution (/themes vs /topics)
[Filled by Task 3]

## 3. /today vs /dashboard references
[Filled by Task 4]

## 4. Working tree state
[Filled by Task 5]

## 5. Screenshot capability
[Filled by Task 6]

## 6. /companies/[name] 500 reproduction
[Filled by Task 7]

## 7. Existing component audit
[Filled by Task 8]

## 8. New dependencies required
[Filled by Task 9]

## Summary
[Filled by Task 10]
```

- [ ] **Step 2: Confirm the file exists and is ~25 lines**

Run: `wc -l .hermes/plans/2026-06-01_frontend-overhaul-preflight.md`
Expected: ~25 (skeleton sections, no content yet)

---

### Task 2: Route inventory

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 1)

- [ ] **Step 1: List every file under (app) and (marketing)**

Run:
```bash
find frontend/src/app/\(app\) -type f -name "page.tsx" | sort > /tmp/app-routes.txt
find frontend/src/app/\(marketing\) -type f -name "page.tsx" | sort >> /tmp/app-routes.txt
find frontend/src/app/\(auth\) -type f -name "page.tsx" | sort >> /tmp/app-routes.txt
cat /tmp/app-routes.txt
```

Capture the full output.

- [ ] **Step 2: Compare against spec assumptions**

The spec at §6 references these surfaces. Cross-check the file list against:
- /today, /patents, /patents/[id], /trends, /trends/[surface], /trends/[surface]/[key]
- /expiry, /opportunity, /themes, /themes/[id], /companies, /companies/[name]
- /search, /watchlist, /account, /account/billing
- /admin, /admin/data-health, /admin/ai-runs
- /login, /login/verify, /unsubscribed
- /, /about, /contact, /pricing, /privacy, /terms

Flag any route the spec assumes that doesn't exist, and any route that exists but isn't mentioned in the spec.

- [ ] **Step 3: Write findings into Section 1 of the report**

In Section 1, write:
- A markdown table of every route file found
- A bullet list of any spec-vs-actual mismatches
- An explicit statement: "All spec-referenced routes exist" OR "The following are missing: …"

- [ ] **Step 4: Commit not applicable (no code changes — just a report file)**

Note: Andy commits the report file when the full preflight is complete (per memory rule).

---

### Task 3: Route naming resolution (/themes vs /topics)

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 2)

The spec's decision register §2.1 #2 says: UI label is "Topics" everywhere; route URL stays `/themes` in V1.

- [ ] **Step 1: Grep for "Topics" and "Themes" in code + copy**

Run:
```bash
grep -rn "Topics\|Themes\|themes\|topics" frontend/src --include="*.tsx" --include="*.ts" | grep -v node_modules > /tmp/topics-themes.txt
wc -l /tmp/topics-themes.txt
head -50 /tmp/topics-themes.txt
```

- [ ] **Step 2: Categorize each occurrence**

For each match, categorize as:
- Route URL (e.g., `href="/themes"`) — should stay as `/themes` per decision
- UI label string (e.g., `<a>Themes</a>` or `"Themes"`) — should become "Topics" in Phase A
- Internal variable / function name — leave as-is
- Comment / docstring — usually leave as-is unless misleading

- [ ] **Step 3: Write the categorized inventory into Section 2**

Format as a table with columns: File:Line | Occurrence | Category | Action.

If there are >30 occurrences, write a summary count + list the top 10 of each category.

- [ ] **Step 4: Confirm there's no "/topics" route anywhere**

Run:
```bash
grep -rn "/topics" frontend/src --include="*.tsx" --include="*.ts" | grep -v node_modules
```

Expected: zero matches (or only inside string literals that aren't routes).

If matches exist that look like routes, flag them in the report.

---

### Task 4: /today vs /dashboard reference scan

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 3)

- [ ] **Step 1: Grep /dashboard in frontend**

Run:
```bash
grep -rn "/dashboard" frontend/src 2>/dev/null | grep -v node_modules
```

Expected: zero matches (the route was removed in earlier UX sprint).

- [ ] **Step 2: Grep /dashboard in backend**

Run:
```bash
grep -rn "/dashboard" backend/app 2>/dev/null
```

Expected: zero matches.

- [ ] **Step 3: Grep /dashboard in email templates**

Run:
```bash
grep -rn "/dashboard" backend/app/email 2>/dev/null
find backend -name "*.html" -o -name "*.txt" | xargs grep -l "/dashboard" 2>/dev/null
```

Expected: zero matches.

- [ ] **Step 4: Grep /dashboard in any docs or .hermes plans**

Run:
```bash
grep -rn "/dashboard" .hermes docs 2>/dev/null || echo "no .hermes/docs hits"
```

Capture any references.

- [ ] **Step 5: Write findings into Section 3**

Write: "Found N references to /dashboard. Locations: [file:line list]. Recommendation: [add 307 redirect | safe to leave deleted]."

If zero references, write: "Clean — no /dashboard references found. /today is the canonical command center."

---

### Task 5: Working tree state check

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 4)

- [ ] **Step 1: Check git status**

Run:
```bash
git status --short
```

Capture the full output.

- [ ] **Step 2: Check if main branch is up to date with origin**

Run:
```bash
git log --oneline origin/main..HEAD 2>/dev/null
git log --oneline HEAD..origin/main 2>/dev/null
```

Capture both.

- [ ] **Step 3: Write findings into Section 4**

Write one of:
- "Clean working tree. No uncommitted changes. Branch is up to date with origin/main. **Proceed.**"
- "Working tree has N uncommitted files: [list]. Recommendation: Andy lands these before Phase A begins."
- "Branch is N commits ahead/behind origin/main. Recommendation: …"

This is a blocking gate — if uncommitted changes exist, Phase A should not start until Andy resolves them.

---

### Task 6: Screenshot capability check

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 5)

- [ ] **Step 1: Check if Playwright or Puppeteer is installed**

Run:
```bash
ls frontend/node_modules/@playwright 2>/dev/null
ls frontend/node_modules/puppeteer 2>/dev/null
```

- [ ] **Step 2: Check for headless chrome availability on the host**

Run:
```bash
which chromium google-chrome chrome 2>/dev/null
```

- [ ] **Step 3: Write findings into Section 5**

Write one of:
- "Playwright/Puppeteer available. Real screenshots will be produced during phase gates."
- "No headless browser available. Visual verification will be done via HTML structural observation (curl + inspect) only. Do NOT fabricate visual descriptions."

This affects how phase gates are verified later. Be explicit.

---

### Task 7: /companies/[name] 500 reproduction

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 6)

Per spec §2.1 decision 8, the /companies/[name] 500 is a V1 blocker fixed in Phase B. Capture the stack trace now so Phase B starts informed.

- [ ] **Step 1: Identify a real company that exists in the DB**

Run:
```bash
docker compose exec backend python -c "
from app.database import get_sync_db
from sqlalchemy import text
with next(get_sync_db()) as db:
    result = db.execute(text('SELECT assignee, COUNT(*) FROM patents WHERE assignee IS NOT NULL GROUP BY assignee ORDER BY 2 DESC LIMIT 5'))
    for row in result:
        print(row)
"
```

Capture the top 5 assignees. Pick one (the first or any) for reproduction.

- [ ] **Step 2: Curl the company detail backend endpoint**

Using the assignee name from Step 1 (URL-encode it; replace `Inc.` with `Inc%2E` if needed):
```bash
docker compose exec backend curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/companies/Apple%20Inc%2E
```

Capture the HTTP status code.

- [ ] **Step 3: If 500, fetch the stack trace from logs**

If Step 2 returned 500:
```bash
docker compose logs backend --tail=100 | tail -50
```

Capture the Python traceback. Look for the file/line where the exception originates.

- [ ] **Step 4: Verify the frontend route reproduces**

If you have a running dev frontend, navigate to:
`http://localhost:3000/companies/<urlencoded-name>`

Capture what renders (error page, 500 boundary, blank, etc.).

- [ ] **Step 5: Write findings into Section 6**

Write:
- HTTP status returned
- Stack trace if 500 (paste the actual lines, full traceback)
- File/line where the error originates
- Initial hypothesis for the fix (e.g., "URL decoding broken" or "company lookup query fails on names with spaces")

This becomes the input to Phase B Task 1 (the fix).

---

### Task 8: Existing component audit

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 7)

Spec §9.1 lists new components. Some of those names might already exist. Flag any duplication.

- [ ] **Step 1: List existing UI components**

Run:
```bash
ls -1 frontend/src/components/ui/
ls -1 frontend/src/components/patents/
ls -1 frontend/src/components/expiry/ 2>/dev/null
ls -1 frontend/src/components/topics/ 2>/dev/null
ls -1 frontend/src/components/marketing/ 2>/dev/null
```

- [ ] **Step 2: Cross-reference against §9.1 "New components" list**

The spec proposes these new files. Check each against the existing list:
- `Card`, `StatTile`, `BriefingItem`, `Counter`, `Pill`, `Button`, `LiveIndicator`, `SectionHeader`
- `PersonaWizard`, `Step1Persona`, `Step2Topics`, `Step3Companies`
- `FollowButton`
- `StatsRow`, `BriefingFeed`, `MyFollowsWidget`, `QuickActionsWidget`, `SavedPatentsWidget`
- `PatentDetailHeader`, `SummaryTab`, `OpportunityTab`, `FamilyTab`, `SourceTab`

For each:
- If exists: note as "EXISTS — audit needed before refactor"
- If not exists: note as "NEW — to be created in Phase X"

- [ ] **Step 3: Write findings into Section 7**

Write a table with columns: Component | Status (exists/new) | Action.

If any "new" components are actually already present, recommend whether to evolve the existing or replace.

---

### Task 9: New dependency check

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Section 8)

Per spec §12, no new heavy dependencies. Allowed: `next/font/google` (Geist).

- [ ] **Step 1: List currently-installed packages**

Run:
```bash
cat frontend/package.json | grep -A 100 "dependencies"
```

- [ ] **Step 2: Identify packages this overhaul will need**

Cross-check against the spec:
- `next/font/google` for Geist — already part of Next.js, no install
- swr (data fetching) — likely already present, confirm
- date-fns or similar for "2h ago" relative timestamps — confirm if present

- [ ] **Step 3: Write findings into Section 8**

Write one of:
- "No new dependencies needed. Geist fonts use next/font/google (already in Next.js)."
- "Need to add: [list]. Andy approval required before install."

---

### Task 10: Summary + go/no-go

**Files:**
- Modify: `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` (Summary section)

- [ ] **Step 1: Write summary**

In the Summary section, write:
- Bulleted list of all 8 findings (one line each)
- Explicit "Phase A is GO" OR "Phase A is BLOCKED — must resolve [X] first"
- Andy decision points listed (e.g., "Andy: confirm screenshot strategy", "Andy: approve any new dependencies", "Andy: review /companies/[name] hypothesis")

- [ ] **Step 2: Mark report status as Complete**

Change the file's header from `**Status:** In progress` to `**Status:** Complete — awaiting Andy's review and go-ahead for Phase A`.

- [ ] **Step 3: Final report length sanity check**

Run:
```bash
wc -l .hermes/plans/2026-06-01_frontend-overhaul-preflight.md
```

Expected: 100–250 lines. Less means findings are too thin; more means over-reporting.

- [ ] **Step 4: Hand off to Andy**

Send Andy a one-paragraph summary message including:
- The preflight report path
- Top 3 most important findings
- Any blockers (uncommitted changes, missing tooling, dependency requests)
- Confirmation that Phase A is GO or BLOCKED

Wait for Andy's go-ahead before starting Phase A. Do NOT auto-proceed.

---

## Phase 0 Gate

Phase A does not begin until:
- [ ] Preflight report at `.hermes/plans/2026-06-01_frontend-overhaul-preflight.md` exists
- [ ] All 10 tasks above are complete (Sections 1–8 + Summary filled)
- [ ] Andy has reviewed the report
- [ ] Andy has given explicit go-ahead in chat
- [ ] Any blockers from the report (uncommitted changes, missing tooling, dependency requests) are resolved
