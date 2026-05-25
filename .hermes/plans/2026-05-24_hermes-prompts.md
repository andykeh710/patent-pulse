# Hermes Prompts — Sprint 6 through V1 Launch

Each section below is a **self-contained prompt** ready to paste to
Hermes. Use them in the order they appear. Each prompt assumes Hermes
has access to the repo and can read the referenced plan docs.

**Workflow for every prompt:**
1. Paste the prompt to Hermes.
2. Hermes executes one chunk and stops at the verification block.
3. You review, ask follow-ups, and commit the chunk.
4. Reply with the next chunk number (e.g. "S6-2") to advance.

---

## 0. Universal Hermes Operating Rules (paste once at session start)

```
You are Hermes, the implementation agent for the Patent Pulse codebase.
Operating rules — non-negotiable:

1. Read AGENTS.md first if not already loaded.
2. I commit, you code. NEVER run git commands. Never run
   `git add`, `git commit`, `git push`, `git reset`, etc. Stop at the
   end of each chunk and wait for me to commit.
3. Chunk-by-chunk: complete exactly one chunk per turn, then stop.
   Print a verification block (table form) and wait for "next" or
   the next chunk identifier.
4. Verification block must include:
   - Files created/modified (table with path + LOC delta + purpose)
   - Full `pytest -q` output WITHOUT --ignore. **Paste the LITERAL
     last 5-15 lines of pytest output, not a summary.** The user will
     re-run pytest themselves to verify; numbers in your summary must
     match the literal tail. If they don't match, you have failed
     the chunk.
   - Report exact counts as part of the literal tail: "N passed,
     M xfailed, K xpassed, F failed". No emoji checkmarks without
     numbers attached.
   - Baseline diff vs the previous chunk's count.
   - Frontend `npm run build` result if any frontend changed — paste
     the literal output (✓ Compiled successfully line or first error).
   - Language audit grep result for sprint surfaces — paste literal
     grep output (zero lines or actual hits).
   - Browser smoke test: each step's actual curl/browser response
     code and JSON shape. No "should work" — only observed results.

   **Run pytest as the LAST step of every chunk, immediately before
   printing the verification block.** Do not rely on counts from
   earlier in the same session. Container restarts, dependency
   installs, or other-chunk changes can invalidate stale numbers.
5. DEVIATION DETECTED protocol — if reality diverges from the plan
   (different schema, different API field, missing dependency, etc.)
   STOP immediately and present Options A/B/C with your recommendation.
   Do NOT silently work around the deviation.
6. No `--no-verify`, no `--ignore`, no `as any` TypeScript casts to
   silence type errors, no deleting tests to make a suite green.
   If a test fails, fix the root cause or report the deviation.
7. All LLM output cached as AIArtifact with proper artifact_type +
   prompt_hash + input_hash. Use the existing LLMRequest/LLMClient
   pattern from app/ai/usage_narrative.py as the reference.
8. Language audit — these phrases must NEVER appear in user-facing
   strings or LLM prompts:
   "free to use", "public domain", "is used by", "definitely used".
   Run a grep on your changed files before declaring done.
9. Always show confidence labels + "verify with official registers"
   caveats on every expiry surface.
10. Stripe TEST MODE only. Email send mode defaults to `dev`. Do not
    flip either to production without explicit instruction from me.
11. If you need an environment variable that isn't set, STOP and ask
    me to set it. Never invent placeholder values.

Acknowledge by saying "Hermes ready — operating rules acknowledged"
and then wait for the first chunk prompt.
```

---

## Sprint 6 — Alerts & Newsletters

### Sprint 6 kickoff prompt

```
Begin Sprint 6 — User Alerts & Newsletters.

Plan: .hermes/plans/2026-05-24_sprint-6-alerts-newsletters-impl.md
Scope: .hermes/plans/2026-05-24_sprint-6-alerts-newsletters-scope.md

Pre-flight verification (do this first, do not start S6-1 until
confirmed):
- `cat .env | grep -E "RESEND_API_KEY|EMAIL_FROM_ADDRESS|EMAIL_DEV_RECIPIENT|AUTH_SECRET_KEY|MAGIC_LINK_BASE_URL|EMAIL_SEND_MODE"`
- All 6 vars must be present and non-empty (EMAIL_SEND_MODE may be
  unset; defaults to `dev`).
- `git status` must be clean (post-Sprint-5 commit landed).
- `pytest -q` baseline must show 227 passed, 1 xfailed, 1 xpassed, 0 failed.

If any pre-flight check fails, STOP and report which one. Do not
proceed.

When pre-flight passes, begin Chunk S6-1 (Migrations 0012-0014 + ORM
models). Stop at the verification block.
```

### Sprint 6 chunk-advance prompts

After each chunk, paste the next identifier:

```
S6-2
```

(or `S6-3`, `S6-4`, ..., `S6-9`)

When S6-9 verification clears, paste:

```
Sprint 6 close-out. Report:
- Cumulative LOC across all 9 chunks
- Full test count and baseline diff (vs 227)
- Language audit final state
- Browser smoke test summary for: /login, /login/verify, /account,
  topic detail subscribe panel
- Suggested commit message for S6-9 (final chunk)
- Confirmation that EMAIL_SEND_MODE is still `dev`

Then stop. Wait for me to commit S6-9 before Sprint 6.5 begins.
```

---

## Sprint 6.5 — Citation Ingestion (D1 + D2)

### Sprint 6.5 plan-out prompt

```
Sprint 6.5 — USPTO Forward Citation Ingestion + Historical Backfill

Context: Sprint 5 usage_signals currently runs on similarity evidence
only because patent_publications.citations_forward is empty across
the entire 54K corpus. The USPTO client at backend/app/ingestion/
uspto_client.py:107 has a TODO documenting this gap.

The patent_client SDK exposes `PatentBiblio.forward_citations` as a
PublicSearchBiblioManager (lazy iterator). Iterating it issues a
separate USPTO API call per patent — so we cannot enable this by
default on the hot ingestion path. We need a feature-flagged opt-in.

Your task — produce an implementation plan doc at
`.hermes/plans/2026-05-24_sprint-6-5-citation-ingestion-impl.md`
with these chunks:

S65-1: Configuration plumbing
- Add `USPTO_FETCH_CITATIONS` boolean to app/config.py (default False).
- Wire it into uspto_client._patent_to_dict so it conditionally
  iterates forward_citations and includes them as ["USPTO:..."] doc IDs.
- Add a rate-limit-aware retry (1 call/sec ceiling, exponential
  backoff on 429).
- Tests with mocked SDK responses.

S65-2: Per-patent fetch helper
- Standalone function `fetch_forward_citations(patent_id)` that takes
  an existing PatentPublication row and calls the SDK directly.
- Used by the backfill task; the ingestion path uses S65-1.

S65-3: Historical backfill Celery task
- `app/tasks/backfill_citations.py` with batch_backfill_citations.
- Orders patents by opportunity_score DESC (high-value first).
- Idempotent: skips patents where citations_forward != [].
- Rate-limited (1 call/sec via asyncio.sleep between calls).
- Includes engine.dispose() pattern from embeddings.py (per A2 audit).
- Beat schedule: every 5 min, limit=50 (≈600 patents/hr,
  ~90 hours to cover 54K). Include comments documenting this.

S65-4: Tests + verification
- backend/tests/ingestion/test_citation_fetch.py — mocked SDK paths
- backend/tests/tasks/test_backfill_citations.py — task harness
- Re-run Sprint 5 usage_signal_score on a sample of patents that now
  have citations_forward — show the new evidence counts.
- Language audit (no new user-facing strings, but the docstrings/
  comments still go through it).
- Full pytest count + baseline diff.

Acceptance for Sprint 6.5:
- USPTO_FETCH_CITATIONS=true causes new ingestion to populate
  citations_forward.
- Backfill task is scheduled and producing rows.
- citation_collector (existing) now returns evidence on backfilled
  patents.
- ~50 patents demonstrably have new evidence appearing in their usage
  signal scores.

Produce the plan doc, then wait for my OK before starting S65-1.
```

### Sprint 6.5 chunk-advance prompts

```
S65-1
```

(then `S65-2`, `S65-3`, `S65-4`)

### Sprint 6.5 close-out prompt

```
Sprint 6.5 close-out. Report:
- Final test count and baseline diff.
- Sample 10 patents that now have non-empty citations_forward.
- Sample 5 patents whose usage_signal_score changed because of the
  newly-populated citation evidence (show before/after).
- Backfill task throughput (patents/hr at current rate).
- Estimated wall time to fully backfill the 54K corpus.
- Suggested commit message.
```

---

## Sprint 7 — SaaS Readiness (BRAINSTORM PHASE FIRST)

### Sprint 7 brainstorm trigger

Before Hermes can code, you and I need to lock 5 decisions. Paste this
to me (Claude) in a new session:

```
Begin Sprint 7 brainstorm. Walk me through the 5 decisions from
.hermes/plans/2026-05-24_v1-completion-roadmap.md §3b:
- S7-Q1: Pricing model
- S7-Q2: Free tier limits
- S7-Q3: Stripe integration depth
- S7-Q4: Export formats
- S7-Q5: OAuth or magic-link only

Use AskUserQuestion. After each answer, summarize implications. When
all 5 are locked, write the Sprint 7 scope + impl plan docs (mirror
the Sprint 6 doc structure). Then I'll hand the impl prompt to Hermes.
```

### Sprint 7 kickoff prompt (only AFTER brainstorm + impl plan exist)

```
Begin Sprint 7 — SaaS Readiness.

Plan: .hermes/plans/<DATE>_sprint-7-saas-readiness-impl.md
Scope: .hermes/plans/<DATE>_sprint-7-saas-readiness-scope.md

Pre-flight verification:
- Locked decisions documented in scope doc.
- Stripe test-mode credentials are set in .env:
  STRIPE_API_KEY (test mode key starting with sk_test_)
  STRIPE_WEBHOOK_SECRET (whsec_...)
  STRIPE_PRICE_ID_PRO (the price ID for the Pro tier)
- `git status` clean.
- `pytest -q` baseline reported (post-Sprint-6.5 count).
- Stripe TEST MODE confirmed — the live key must NOT be present.

Reminder per AGENTS.md and your operating rules: Stripe stays in TEST
MODE for the entire sprint. The first live-mode flip requires
explicit instruction from me, and you will refuse if asked to use a
key starting with sk_live_.

When pre-flight passes, begin Chunk S7-1. Stop at the verification
block.
```

### Sprint 7 chunk-advance + close-out

```
S7-2
```

(etc., through the chunks defined in the plan)

Close-out at the end:

```
Sprint 7 close-out. Confirm:
- All Stripe operations exercised in TEST MODE (provide the test
  Stripe customer IDs, subscription IDs, webhook event IDs used).
- Quota middleware tested against synthetic over-quota users.
- Export endpoints render in dev — provide sample CSV/PDF byte counts.
- Admin dashboard reachable, ownership-gated.
- Final pytest count + baseline diff.
- Language audit.
- Suggested commit message.
```

---

## Sprint 8 — Content Packaging

### Sprint 8 plan-out prompt

```
Sprint 8 — Content Packaging

Goal per AGENTS.md priority #7: downstream packaging only. LinkedIn
posts (already shipped Phase 4.1) and weekly digests (shipping in
S6-7) are the existing two formats. Sprint 8 adds:

S8-1: Newsletter public-URL view
- Each weekly digest already cached as AIArtifact (artifact_type
  = "weekly_digest"). Add a public read-only page at
  /newsletter/[artifact_id] that renders the cached content with
  AISourceFooter, attribution, and a "subscribe to topics like this"
  CTA.
- Frontend route + a single backend endpoint
  GET /api/v1/newsletter/{artifact_id} (no auth, but rate-limited).
- ~200 LOC total.

S8-2: PDF report generator
- New endpoint POST /api/v1/patents/{patent_id}/report → renders
  a branded PDF with:
  - Header: title, doc_id, assignees, filing/grant dates
  - Expiry section (status + confidence + caveats)
  - Claims summary (first 3 claims or LLM summary if cached)
  - Family panel (if family_members populated)
  - Usage signals score + tier breakdown + top 5 evidence rows
  - Sprint 4 narrative if present (cached `why_now`)
  - Footer: AISourceFooter + "verify with official registers"
- Use reportlab or weasyprint (recommend weasyprint for HTML→PDF
  templating). Test the docker image already includes the binary
  deps — add them if not.
- ~400 LOC.

S8-3: content_generator Haiku audit (deferred from A3)
- Generate 5 LinkedIn posts via the existing endpoint against 5
  diverse patents.
- Inspect the AIArtifact rows: are the keys (post_markdown, hook,
  tone, caveats) populated correctly?
- If YES → no code change needed; document the audit result in this
  same plan doc as a §"Audit" section.
- If NO → switch content_generator.py tier from "narrative" to
  "summary" (mirror A3 fix), update key_map if needed.
- ~30-60 min investigation + ~10-50 LOC if a fix is needed.

S8-4 (OPTIONAL — discuss with me before doing): Editorial review queue
- Drafts (LinkedIn post, weekly digest, newsletter) land in a queue.
- Admin can approve/reject before send.
- ~300 LOC.

Produce the plan doc at
.hermes/plans/<DATE>_sprint-8-content-packaging-impl.md with
S8-1, S8-2, S8-3 chunks. Leave S8-4 as a §"Deferred — pending user
decision" section.

Wait for my OK before starting S8-1.
```

### Sprint 8 chunk-advance + close-out

Same pattern: `S8-1`, `S8-2`, `S8-3`, then close-out.

---

## Production Readiness — Code Items (PR8, PR9, PR11, PR12, PR13, PR14)

These can run in parallel with sprints or interleaved. Each is
small and self-contained. Group prompt:

### Production-readiness code kickoff prompt

```
Production readiness — code items (PR8, PR9, PR11, PR12, PR13, PR14
from .hermes/plans/2026-05-24_v1-completion-roadmap.md §6).

These are 6 independent items. Execute in this order (smallest first
to build momentum):

PR11 — Healthcheck extension
- Modify backend/app/api/v1/health.py (or wherever GET /health lives)
- Add probes: DB reachable, Redis reachable, Resend reachable
  (just a GET to api.resend.com/domains with a short timeout — count
  any non-network-error as healthy).
- Return per-probe status in JSON, overall status="ok" only if all pass.
- Test with all probes mocked.
- ~50 LOC.

PR13 — Production Dockerfile
- Multi-stage build: builder + runtime.
- Non-root user (uid 10001).
- Slim base (python:3.12-slim).
- Drop dev dependencies in runtime image.
- Add HEALTHCHECK directive pointing at /health.
- Confirm image size dropped by ≥40% vs current single-stage.
- ~30 LOC Dockerfile changes.

PR9 — Structured JSON logging
- Configure Python logging to emit JSON to stdout.
- Use python-json-logger or structlog (recommend structlog).
- Include trace fields: timestamp, level, logger, message, request_id
  (FastAPI middleware that adds it).
- Replace logging.basicConfig calls.
- ~100 LOC.

PR12 — API-layer rate limiting
- Use slowapi (FastAPI rate-limit middleware).
- Default limit: 60/min per IP.
- Authenticated users: 300/min per user_id.
- Apply globally; exempt /health and /api/v1/auth/verify.
- Tests: 429 returned on over-limit.
- ~80 LOC.

PR8 — Sentry
- Wire sentry-sdk on backend (app/main.py startup).
- Wire @sentry/nextjs on frontend.
- Both gated by SENTRY_DSN env var (if unset, silently noop).
- Add a /api/v1/debug/sentry endpoint (admin-only) that triggers a
  test exception.
- ~50 LOC + setup.

PR14 — GitHub Actions CI
- Create .github/workflows/ci.yml
- Jobs: lint (ruff), test (pytest with postgres+redis services),
  build (npm build).
- Trigger on PR + push to main.
- Cache pip + npm.
- Fail on any non-zero exit.
- ~150 LOC YAML.

Execute as 6 chunks (PR11 → PR13 → PR9 → PR12 → PR8 → PR14). Stop at
the verification block after each. Standard verification format
applies.

Pre-flight: confirm SENTRY_DSN may be unset (OK — Sentry silently
noops). Confirm we have a GitHub repo (else PR14 is moot until then).

Begin with PR11.
```

### Production-readiness close-out

```
Production readiness close-out. Report:
- Image size before/after PR13.
- CI workflow link (push to a branch and confirm green).
- Health endpoint response sample.
- Rate-limit verification (curl until 429).
- Sentry test event ID (if SENTRY_DSN set).
- Final pytest count.
```

---

## Legal / Launch — Code Items (L3, L4, L5, L7)

### Legal/launch kickoff prompt

```
Legal / launch — code items (L3, L4, L5, L7 from
.hermes/plans/2026-05-24_v1-completion-roadmap.md §7).

These are 4 independent items. Execute in this order:

L5 — Patent data source attribution audit
- Grep frontend/ for every page that renders patent data
  (PatentDetailPage, ExpiryRadar, Trends, search results, etc.)
- Verify each page has a visible "Source: USPTO" / "Source: EPO"
  attribution near the data — either inline or in a footer.
- Add the attribution to any page missing it. Use a reusable
  <SourceAttribution office={patent.office} /> component.
- ~50 LOC + component.

L3 — GDPR data deletion endpoint
- DELETE /api/v1/account/me (requires current_user dep from S6-2).
- Cascade-deletes:
  - topic_subscriptions (already cascades via FK)
  - auth_magic_link_tokens (already cascades via FK)
  - email_deliveries (NOT cascade — set user_id to NULL OR keep with
    anonymized user_id for audit trail; pick one and document)
  - AIArtifact rows attributable to user (artifact has no FK to user
    currently — if not attributable, leave alone and document)
  - users row itself
- Returns 204 on success.
- Frontend: /account page gets a "Delete my account" button with a
  type-the-email-to-confirm pattern.
- ~150 LOC.

L4 — Cookie / tracking consent banner (CONDITIONAL)
- IF analytics has been added (Plausible, Segment, GA) — add a
  consent banner before any tracking fires.
- IF NO analytics — skip this item, document as "deferred until
  analytics added."
- Check existing frontend for any tracking SDKs in package.json or
  app/layout.tsx imports.
- ~80 LOC if needed.

L7 — First-login onboarding flow
- After magic-link verify, if user has zero topic subscriptions,
  redirect to /onboarding instead of /.
- 3-step wizard:
  1. "Pick your interests" — checkboxes for top 6 CPC sections,
     pre-selecting based on default themes.
  2. "Choose how you hear about new patents" — instant / weekly /
     both, set on the subscriptions created in step 1.
  3. "You're set" — confirmation, link to /account.
- ~200 LOC.

Execute as 4 chunks (L5 → L3 → L4 if applicable → L7). Pre-flight:
- Sprint 6 must be complete (current_user dep + subscriptions table
  + /account page exist).
- Confirm whether any analytics SDKs are present.

Begin with L5.
```

### Legal/launch close-out

```
Legal/launch close-out. Report:
- Pages audited and fixed in L5 — full list.
- L3 DELETE verified end-to-end on a test user. Show the audit-trail
  decision for email_deliveries (NULL vs anonymize).
- L4 status — done or deferred (and why).
- L7 onboarding screenshots or text descriptions for all 3 steps.
- Final pytest count.
```

---

## Final V1 close-out (only after everything above)

```
Final V1 close-out. Produce a single report covering:

1. Cumulative LOC delta from session start (2026-05-24 baseline).
2. Final pytest count and the path from 213 → final.
3. Sprint-by-sprint summary (one line per sprint).
4. Every feature flag and env var introduced — full list with
   purpose, default, and "must-be-set-for-production" indicator.
5. Outstanding TODOs / KNOWN_ISSUES in code (grep for those).
6. The post-V1 backlog (anything explicitly deferred during the
   sprint sweep — D3, D4, D5, S8-4 if not done, any new ones
   discovered).
7. A 1-page README update suggestion (top of repo) explaining what
   V1 ships with.

After producing the report, stop. Do not run any git commands. I
will tag v1.0.0 from main when I'm satisfied.
```

---

## Quick reference — full execution sequence

```
1. (User) Pre-flight P1-P8 from v1-completion-roadmap.md §1
2. (User) Paste "Universal Hermes Operating Rules" prompt
3. (User) Paste "Sprint 6 kickoff" prompt
4. (Loop) Hermes runs S6-1; you commit; paste "S6-2"; etc. through S6-9
5. (User) Paste "Sprint 6 close-out"
6. (User) Paste "Sprint 6.5 plan-out" → Hermes writes plan → you OK it
7. (Loop) S65-1 → S65-2 → S65-3 → S65-4
8. (User) Paste "Sprint 6.5 close-out"
9. (User → Claude session) Trigger Sprint 7 brainstorm
10. (Claude) AskUserQuestion → 5 decisions → write S7 scope+impl
11. (User → Hermes) Paste "Sprint 7 kickoff" + Stripe TEST keys in .env
12. (Loop) Sprint 7 chunks per the impl plan
13. (User) Paste "Sprint 7 close-out"
14. (User) Paste "Sprint 8 plan-out" → Hermes writes plan → you OK it
15. (Loop) S8-1 → S8-2 → S8-3 (+ S8-4 only if approved)
16. (User) Paste "Sprint 8 close-out"
17. (User) Paste "Production-readiness kickoff" (can be done earlier
   in parallel — PR14 CI especially benefits from being early)
18. (Loop) PR11 → PR13 → PR9 → PR12 → PR8 → PR14
19. (User) Paste "Production-readiness close-out"
20. (User) Paste "Legal/launch kickoff"
21. (Loop) L5 → L3 → L4 (if needed) → L7
22. (User) Paste "Legal/launch close-out"
23. (User) Paste "Final V1 close-out"
24. (User) Tag v1.0.0, deploy, announce.
```

---

## Notes on parallelism

You can save wall-clock time by interleaving these:

- **Production readiness PR14 (CI pipeline)** — ship this as early as
  possible, even mid-Sprint-6. Every subsequent chunk benefits from
  catching regressions in CI.
- **Production readiness PR8 (Sentry) + PR9 (structured logging)** —
  ship anytime after Sprint 6.5. Independent of feature work.
- **Sprint 6.5 (citation ingestion backfill)** — once the backfill
  task is scheduled, it runs for ~90 hours in the background. You can
  start Sprint 7 work while it's running.
- **L5 (attribution audit)** — can ship anytime; doesn't depend on
  other sprints.

Safe parallel groups:
- During Sprint 6: nothing else (foundation work)
- During Sprint 6.5 build: PR14 (CI)
- During Sprint 6.5 backfill running: Sprint 7 brainstorm
- During Sprint 7 build: PR8, PR9, L5
- During Sprint 8 build: PR11, PR12, PR13
- Final: L3, L4, L7
