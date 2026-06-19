# V4.0 — Community Trust & Safety Model

## Confidential Disclosure Warning

All UIs that accept public user content MUST display:

> **Confidential Disclosure Warning**
> Do not post confidential invention details, trade secrets, unpublished patent ideas, or privileged legal information. Community content is not legal advice. Verify patent status with official registers before relying on any expiry, freedom-to-operate, or licensing signal.

Display at: submission form, comment box, public profile editor, collection description editor.

## Moderation Architecture

### Report Flow
1. User clicks "Report" on any public object
2. Modal: select reason (spam, confidential, inaccurate, harassment, other)
3. Optional description text
4. Creates `moderation_event` row
5. Admin dashboard shows queue sorted by report count + recency

### Admin Actions
- **Dismiss**: close report, no action
- **Hide**: visibility → `moderated`, object hidden from public
- **Delete**: visibility → `removed`, soft-delete
- **Suspend user**: prevent future public actions for N days
- **Trust contributor**: flag user as trusted, skip pre-moderation

### Rate Limits (when implemented)
- 30 public actions per minute per user
- 5 reports per minute per user
- 10 comments per minute per user

## Trust Model

| Level | Criterion | Effect |
|-------|-----------|--------|
| **Verified email** | Email confirmed | Can follow, save |
| **Active user** | 10+ interactions | Can create collections |
| **Trusted contributor** | Admin-flagged, 50+ useful votes | Can publish public briefs |
| **Expert** (V4.5+) | Domain-verified | Expert annotations, featured content |

## Private Data Rules

- User email, preferences, saved searches NEVER exposed publicly
- `owner_user_id` on public objects links to an opt-in public profile only
- Public profiles: display_name, bio, public collections — optional
- No user graph, follower list, or activity feed is public by default
- Collection ownership: visible only if owner has public profile

## Content Provenance

- AI-generated content labeled in UI
- Source data linked to evidence_items
- Estimated vs verified legal status always displayed
- No patent claim certainty without source-backed evidence

## Emergency Measures

- Global content freeze: admin can disable all public posting
- User-level mute: suspend specific user from public actions
- Object-level hide: single report can hide content pending review
