# Patent Pulse Landing Page — Design Spec

**Status:** Decisions locked 2026-05-29. Ready for implementation plan.
**Goal:** Replace the bare `/` → `/today` redirect with a polished marketing landing page that converts mixed-B2B visitors (patent attorneys / corporate IP / founders & investors) into Free signups or paid customers, while staying within AGENTS.md's no-overclaim culture.

---

## Locked decisions

| # | Decision | Choice |
|---|---|---|
| Q1 | Target audience | Mixed B2B (attorneys, corporate IP/R&D, founders/investors) |
| Q2 | Primary conversion goal | Dual CTA — "Get started free" + "See pricing" |
| Q3 | Brand voice | Confident-modern (evidence-backed, no hype, Linear/Stripe-style polish) |
| Q4 | Pricing display | Teaser on landing + dedicated `/pricing` page with feature matrix + FAQ |
| Q5 | Approach | Standard high-converting B2B structure (Approach A) with editorial flourishes — real data points, "show your work" hero copy |
| Q6 | Hero copy | "Patent intelligence with the receipts." + transparency-focused subhead |
| Q7 | Hero visual | Split layout — copy left, "weekly briefing preview" card right (CSS-rendered mock with real confidence labels, evidence tiers, self-cite chips) |
| Q8 | Value props | 4 cards in 2×2 grid, each with signature visual element from actual product (not generic icons) |
| Q9 | Use cases | 3 personas, neutral matched cards, order: attorneys → IP teams → founders |
| Q10 | Pricing highlight | Lifetime ("Best value") not Basic ("Most popular") — math is verifiable, customer count isn't |
| Q11 | Trust block + footer | Trust block before final CTA; 4-column footer; legal page skeletons included |
| Q12 | URL structure | Next.js route groups — `(marketing)`, `(app)`, `(auth)` — no URL changes, layout split via groups |

---

## Page structure — `/` (the landing)

Ten sections, top to bottom:

1. **Marketing nav** — text logo · Pricing · About · Sign in
2. **Hero** — split layout (copy left, briefing preview card right)
3. **Data strip** — `54,903 patents · USPTO · EPO · WIPO · Updated weekly · Evidence-backed`
4. **Value props** — 4 cards, 2×2 grid (Expiry / Usage signals / Trend narratives / Topics & alerts)
5. **Use cases** — 3 cards (Attorneys / IP teams / Founders)
6. **How it works** — 3-step explainer (Pick topics → Get briefings → Drill into patents)
7. **Pricing teaser** — 4 compact cards with Lifetime highlighted
8. **Trust block** — "We show our work" + facts strip
9. **Final CTA** — single "Get started free" button + "No credit card required"
10. **Footer** — 4 columns (Product / Company / Legal / Sources) + tagline

---

## Hero — copy and visual (highest-stakes section)

### Copy (Option 1 locked)

```
Patent intelligence with the receipts.

Track expiry, usage signals, and filing trends across USPTO, EPO,
and WIPO data — every claim labeled with confidence, every source
linked back. Subscribe to your topics for weekly briefings and
instant alerts.

[Get started free]  [See pricing]
```

### Visual (Option A locked) — Split layout

Left column: headline + subhead + dual CTA.
Right column: a CSS-rendered "weekly briefing preview" card showing real-looking patent data:

```
╭─ Your weekly briefing ─────────────╮
│  G06F · Computing                   │
│                                     │
│  ▸ USPTO:20260144033                │
│    Score 89  · strong               │
│    confidence: high                 │
│                                     │
│  ▸ USPTO:20260144068                │
│    Score 86  · strong               │
│    confidence: high                 │
│    ⚠ self-citation risk             │
│                                     │
│  3 more · view all →                │
╰─────────────────────────────────────╯
```

This is **not a screenshot** — it's a CSS-rendered card built from Tailwind components. The card uses real-looking patent doc IDs, real confidence labels (`high`, `medium`, `low`), real evidence tiers (`strong`, `medium`, `weak`), and the actual self-cite warning chip from Sprint 5. The same component can be reused on `/pricing` and in the demo section.

### Mobile breakpoint

On mobile (< md): copy stacks above briefing preview, both centered. CTA buttons stack to full-width.

---

## Value Props — 4 cards, 2×2 grid

Each card has a **signature visual element** from the actual product instead of a generic icon, reinforcing the "we show our work" angle.

### Card 1 — Expiry intelligence
- **Visual:** Pill row showing confidence labels — `active_estimated` `expiring_soon` `lapsed_possible` `lapsed_confirmed`
- **Copy:**
  > **Expiry intelligence, calibrated.**
  > Estimated expiry dates with explicit confidence labels — not raw guesses. Active family members in other jurisdictions surfaced when relevant. Every estimate links to the official register for verification.

### Card 2 — Usage signals
- **Visual:** Tier badges `strong` `medium` `weak` + `⚠ self-citation risk` chip
- **Copy:**
  > **Usage signals, evidence-backed.**
  > See how patent ideas appear in newer art — with a tier (strong/medium/weak) on every piece of evidence and a source link beneath. No "this patent is used by Company X" claims. Only patterns you can verify.

### Card 3 — Trend narratives
- **Visual:** "AI-generated · Claude Sonnet" badge above a 2-line narrative snippet
- **Copy:**
  > **Trend narratives, in plain English.**
  > Filing surges and assignee movement explained by Claude Sonnet — the model that follows structured-JSON instructions reliably. Every narrative cites the underlying patents. Refreshed as new filings drop.

### Card 4 — Topics & alerts
- **Visual:** Subscription card mock showing `Topic: G06F` `Mode: weekly_digest + instant_alert` `Threshold: ≥ 60`
- **Copy:**
  > **Your topics. Briefed weekly. Alerted instantly.**
  > Subscribe to topics by CPC class, keyword, or assignee — with optional opportunity-score thresholds. Get instant alerts on high-priority matches and a Sonnet-written briefing every Sunday morning.

---

## Use Cases — 3 personas

Section header: **"Who it's for"**

### Card 1 — For patent attorneys & law firms
> Surveil portfolios with confidence-labeled expiry estimates. Build evidence packets with source citations linked to official registers. Hand clients reports they can verify.
>
> *Tracks: expiry windows · active family risk · cite-graph signals*

### Card 2 — For corporate IP teams
> Monitor your CPC areas for filing surges, family expansions, and expiry opportunities. Track usage signals showing how your prior art shows up in newer filings — with evidence tiers, not claims.
>
> *Tracks: competitor filings · expiry windows · usage signals*

### Card 3 — For founders & investors
> Find ideas approaching estimated expiry in your thesis areas — with confidence labels so you know what's open vs. uncertain. Subscribe to topics tied to your thesis. Verify before you commit.
>
> *Tracks: expiring opportunities · whitespace topics · weekly briefings*

**No per-card CTAs.** All three feed into the same "Get started free" final CTA.

---

## How It Works — 3 steps

Section header: **"How it works"**

```
1. Pick your topics
   Subscribe by CPC class, keyword, assignee, or
   opportunity-score threshold.

2. Get briefings + alerts
   Sunday morning weekly digest. Instant alerts on
   high-priority matches.

3. Drill into patents
   Full intelligence per patent — expiry, family,
   usage signals, AI narratives, source links.
```

Visual: horizontal 3-step row with simple connecting lines on desktop, vertical stack on mobile.

---

## Pricing Teaser — 4 cards

Lifetime highlighted with **"Best value"** badge (NOT "Most popular" — no customers yet).

| | Free | Basic | Lifetime ★ | Enterprise |
|---|---|---|---|---|
| Price | $0 | $8 / year | $108 once | $1,000 / year |
| Topics | 1 | Unlimited | Unlimited | Unlimited |
| Alerts | 5/week | Unlimited | Unlimited | Unlimited |
| CSV export | — | ✓ | ✓ | ✓ |
| PDF reports | — | — | ✓ | ✓ |
| API access | — | — | — | ✓ (300/min) |
| CTA | `Get started` | `Choose Basic` | `Choose Lifetime` | `Choose Enterprise` |

Below: "See full feature comparison →" → `/pricing`

---

## `/pricing` — dedicated page

**Structure:**
1. Same 4 cards at top
2. Full feature matrix table (extends teaser with: weekly digest, admin tools, support tier, billing cycle, auth method)
3. FAQ block — 9 questions covering: tier switching, cancellation, refunds, lifetime definition, taxes/VAT, invoices, data export on cancel, API key behavior, GDPR delete

---

## Trust Block — "We show our work"

Sits between Pricing teaser and Final CTA:

```
We show our work.

Patent Pulse calibrates uncertainty. We label every estimate.
We cite every source. We don't claim freedom-to-operate, we
don't invent market data, and we tell you when our confidence
is low.

Read the limitations →  /about

Data: USPTO + EPO + WIPO    Updated weekly
AI: Claude Sonnet narratives    Not legal advice
```

---

## Final CTA

```
Ready to read the patent landscape?

[Get started free]
No credit card required
```

---

## Footer

Four columns:
- **Product:** Pricing · Sign in
- **Company:** About · Limitations · Contact
- **Legal:** Terms · Privacy · GDPR / delete
- **Sources:** USPTO · EPO · WIPO (each links to the patent office's main site)

Tagline below:
> Patent Pulse · Evidence-backed patent intelligence · Verify with official registers.

Plus `© 2026`.

---

## Technical architecture

### Route group layout

```
src/app/
├── layout.tsx                      # Root: <html><body><AuthProvider>
│
├── (marketing)/                    # No sidebar; top nav only
│   ├── layout.tsx
│   ├── page.tsx                    # /
│   ├── pricing/page.tsx            # /pricing
│   ├── about/page.tsx              # /about (moved here)
│   ├── terms/page.tsx              # /terms (NEW)
│   ├── privacy/page.tsx            # /privacy (NEW)
│   └── contact/page.tsx            # /contact (NEW; mailto link)
│
├── (app)/                          # Existing NavSidebar + main layout
│   ├── layout.tsx
│   ├── today/page.tsx
│   ├── expiry/page.tsx
│   ├── opportunity/page.tsx
│   ├── trends/page.tsx
│   ├── patents/[id]/page.tsx
│   ├── search/page.tsx
│   ├── themes/page.tsx
│   ├── themes/[id]/page.tsx
│   ├── companies/page.tsx
│   ├── watchlist/page.tsx
│   ├── account/page.tsx
│   ├── account/billing/page.tsx
│   ├── admin/page.tsx
│   └── admin/ai-runs/page.tsx
│
└── (auth)/                         # Centered no-nav layout
    ├── layout.tsx
    ├── login/page.tsx
    ├── login/verify/page.tsx
    └── unsubscribed/page.tsx
```

URLs do NOT include the parenthesized group name. `/today` not `/(app)/today`.

### Auth-aware root redirect

Middleware at `/` checks the auth_session cookie:
- Unauthenticated → render landing page
- Authenticated → 302 redirect to `/today`

On cookie parse/verify error: default to landing page (never block visitors with errors).

### Marketing top nav (replaces the absent sidebar on marketing pages)

```
┌──────────────────────────────────────────────────────────┐
│  Patent Pulse              Pricing  About  Sign in       │
└──────────────────────────────────────────────────────────┘
```

Mobile (< md): hamburger menu collapses the 3 links.

### Metadata + SEO

Per-page metadata exports in Next.js App Router pattern:

- `/`: `title: "Patent Pulse — Patent intelligence with the receipts"`, description from hero subhead, OG image
- `/pricing`: `title: "Pricing — Patent Pulse"`, description listing all 4 tiers + prices
- `/about`: existing copy; add description from /about's first paragraph

OG image: 1200×630 PNG. Design: solid Tailwind `sky-600` background (#0284c7 — the brand primary-600), white text "Patent Pulse" as logo (large), tagline below "Patent intelligence with the receipts" (smaller). Generated once via a one-off script using Sharp or any image lib, committed to `public/og-image.png`. (V1.1: switch to `@vercel/og` for dynamic per-page images.)

Favicon: check existing — if missing, generate simple text-mark from logo.

robots.txt: allow `/`, `/pricing`, `/about`, `/terms`, `/privacy`; disallow `/admin/*`. Most routes default to allowed.

### Performance

- Server Components by default — only client components where interactivity demands
- `next/image` for any image assets
- System fonts (already in use) — no Google Fonts integration
- The briefing preview card is pure CSS/Tailwind, not an `<img>`

### Mobile responsiveness

Tailwind default breakpoints: `sm` (≥640px), `md` (≥768px), `lg` (≥1024px). Mobile-first base styles assumed.

| Section | Mobile (< sm) | Tablet (sm–md) | Desktop (≥ md) |
|---|---|---|---|
| Hero split | Stacks vertical (copy then preview) | Stacked still | Side-by-side split |
| Data strip | Wraps to multiple lines | Single-line wrap | Single line |
| Value props 2×2 | 1 column | 2 columns | 2×2 grid |
| Use cases 3-up | 1 column | 1 column | 3 columns |
| How-it-works | Vertical stack | Vertical stack | Horizontal 3-step row |
| Pricing 4-up | 1 column | 2×2 | 4 columns |
| Footer 4-column | Accordion (collapsed sections) | 2×2 | 4 columns |

---

## Implementation chunks (estimated 9 chunks, ~940 LOC)

| # | Chunk | LOC | Dependencies |
|---|---|---|---|
| M1 | Route group restructure: move existing routes into `(app)`; create `(marketing)` and `(auth)` group dirs | ~0 LOC, all `git mv` | none |
| M2 | Root layout split: minimal root layout + `(marketing)/layout.tsx` (top nav) + `(app)/layout.tsx` (existing sidebar) + `(auth)/layout.tsx` (centered) | ~80 | M1 |
| M3 | Auth-aware middleware on `/` — read session cookie, redirect to `/today` if valid | ~20 | M2 |
| M4 | Landing page `(marketing)/page.tsx` — hero, data strip, value props, use cases, how-it-works, trust block, final CTA | ~350 | M2 |
| M5 | Dedicated `/pricing` page — 4 cards, feature matrix, FAQ block | ~200 | M2 |
| M6 | Briefing-preview component — reusable CSS-rendered card for hero visual | ~80 | none |
| M7 | Skeleton `/terms`, `/privacy`, `/contact` pages — see "Skeleton legal content" below | ~120 | M2 |
| M8 | Metadata + OG image + favicon + robots.txt | ~40 | M2 |
| M9 | Mobile responsive testing + polish across all sections | ~50 | M4, M5 |
| **Total** | **~940 LOC + file moves** | ~1 day Hermes |

### Skeleton legal content (M7)

The three legal pages must be functional (no 404, no broken Stripe/Resend validation) but the legal text itself is placeholder — you'll replace it with counsel-reviewed copy before public launch.

**`/terms`** — Minimum sections:
- Acceptance of terms
- Description of service ("patent intelligence tool")
- User accounts (magic-link auth, deletion via /account)
- Paid subscriptions (Stripe handles billing; refund policy: case-by-case via support)
- Acceptable use (no automated scraping, no resale of bulk data)
- Intellectual property (your account data is yours; aggregated patent data we surface is from public patent office feeds)
- Disclaimer of warranty (not legal advice, expiry estimates are not guarantees)
- Limitation of liability
- Governing law (TBD — placeholder: jurisdiction of your operating entity)
- Changes to terms
- Contact: support@yourdomain.com

**`/privacy`** — Minimum sections:
- What we collect (email, magic-link sign-in metadata, topic subscriptions, Stripe customer ID, usage logs)
- What we don't collect (no third-party tracking pixels, no analytics by default)
- How we use it (deliver the service, billing, support)
- Third parties: Stripe (billing), Resend (email), Anthropic (AI narratives via cached artifacts only, no PII in prompts), OpenAI (embeddings, no PII)
- Data retention (email_deliveries kept anonymized; account deletion cascades)
- GDPR rights (access via /account, deletion via /account)
- Contact: privacy@yourdomain.com

**`/contact`** — Minimal page. Just a mailto link: "Email support@yourdomain.com" + maybe a paragraph about response times.

These three pages are FUNCTIONAL (links work, content is coherent, Stripe/Resend reviewers can read them and tick boxes) but the legal text needs counsel review before going live with paid traffic.

---

## Out of scope for this design (deferred to V1.1)

- Customer testimonials / case studies (no customers yet)
- Embedded video demos (production cost)
- Newsletter signup form (duplicates "Get started free")
- A/B testing infrastructure (need traffic first)
- i18n / multi-language (English-only V1)
- Custom Google Fonts (system fonts work fine)
- Scroll-triggered animations
- Logo image (text mark is sufficient for V1)
- Dynamic OG images (static PNG is fine; switch to `@vercel/og` later)
- Interactive demo / public read-only API for marketing
- Blog / Resources nav (no content yet)

---

## AGENTS.md compliance — language guardrails

Every piece of copy on the landing page MUST avoid:
- "free to use"
- "public domain"
- "is used by" / "this patent is used"
- "definitely used"
- "freedom to operate"
- Any claim of commercial usage without evidence tiers

Implementation MUST include a grep step against the new files before declaring done.

The landing page copy intentionally LEANS INTO the AGENTS.md culture as a positive feature ("we show our work", "every claim labeled with confidence") rather than as a defensive disclaimer.

---

## Success criteria

- Visitor lands on `/` and within 5 seconds understands what Patent Pulse does
- 4 personas (attorneys, IP teams, founders, investors) can self-identify
- All pricing tiers are visible without leaving the landing page
- "Get started free" CTA appears 3 times (hero, pricing, final CTA)
- "See pricing" CTA appears 2 times (hero, pricing teaser link)
- All AGENTS.md forbidden phrases return zero hits via grep
- Mobile renders cleanly at 375px width
- Lighthouse score: ≥ 90 on landing page (no JS-heavy interactivity)
- The same `BriefingPreview` component is reused in `/pricing` (DRY check)

---

## Open questions for implementation phase

None. All design decisions are locked. The writing-plans skill will detail the chunk-by-chunk implementation steps.
