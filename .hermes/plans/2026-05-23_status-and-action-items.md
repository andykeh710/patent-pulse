# Patent Pulse — Status & Action Items (2026-05-23)

> Snapshot of where the product stands, what's in flight, and the
> remaining sprint sequence. Reference doc — update as state changes.
> See `ROADMAP.md` for full sprint specs, `PRODUCT_STRATEGY.md` for
> product framing, `AGENTS.md` for working rules.

## Current state at a glance

| Item | Status |
|---|---|
| Backend tests | 180 passing |
| Frontend tests | 31 passing |
| Frontend build | Clean, 16 routes |
| DB migration | 0009 (head) |
| Services running | db, redis, backend, worker, beat, frontend |
| Last commit on origin | `a93cdc2 feat: Phase 4.1 — Generate LinkedIn Post from Patent` |
| Branch state | Significantly ahead of origin — uncommitted Sprint 2C + Sprint 3 work in tree |

## What's shipped (in code, not necessarily committed)

| Phase / Sprint | Scope | Committed? |
|---|---|---|
| Phase 0 (legacy) | Foundation, ingestion, AI summaries | ✓ |
| Phase 1 (legacy) | Patent credibility — 7 tabs, family stub, citations stub | ✓ |
| Phase 2 (legacy) | Nav rebuild, `/today` editorial homepage | ✓ |
| Phase 3 (legacy) | User-created topics | ✓ |
| Phase 4.1 (legacy) | LinkedIn post generation | ✓ |
| Sprint 1 | Strategy docs (`PRODUCT_STRATEGY.md`, `ROADMAP.md`, `AGENTS.md`) | ❌ uncommitted |
| Sprint 2A | `ExpiryAssessment` model, deterministic engine, backfill, migration 0007 | ❌ uncommitted |
| Sprint 2B | `expiry_opportunity_score`, `/summary` + `/opportunities` endpoints, migration 0008 | ❌ uncommitted |
| Sprint 2C | Expiry Radar UI — 7 sections, URL state, legal caveats, CSV export | ❌ uncommitted |
| Sprint 3 (partial) | Chunk 1: `citations_forward` field + migration 0009; Chunk 2: claim mechanisms + broadness; Chunk 3: family tab rewrite (with banner deviation fix) | ❌ uncommitted, Chunks 4–5 remaining |

## What's planned but not started

| Sprint | Scope | Notes |
|---|---|---|
| Sprint 4 | Trend Intelligence Drilldowns — clickable trend cards, drilldown pages, narratives | Plan not yet written |
| Sprint 4.5 | Patent Figure Ingestion (link-only, ~1 day) | Plan not yet written; small bridge sprint |
| Sprint 5 | Commercial Usage Signals MVP — citations + similar-patent evidence, scoring, narrative panel | Scope doc exists at `.hermes/plans/2026-05-22_sprint-5-usage-signals-scope.md`; impl plan not yet written |
| Sprint 6A | Highlights data layer — `highlight_cards` table, 7 generators, daily job, GET endpoint | Plan not yet written |
| Sprint 6B | Patent News Feed (`/news` route) — visual cards with figures | Prereq: Sprint 4.5 |
| Sprint 6C | Topics enhancement — auto-matching on ingest, alerts table, 7 alert types | |
| Sprint 6D | Newsletter delivery — issue generation, email provider, unsubscribe | Test mode only until explicit approval for broad send |
| Sprint 7 | SaaS Foundation — auth, multi-tenancy, Stripe (test mode), quotas, exports | 5 chunks; auth/billing are hard-stops in verify |
| Sprint 8 | Commercial API & Exports — API keys, `/api/commercial/v1/*`, webhooks, large exports | 6 chunks; depends on Sprint 7 |

## Active deviations and design decisions worth remembering

1. **Sprint 2C — Backend gap fixes folded in:** the `expiry_window_start` query param, `days_ahead ge=0` validator change, and `publication_number`/`office` on `ExpiryItem` were all deviation fixes during Sprint 2C, not part of the original Sprint 2B scope.
2. **Sprint 3 Chunk 3 — Family banner reworded (Option B):** the planned conditional `active_family_risk` banner was changed to a generic family-awareness disclaimer. Reason: `active_family_risk` lives on `ExpiryAssessment`, not `PatentDetailResponse`. Proper conditional rendering needs backend join scope creep deferred to a later sprint.
3. **Forward citations are plumbed but empty:** `citations_forward` column + API field added in Sprint 3 Chunk 1, but no ingestion task populates it yet. Empty state handles this gracefully; populating it is a separate, deferred concern.
4. **AI claim summaries deferred:** Sprint 3 explicitly does NOT add LLM-generated claim summaries. Cost risk. Defer to post-Sprint 5.
5. **Per-family-member legal status deferred:** Sprint 3 family tab shows "Unknown" for members other than the current patent. Requires INPADOC integration — out of scope.

## Next-action sequence (do in this order)

### 1. Finish Sprint 3 (immediate)

| Step | Owner | Action |
|---|---|---|
| 1.1 | You | Commit Sprint 2C (2 commits — backend + frontend; see prompt history for `git add` commands) |
| 1.2 | Hermes | Chunk 4 — External links (add WIPO) + citation header counts + inventor prominence |
| 1.3 | You | Verify Chunk 4 diff; approve Chunk 5 |
| 1.4 | Hermes | Chunk 5 — types update + run full 14-check Sprint 3 verify |
| 1.5 | You | Review 14-check report; if green, commit Sprint 3 (1–2 commits) |

### 2. Sprint 4 — Trend Intelligence Drilldowns

| Step | Owner | Action |
|---|---|---|
| 2.1 | You | Send Sprint 4 kickoff prompt (from playbook) |
| 2.2 | Hermes | Write plan to `.hermes/plans/2026-XX-XX_sprint-4-trend-drilldowns.md`, stop |
| 2.3 | You | Review plan, approve |
| 2.4 | Hermes | Build 5 chunks, stop between each |
| 2.5 | You | Review each diff, approve next chunk |
| 2.6 | You | Send Sprint 4 12-check verify prompt |
| 2.7 | Hermes | Run verify, report |
| 2.8 | You | If green, commit Sprint 4 (2–3 commits) |

### 3. Sprint 4.5 — Patent Figure Ingestion (~1 day)

| Step | Owner | Action |
|---|---|---|
| 3.1 | You | Send combined kickoff+verify prompt (from playbook) |
| 3.2 | Hermes | Write plan, build straight through, run verify |
| 3.3 | You | Review diff + verification; commit (1 commit) |

### 4. Cross-cutting health check (recommended)

| Step | Owner | Action |
|---|---|---|
| 4.1 | You | Send health check prompt before starting Sprint 5 |
| 4.2 | Hermes | Run 10-point read-only audit, report |
| 4.3 | You | Review for drift; address before Sprint 5 |

### 5. Sprint 5 — Commercial Usage Signals MVP (largest sprint)

| Step | Owner | Action |
|---|---|---|
| 5.1 | You | Ask Hermes to summarize existing scope doc + list top 3 risks |
| 5.2 | Hermes | Summarize, no impl plan yet |
| 5.3 | You | Debate scope; revise scope doc if needed |
| 5.4 | You | Send Sprint 5 kickoff (after scope approved) |
| 5.5 | Hermes | Write impl plan to `.hermes/plans/2026-XX-XX_sprint-5-usage-signals-impl.md`, stop |
| 5.6 | You | Review plan, approve |
| 5.7 | Hermes | Build 8 chunks (migration → collectors → scoring → backfill → API → narrative → frontend → expiry integration) |
| 5.8 | You | Review each chunk, approve next |
| 5.9 | You | Send Sprint 5 16-check verify (language audit = hard stop) |
| 5.10 | Hermes | Run verify, report |
| 5.11 | You | If green, commit Sprint 5 (4–5 commits) |

### 6. Sprint 6 — Topics + News + Highlights + Newsletter (4 sub-sprints)

| Sub | Steps | Sequence |
|---|---|---|
| 6A | Kickoff → plan → build → 10-check verify → commit (1) | Highlights data layer |
| 6B | Kickoff → plan → build → 13-check verify → commit (2) | **Prereq: Sprint 4.5 done** |
| 6C | Kickoff → plan → build → 11-check verify → commit (2) | Auto-matching + alerts |
| 6D | Kickoff → plan → build → 11-check verify → commit (2) | **No broad sends without explicit approval** |

### 7. Sprint 7 — SaaS Foundation

| Step | Owner | Action |
|---|---|---|
| 7.1 | You | Send Sprint 7 kickoff |
| 7.2 | Hermes | Write plan, stop |
| 7.3 | You | Review plan |
| 7.4 | Hermes | Chunk 1 (Auth) → stop |
| 7.5 | You | Review, approve |
| 7.6 | Hermes | Chunk 2 (Multi-tenancy migration) → stop |
| 7.7 | You | Review, approve |
| 7.8 | Hermes | Chunk 3 (Stripe — TEST MODE only) → stop |
| 7.9 | You | Review, approve |
| 7.10 | Hermes | Chunk 4 (Quotas + entitlements) → stop |
| 7.11 | You | Review, approve |
| 7.12 | Hermes | Chunk 5 (Account + exports) → stop |
| 7.13 | You | Send Sprint 7 20-check verify (auth/billing = hard stops) |
| 7.14 | Hermes | Run verify, report |
| 7.15 | You | If green, commit Sprint 7 (5 commits, one per chunk) |
| 7.16 | You | **Do not switch Stripe to production** without explicit approval |

### 8. Sprint 8 — Commercial API & Exports

| Step | Owner | Action |
|---|---|---|
| 8.1 | You | Send Sprint 8 kickoff |
| 8.2 | Hermes | Plan → 6 chunks (API keys → endpoints → usage tracking → webhooks → exports → OpenAPI docs) |
| 8.3 | You | Send 18-check verify |
| 8.4 | You | If green, commit Sprint 8 (6 commits) |

## Post-launch / ongoing

| Item | Cadence | Action |
|---|---|---|
| Plan-drift audit | Quarterly or before strategy changes | Send playbook prompt; review drift |
| Cross-cutting health check | Between every sprint | Read-only state snapshot |
| External validation | Before/during Sprint 5 | Test with 1–2 real prospects — no external feedback yet |
| Cost model verification | Before Sprint 7 launches paid tiers | Per-user AI compute attribution + margin check |
| Decommission portable | After 1 month of clean operation on consolidated repo | Delete LEGACY tarball and patent-pulse2 GitHub repo |

## Quick reference — which prompt to send when

| Situation | Prompt |
|---|---|
| Sprint 3 mid-chunk (where we are now) | Use the Chunk 4 prompt I drafted in chat |
| Sprint 3 Chunk 4 done | Chunk 5 prompt (drafted) |
| Sprint 3 Chunk 5 done | Sprint 3 verify prompt (playbook) |
| Sprint 3 verified | Sprint 4 kickoff (playbook) |
| Sprint 4 done | Sprint 4 verify (12 checks) |
| Sprint 4 verified | Sprint 4.5 combined kickoff+verify |
| Sprint 4.5 verified | Health check prompt, then Sprint 5 scope summary request |
| Sprint 5 scope debated | Sprint 5 implementation kickoff |
| Sprint 5 done | Sprint 5 verify (16 checks; language audit hard-stop) |
| Sprint 5 verified | Sprint 6A kickoff |
| Sprint 6A done | 6A verify; then 6B kickoff (after Sprint 4.5 confirmed) |
| Sprint 6B done | 6B verify; then 6C kickoff |
| Sprint 6C done | 6C verify; then 6D kickoff |
| Sprint 6D done | 6D verify (test deliveries only) |
| Sprint 6 fully done | Sprint 7 kickoff |
| Sprint 7 each chunk done | Chunk-specific review, then approve next |
| Sprint 7 done | Sprint 7 verify (20 checks; auth/billing hard-stops) |
| Sprint 7 verified | Sprint 8 kickoff |
| Sprint 8 done | Sprint 8 verify (18 checks) |
| Between any two sprints | Cross-cutting health check |
| Drift suspected | Plan-drift audit |
| Revenue urgency rises | Skip ahead to Sprint 7 after Sprint 2; resume Sprints 3–6 after |

## Hard rules — re-stated for any agent reading this doc

1. **No git commands by Hermes.** You commit, Hermes codes.
2. **No silent deviations.** If reality contradicts the plan, STOP and report with options.
3. **No "free to use" or "public domain" anywhere** in user-facing strings.
4. **All AI output must be cached as `AIArtifact`** and labeled with `AISourceFooter`.
5. **Patent figures: link-only**, never host or re-serve.
6. **Stripe: test mode only** until explicit approval to go live.
7. **Newsletter: test deliveries only** until explicit approval for broad send.
8. **Reuse existing components** (`PatentCard`, `EmptyState`, `ErrorState`, `FreshnessBanner`, `AISourceFooter`, `useAsyncAction`).
9. **Match existing patterns** (URL state pattern from `/opportunity` and `/expiry`).
10. **Run `npm run build` + `pytest -q` between chunks.** Never let a chunk land with a broken build.

## Risks and open questions

1. **No external validation yet.** Product direction is based on your own usage/reflection. Test with 1–2 real patent-literate prospects before Sprint 5 or 6 ships.
2. **Cost model unverified.** $10/yr Lite tier may not cover AI compute. Verify before launching paid tiers in Sprint 7.
3. **Hermes silent-deviation pattern.** Caught twice (Sprint 2C `days_ahead=1`, Sprint 3 family-banner conditional removal). Tighten the kickoff prompts going forward to explicitly require "DEVIATION DETECTED → options → wait for approval" rather than just "flag any deviation."
4. **Forward citations empty.** Sprint 3 plumbed the field but no ingestion populates it. Acceptable for now (empty states handle it) but worth a follow-up sprint or task once we identify an ingestion source.
5. **Per-member family legal status missing.** Family tab shows "Unknown" for non-self members. Requires INPADOC integration — defer.
6. **Sprint 7 sequencing flexibility.** If revenue urgency rises, Sprint 7 can move up after Sprint 2. Document the choice when made.
7. **Production deployment.** No production deploy path defined yet. Sprint 7 ships auth + billing; an actual production environment (Vercel + Render/Fly/etc) is a separate concern.

## File pointers

| File | Purpose |
|---|---|
| `ROADMAP.md` | Full sprint specs, sequencing rationale |
| `PRODUCT_STRATEGY.md` | Product pillars, surface map, pricing tiers |
| `AGENTS.md` | Agent operating rules — read at the start of every sprint |
| `.hermes/plans/` | Sprint plans (one file per sprint) and scope docs |
| `backend/alembic/versions/` | All migrations |
| `backend/tests/` | Test suite (180+ passing) |
| `frontend/src/app/` | Next.js pages (16 routes) |
| `frontend/src/components/` | Reusable React components |

## Total remaining commit count (rough estimate)

| Phase | Commits |
|---|---|
| Sprint 2C | 2 |
| Sprint 3 | 2 |
| Sprint 4 | 2–3 |
| Sprint 4.5 | 1 |
| Sprint 5 | 4–5 |
| Sprint 6A | 1 |
| Sprint 6B | 2 |
| Sprint 6C | 2 |
| Sprint 6D | 2 |
| Sprint 7 | 5 |
| Sprint 8 | 6 |
| **Total** | **~29–32 commits to ship the full V1 roadmap** |

---

*Last updated: 2026-05-23. Update this doc as sprints close or scope shifts.*
