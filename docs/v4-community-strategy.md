# V4.0 — Community Intelligence Layer — Strategy

**Status:** Planning — do not implement until V3 punch list is resolved
**Rule:** Community features attach to useful product objects, not empty social

## V4 North Star

Make InventionIndex8 the place people go to understand what the world is inventing, which companies are moving, which technologies are accelerating, and where opportunities are emerging — privately first, publicly when ready.

## Core Principle

Community features must attach to objects that already have value:
- patents
- companies
- topics
- expiry opportunities
- saved searches
- watchlists / collections
- public insight cards
- expert notes (later)

Do NOT build random social posting, private messaging, or creator marketplace without anchored utility.

## Visibility Model

| Level | Description | Who can see |
|-------|-------------|-------------|
| `private` | Default. Only the owner. | Owner only |
| `unlisted` | Anyone with link, not indexed. | Link holders |
| `organization` | Team members only (V4.3+). | Org members |
| `public` | Visible on site, searchable. | Everyone |
| `moderated` | Hidden pending review. | Admin + owner |
| `removed` | Soft-deleted by moderation. | Admin only |

## Sharing Rules

1. Public sharing requires explicit opt-in — no accidental leaks.
2. Private data (email, preferences, saved searches) never exposed publicly.
3. User profiles are opt-in public — default is private.
4. All shared content requires source/evidence metadata.
5. All AI-generated content must be labeled.
6. No legal/patent certainty claims without verified source confirmation.

## Confidential Disclosure Warning

Any UI that accepts public content must show:

> **Confidential Disclosure Warning**
> Do not post confidential invention details, trade secrets, unpublished patent ideas, or privileged legal information. Community content is not legal advice. Verify patent status with official registers before relying on any expiry, freedom-to-operate, or licensing signal.

## Initial MVP Scope (V4.1–V4.2)

- Public topic pages (`/topics/{slug}`)
- Public company pages (`/companies/{slug}`)
- Shareable research briefs (private → unlisted → public)
- Private collections with optional unlisted sharing

## Deferred to V4.3+

- Public comments
- Public profiles
- Voting on intelligence objects
- Feature request voting
- Expert annotations
- Activity feeds
- Notifications

## Moderation Model

See `docs/v4-community-trust-safety.md` for full moderation design.

Minimum before any public content:
1. Report content mechanism
2. Admin review queue
3. Hide/delete content
4. User suspension
5. Audit log
