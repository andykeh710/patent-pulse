# V3/V4 Continuation Roadmap

**Date:** 2026-06-15
**Status:** Post-launch planning. Controlled launch complete. Open signup blocked by Resend.
**App:** Live at https://inventionindex8.com

---

## Corrected Production Status

- Core services: healthy (backend, frontend, db, redis, worker, beat)
- Alembic: 0034 (head)
- Health: `{"db":"ok","redis":"ok","alembic_head":"0034","resend":"degraded","overall":"degraded"}`
- Public routes: bare domain 200, www 301 redirect, /docs 200
- Caddy: www redirect validated + reloaded
- `.env` duplicates: cleaned
- Redis password: rotated
- Resend: still unavailable — blocks magic-link/open signup
- Server commit: may still be `27df754`; latest is `4d78dca`

---

## Remaining Post-Launch Stabilization Checklist

| # | Item | Priority | Command / Notes |
|---|------|----------|----------------|
| 1 | Fix Resend | P0 | Get valid API key at resend.com, verify sending domain, set RESEND_API_KEY + EMAIL_FROM_ADDRESS in .env, restart backend |
| 2 | Verify assignee backfill | P1 | `docker compose exec db psql -U patent -d patent_pulse -c "SELECT entity_type, COUNT(*) FROM assignees GROUP BY entity_type;"` |
| 3 | Pull/deploy latest commit | P2 | `git pull origin release/revamp-launch-validation && docker compose build backend && docker compose up -d backend` |
| 4 | Decide open-signup posture | P1 | If Resend fixed: enable open signup. If not: continue manual provisioning. |

---

## V3 — Product Depth, Reliability, Retention

**Goal:** Turn the V2 commercial revamp into a daily-use intelligence product
with deeper personalization, stronger evidence, and operational resilience.

### V3.1 — Personalized Today + Onboarding

**Features:**
- Persona-based onboarding defaults (competitive intel, R&D scouting, licensing, investing)
- Industry/CPC-based starter watchlists generated at onboarding
- Today cards: personalized by followed companies, saved searches, topic subscriptions
- "Since your last visit" improvements: per-section deltas, not just one timestamp
- Empty-state guidance when no personalization exists: "Search an area → save a patent → get better briefings"

**Dependencies:** Onboarding flow exists (partial). Today habit engine (Sprint 3) works.
**Acceptance:** New user reaches personalized Today within 5 minutes of onboarding.

### V3.2 — Watchlists + Saved Intelligence

**Features:**
- Watchlist: add Topic/Themes tab (follow technology areas)
- Watchlist: Recently Viewed section (privacy-safe, client or server)
- Saved searches: naming, editing, reordering
- Export saved watchlist as CSV/shareable link
- Watchlist email digest (gated on Resend)

**Dependencies:** Watchlist 3-tab workspace (Sprint 7). Saved searches (Sprint 4.5). Company follow (Sprint 5).
**Acceptance:** User has 5+ saved items within first week.

### V3.3 — Company + Inventor Follow

**Features:**
- Follow/unfollow on company list page (not just detail)
- Inventor follow (new model: user_inventor_follows)
- Company "What Changed" module: filing deltas vs previous period
- Company comparison: side-by-side portfolio diff
- Email alerts for followed company activity (gated on Resend)

**Dependencies:** Company follow backend (Sprint 5). Company detail page (Sprint 5).
**Acceptance:** User follows 3+ companies, sees filing activity changes.

### V3.4 — Research Paper Ingestion

**Features:**
- ArXiv API integration: search + ingest paper metadata
- Paper-to-patent linking: citing patents, cited-by patents
- Research paper cards on Today, Patent Detail, Company pages
- "Papers → Patents" opportunity signal: emerging research without patent coverage

**Dependencies:** New models needed (papers, paper_citations). ArXiv API key.
**Acceptance:** Papers surface as relevant signals on patent and company pages.

### V3.5a — Assignee Enrichment with Provenance

**Current state:** 16,723 assignees with normalized names + patent counts.
entity_type is NULL for 14,236 rows (2,487 have old heuristic values that are
NOT authoritative). Country is NULL for all rows.

**Source:** USPTO PatentsView `/assignee` API (free, no auth, rate-limited).
Provides: `assignee_id`, `organization`, `individual_name_first`, 
`individual_name_last`, `entity_type` (organization/person), `country`.

**Design:**

```
assignees table columns (new):
  entity_type           TEXT  -- 'organization' | 'person' | NULL
  country               TEXT  -- two-letter country code or NULL
  enrichment_source     TEXT  -- 'patentsview' | 'manual' | NULL
  enrichment_confidence TEXT  -- 'high' | 'medium' | 'low' | NULL
  enrichment_verified_at TIMESTAMPTZ
  source_assignee_id    TEXT  -- PatentsView assignee_id for audit trail
```

**Data flow:**
1. New Celery task: `enrich_assignees_from_patentsview`
2. Query PatentsView `/assignee` endpoint, match by name against our normalized names
3. Populate entity_type, country, enrichment_source, confidence, source_assignee_id
4. Store match confidence based on name similarity (exact match = high, fuzzy = medium)
5. Re-run periodically to catch newly added assignees

**UI behavior:**
- Show entity_type/country badges ONLY when `enrichment_source` is NOT NULL
- If source is NULL: show no badge (neutral) — never show "unknown" or guessed value
- Add hover tooltip: "Source: USPTO PatentsView · Confidence: high"
- On Company Intelligence pages: show enrichment provenance in metadata section

**Test coverage:**
- PatentsView API mock: returns assignee metadata for known names
- Backfill: stores entity_type + country + provenance
- UI: hides badges when no source, shows with provenance when enriched

**Acceptance:** 70%+ of top-1,000 patent-count assignees have verified entity_type
from PatentsView. All enriched rows have non-NULL enrichment_source.

### V3.5b — Evidence Packets

**Features:**
- Patent "Evidence Packet": official links, family tree, expiry confidence breakdown, usage signals, citation graph, maintenance fee status
- Confidence labels on every expiry/legal claim
- "Why this estimate" expandable explanation
- Source links: USPTO Public PAIR, Google Patents, Espacenet, WIPO Patentscope

**Dependencies:** Patent detail page (Sprint 4). Expiry Radar (Sprint 6).
**Acceptance:** Every patent card has at least 3 verifiable source links.

### V3.6 — Admin Tools

**Features:**
- Manual account provisioning UI (while Resend is degraded)
- User activation state dashboard
- Feedback review queue
- Backfill trigger + progress monitor
- Celery task monitoring

**Dependencies:** Admin panel (existing). Retention endpoints (Sprint 7).
**Acceptance:** Andy can provision accounts + monitor backfills from admin panel.

### V3.7 — Operational Hardening

**Features:**
- Backend venv fix (Python 3.12) for local dev
- Backend test suite runnable locally
- Celery beat crash alerting (dead man's switch or health check)
- Database backup automation (daily pg_dump to off-server storage)
- Log aggregation / structured logging
- Sentry alerting for production errors
- Rate limiting on feedback/admin endpoints

**Dependencies:** DevOps/ops. Hetzner VPS access.
**Acceptance:** Backend tests pass locally. Celery beat failures detected within 1 hour.

---

## V4 — Network Effects, Community Value, Distribution

**Goal:** Extend the app beyond a solo research tool into a shared intelligence
platform with network effects and commercial-grade distribution.

**Gate:** Open signup must be available (Resend fixed). Do not start V4 until
Resend is operational and at least V3.1 (personalized onboarding) is shipped.

### V4.1 — Public/Community Pages

**Features:**
- Public trend pages: technology areas with patent activity charts
- Public company profile pages: portfolio summary, top inventors, recent activity
- Public patent "share card": title, summary, assignee, status, expiry estimate, key figure
- SEO-optimized: meta tags, structured data (JSON-LD), sitemap
- Community bookmarking: users can publicly bookmark interesting patents

**Dependencies:** Open signup. Public route infrastructure (existing: /t/[slug], /blog).
**Acceptance:** Public trend page ranks for "patent activity in [technology]".

### V4.2 — Weekly "Invention Signals" Report

**Features:**
- Auto-generated weekly public report: top trends, notable patents, company activity
- Sections: Patent Activity Heatmap, Company Moves, Emerging Technologies, Expiring Opportunities
- Email distribution to subscribers (gated on Resend)
- Web version with shareable URL
- Archive/browse past reports

**Dependencies:** Resend operational. Existing briefing/weekly infrastructure.
**Acceptance:** One automated report per week, delivered to subscribers.

### V4.3 — Research Brief Library

**Features:**
- Curated collections: "Battery Technology 2024-2026", "CRISPR Delivery Vectors"
- AI-generated briefs synthesizing patent + paper evidence
- Shareable brief URLs
- User-submitted briefs (community contributions)

**Dependencies:** Research paper ingestion (V3.4). Content generation pipeline.
**Acceptance:** 3+ curated briefs with 10+ patents/papers each.

### V4.4 — Curated Collections + Community Voting

**Features:**
- User-curated watchlists made public (optional)
- Community voting: upvote interesting patents/inventions
- "Most interesting this week" leaderboard
- Comment/discussion on patents (moderated)

**Dependencies:** Open signup. Public profiles. Content moderation plan.
**Acceptance:** Top-voted patents visible to all users.

### V4.5 — Persona-Specific Landing Flows

**Features:**
- Founder/inventor landing: "Track your space, find expired IP, monitor competitors"
- Investor landing: "Due diligence signals, portfolio monitoring, tech scouting"
- Law firm landing: "Prior art search, portfolio analysis, expiry tracking"
- R&D landing: "Technology landscaping, white space analysis, emerging signals"
- Each flow: tailored onboarding, starter watchlist, sample briefing

**Dependencies:** Open signup. Onboarding flow. Persona defaults (V3.1).
**Acceptance:** Conversion rate measurable per persona flow.

### V4.6 — Social/Content Engine

**Features:**
- Auto-generated LinkedIn posts from patent signals
- Twitter/X share cards for interesting patents
- Weekly content digest for LinkedIn/newsletter
- Embeddable patent cards for external blogs/sites

**Dependencies:** Content generation pipeline (existing LinkedIn post generator). Open signup.
**Acceptance:** One-click share to LinkedIn from any patent detail page.

### V4.7 — Premium Layer

**Features:**
- Export limits on free tier; unlimited on paid
- Advanced analytics: portfolio comparison, technology landscaping reports
- API access for programmatic patent search
- Priority support + custom briefs
- Team/org accounts with shared watchlists

**Dependencies:** Stripe billing (existing, TEST MODE). Open signup. Auth system.
**Acceptance:** Stripe checkout → user upgraded → premium features unlocked.

---

## Recommended Sequencing (Next 2 Weeks)

### Week 1 — Stabilization + Quick Wins
1. Fix Resend API key (Andy) — unblocks open signup
2. Pull/deploy latest commit (`4d78dca`) to production
3. Verify assignee backfill status
4. Decide open-signup posture
5. Backend venv fix for local dev (Python 3.12)
6. Begin V3.1: persona-based onboarding defaults

### Week 2 — V3 Depth
7. V3.1: Personalized Today improvements
8. V3.6: Admin provisioning UI (critical if Resend still broken)
9. V3.5: Evidence packet improvements on patent detail
10. V3.7: Celery beat monitoring + backup automation

### Week 3+ — V3 Completion → V4 Gate
11. V3.2-V3.4: Watchlist topics, research papers, company follow
12. Open signup available → begin V4.1 public pages
13. V4.2: Weekly report automation
