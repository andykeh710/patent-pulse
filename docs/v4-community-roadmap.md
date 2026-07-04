# V4 Community Roadmap

## V4.0 — Foundation (CURRENT PHASE)

**Goal:** Design community architecture before any code. No public features yet.

Deliverables:
- [x] `docs/v4-community-strategy.md`
- [x] `docs/v4-community-data-model.md`
- [x] `docs/v4-community-trust-safety.md`
- [ ] `docs/v4-community-roadmap.md` (this file)
- [ ] Migration 0040: `intelligence_items`, `evidence_items`, `collections`, `collection_items`
- [ ] Visibility model enforcement at query level
- [ ] Private → unlisted → public upgrade path
- [ ] Confidential disclosure warning component

## V4.1 — Public Read-Only Intelligence

Pages:
- `/topics/{slug}` — public topic overview pages
- `/companies/{slug}` — public company pages
- `/research/{slug}` — public research briefs
- `/patents/{id}` — public-safe patent detail page

Requirements:
- Evidence-backed content only
- SEO metadata on all public pages
- CTA to sign up / create private watchlist

## V4.2 — Shareable Briefs + Collections

- Users can create private collections
- Share collection via unlisted link
- Briefs: private → unlisted → public workflow
- Follow public collections

## V4.3 — Voting Systems

A. Product Feature Voting
- `/roadmap` — feature request board
- Upvote, comment, status tracking
- Admin dashboard for merging/managing

B. Intelligence Voting
- useful/not_useful/interesting/overhyped/needs_review
- Applied to public intelligence objects only
- Auth required, rate limited

## V4.4 — Social Components

- Public profiles (opt-in)
- Follow users, collections, topics
- Comments on public briefs and collections
- Activity feed for followed topics

## V4.5 — Moderation + Trust

- Report content flow
- Admin review dashboard
- Trusted contributor flags
- Reputation signals (useful vote count, collection followers)

## V4.6 — API / Data Product

- RSS feeds for public topic pages
- Webhook alerts for saved searches
- API access for enterprise
- Embeddable widgets
- Team dashboards

## Implementation Gating

V4.1 cannot start until:
- V3 punch list is resolved
- USPTO ingestion is operational
- DB latest publication date advances beyond May 28

V4.3+ cannot start until:
- Public objects exist and have evidence
- Moderation infrastructure is deployed
