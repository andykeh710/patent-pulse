# Invention Index 8 — Product Audit

**Date:** 2026-06-14
**Author:** Hermes Agent
**Purpose:** Screen-by-screen product walkthrough — analyze each surface against the three core questions: *What changed? Why should I care? What action should I take now?*

**Note:** This audit is based on source-code analysis, existing investigation reports, and the V3 end-of-phase audit. Dynamic walkthrough (screenshots, Lighthouse, keyboard nav) requires running the app locally which needs Docker. Those sections are marked SCREENSHOTS NEEDED.

---

## Screen 1: Landing Page (`/`)

**File:** `frontend/src/app/(marketing)/page.tsx`

### Job of the screen
Sell the value proposition and get users to sign up or browse pricing.

### Current state (from code)
- Marketing layout with `MarketingNav` (top nav)
- Hero section with CTA
- `BriefingPreview` component showing example intelligence cards
- Pricing CTA
- Links to: `/about`, `/pricing`, `/contact`, `/privacy`, `/terms`

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Conversion — get visitors to sign up |
| Who is it for? | First-time visitors, potential customers |
| What is the primary action? | Sign up / View pricing |
| What is the secondary action? | Browse public pages (company/theme/blog) |
| What data is most important? | Value proposition clarity, trust signals, social proof |
| What is currently overemphasized? | Unknown — needs visual inspection |
| What feels clunky? | Landing page was flagged in V3 audit as possibly not deployed (#30 in conflict state) |
| What feels broken? | Unknown — needs verification |
| What would make someone come back tomorrow? | N/A — landing page is one-time conversion, not repeat-use |

### SCREENSHOTS NEEDED
- [ ] Landing page at 1440px
- [ ] Landing page at 375px (mobile)
- [ ] CTA flow

### Revamp priorities
- Ensure landing page is deployed and functional
- Add specific use cases (competitive intel, portfolio monitoring, etc.)
- Add trust signals (patent count, data sources, data freshness)

---

## Screen 2: Login (`/login`)

**File:** `frontend/src/app/(auth)/login/page.tsx`

### Job of the screen
Get users authenticated via magic-link email.

### Current state
- Magic-link auth flow (email → link → verify → session cookie)
- Clean auth layout
- Works end-to-end (verified in V3 audit)

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Authentication |
| Who is it for? | All users |
| Primary action? | Enter email, submit |
| What feels clunky? | Magic link is good for first-time, but returning users have no "remember me" — every new session requires a fresh email |
| What would make someone come back? | Session persistence; "stay logged in" option |

### Revamp priorities
- Consider adding session persistence or "remember this device"
- Test email deliverability (DKIM/SPF/DMARC — Andy action in V3 checklist)

---

## Screen 3: Onboarding (`/onboarding`)

**File:** `frontend/src/app/(app)/onboarding/page.tsx`

### Job of the screen
Collect user persona to personalize the experience.

### Current state
- 4-step wizard: Role → Industry → Interests → Confirm
- Collects: persona (operator/investor/curious), industry, interests
- On completion: saves persona, redirects to today
- `StepRole`, `StepIndustry`, `StepInterests`, `StepConfirm` components

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Personalization setup |
| Who is it for? | First-time users |
| Primary action? | Select persona → select industry → write interests → confirm |
| What is good? | Clean wizard pattern, 4 steps, suggested companies/themes on confirm |
| What feels clunky? | Skippable? No. User must complete all 4 steps. |
| What is broken? | If user navigates away before completing, persona stays null (defaults to "curious") — noted in V3 audit as P2 issue |
| What would make someone come back? | N/A — one-time flow |

### Known issues
- **P2: No post-onboarding persona recovery.** If user skips onboarding, persona stays null and briefings are unpersonalized. V3 audit recommends adding a "Set your persona →" nudge on the Today page.
- Onboarding completion marks `user.onboarding_completed = True` but doesn't verify activation.

### Suggested activation definition
```
User follows at least 3 entities/themes
User saves at least 1 search
User opens at least 1 patent detail
User reaches a personalized Today view
```

### Revamp priorities
- Make onboarding skippable with a "Set up later" option
- Add post-skip persona nudge on Today page
- Reduce to 2-3 steps if possible (industry + interests; role is less actionable)

---

## Screen 4: Today (`/today`)

**File:** `frontend/src/app/(app)/today/page.tsx` (606 lines)

### Job of the screen
The daily intelligence command center — the reason users come back.

### Current state
- `FreshnessBanner` — shows data freshness
- `FilingTrendHighlight` — trending CPC categories from `useHotTrends`
- `ExpiringOppHighlight` — expiring opportunities from `useOpportunityList`
- `NotablePatentHighlight` — notable patents
- `CompanyMoveHighlight` — assignee movement
- `PriorityWatchSection` — user's followed items
- `StarterTopics` — topic suggestions for new users
- `SourceAttribution` — data source footer
- Briefing section via `todayApi`
- **Tour** component for new users

### Deep analysis from code

#### Strength: The Today page tries hard
The page loads data from 7+ SWR hooks (`useOpportunityList`, `useHotTrends`, `usePriorityWatch`, `usePatentStats`, `useSuppliers`, `useThemes`, `useWatchlist`, `todayApi`). It renders multiple highlight cards in a card-grid layout. Each card has a type badge, a title linking to the detail page, and supporting stats.

#### Weakness: Cards don't answer "why should I care?"
Looking at the `FilingTrendHighlight` component:
```tsx
{data.trend_label}
{data.count_4w} patents (4wk) · z-score {data.z_score}
Top: {data.top_assignees.join(", ")}
```
This shows raw data (count, z-score, top assignees) but doesn't explain:
- Why is this trend important?
- Is this good or bad for the user?
- What action should the user take?

#### Weakness: Empty state is honest but not compelling
```tsx
No high-value patents expiring within 90 days yet.
As v3 scoring reaches more patents, this card will populate.
Browse all expiry data →
```
This is honest about data limitations but reads like "product not ready yet." Better: explain what expiry opportunities mean and when to expect them.

#### Weakness: Too many cards, not enough narrative
The page renders up to 8 different card types. Each is a small card with a badge and a link. There's no overarching narrative — no "here's what's important today" synthesis. The user has to read and interpret every card individually.

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Daily intelligence briefing |
| Who is it for? | Returning professional users |
| Primary action? | Scan highlights, click into details |
| What data is most important? | Changes since last visit, personalized signals, actionable opportunities |
| What is currently overemphasized? | Raw stats (z-scores, counts) without interpretation |
| What feels clunky? | Multiple independent SWR fetches; cards render at different times causing layout shift |
| What feels broken? | Cards can show "null" if data hasn't loaded; no unified loading state |
| **What would make someone come back tomorrow?** | Currently: unclear. The page shows data but doesn't synthesize it into a compelling "this is what you need to know" narrative. |

### Critical gap
The three questions the revamp plan demands are not being answered:
1. **What changed?** — No "since your last visit" tracking
2. **Why should I care?** — Raw stats without interpretation
3. **What action should I take now?** — Links exist but no prioritized CTAs

### Revamp priorities (HIGH)
- Add "Since your last visit" change tracking
- Add a Daily Brief summary card (plain-English synthesis at the top)
- Ensure every card has: title, why-it-matters, primary action
- Reduce card count; promote 3-5 most important signals
- Unified loading skeleton (not per-card spinners)
- Add "Set your persona" nudge if persona is null

---

## Screen 5: Search (`/search`)

**File:** `frontend/src/app/(app)/search/page.tsx` (256 lines)

### Job of the screen
Let users find relevant patents by keyword or natural-language query.

### Current state
- Search input with rotating NL placeholder examples
- Three search modes: hybrid, semantic, fulltext
- Results displayed as `PatentCard` grid
- URL-synced search state (query, mode, page)
- `PatentCardSkeleton` for loading
- `FreshnessBanner` + `SourceAttribution`

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Patent discovery |
| Who is it for? | All users |
| Primary action? | Enter query, browse results, click into patents |
| Secondary action? | Toggle search mode |
| What is good? | Hybrid/semantic/fulltext mode toggle, NL placeholders, URL state sync |
| What is missing? | No saved searches, no filters (assignee, date range, CPC), no sort options, no result count display |
| What feels clunky? | Mode toggle below the search bar is easy to miss |

### Missing features
- **Saved searches** — users can't save a search for later
- **Filters** — no assignee, date range, CPC, legal status filters
- **Sort options** — no relevance/recency/opportunity-score sorting
- **No-results recovery** — what happens when 0 results? Code shows: no special handling beyond `!hasResults`

### Revamp priorities (MEDIUM-HIGH)
- Add filters sidebar/chips (assignee, date range, CPC, status)
- Add sort options (relevance, recency, opportunity score)
- Add saved searches
- Add no-results recovery (suggest broader terms or related searches)
- Show result count prominently
- Consider quick-preview drawer for search results

---

## Screen 6: Patents List (`/patents`)

**File:** `frontend/src/app/(app)/patents/page.tsx`

### Job of the screen
Browse, filter, and discover patents.

### Current state
- Uses `usePatents` hook with filter/sort params
- `PatentCard` display with title, assignee, score badges, tags
- Pagination

### Analysis
The Patents list page shares concerns with Search — missing filters, no saved views, no bulk actions. It currently feels like a raw database view rather than an intelligence exploration tool.

### Revamp priorities (MEDIUM)
- Add the same filters as Search
- Add compact/expanded view toggle
- Add save/follow on each card
- Quick preview drawer

---

## Screen 7: Patent Detail (`/patents/[id]`)

**File:** `frontend/src/app/(app)/patents/[id]/page.tsx` (935 lines)

### Job of the screen
Turn one patent into a clear, actionable intelligence object.

### Current state — EXTREMELY feature-rich
The patent detail page is the most developed surface in the app. It loads:
1. `AISummaryPanel` — AI-generated plain-English summary
2. `ScoreBadge` + `OpportunityScoreBadge` — dual scoring
3. `TagsPanel` — technology tags
4. `LegalConfidenceBadge` — legal status confidence
5. `RiskFlagsBadge` — family risk, expiry risk
6. `WhyNowPanel` — why-now narrative
7. `LinkedInPostPanel` — content generation
8. `UsageSignalsPanel` — commercial usage signals
9. `OpportunityNarrativePanel` — opportunity narrative
10. `TrendSnapshotPanel` — filing trend snapshot
11. `AssigneeIntelligencePanel` — assignee analysis
12. `ClaimsPanel` — patent claims
13. `ExternalPatentLinks` — external patent office links
14. `PatentFiguresPanel` — patent figures/images
15. `PatentDetailTabs` — tab navigation
16. `DataCompletenessPanel` — shows which fields are populated
17. Watchlist save/unsave
18. "Ask AI" button for chatbot
19. Similar patents section
20. `FreshnessBanner` + `SourceAttribution`

### Deep analysis

#### Strength: Depth of intelligence
The patent detail page has genuinely impressive coverage. It doesn't just show metadata — it has AI-generated narratives (summary, why-now, opportunity, trends), commercial usage signals, assignee intelligence, and content generation tools. The data completeness panel is a thoughtful transparency feature.

#### Critical weakness: Intelligence is buried
The page is 935 lines of TypeScript. The top of the page shows: title, assignee, dates, badges, and then immediately launches into panels. The most valuable content (why-now narrative, opportunity score explanation) may be scrolled out of view. The page doesn't prioritize what matters most.

#### Weakness: No executive summary
Despite having AI-generated summaries, why-now narratives, and opportunity scores, there's no single "executive summary" section that answers: *What is this patent? Why does it matter? What should I do with this information?*

#### Weakness: Data completeness exposes gaps visually
The data completeness panel shows `available/unavailable` status per field. While transparent, it also visually highlights that many patents are missing AI-generated content. For a user, seeing "Core: 2/2, Content: 2/2, Intelligence: 0/4" undermines confidence.

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Deep patent intelligence |
| Who is it for? | Power users, researchers, competitive analysts |
| Primary action? | Read about the patent |
| Secondary action? | Save, follow, export, ask AI, generate content |
| What data is most important? | Summary, commercial relevance, claims, expiry, opportunity |
| What is currently overemphasized? | Data completeness panel draws attention to gaps |
| **What would make someone come back?** | Follow/save creates a return path. But the page doesn't suggest "what to look at next." |

### Revamp priorities (HIGH)
- Add **executive summary section** at TOP: title, assignee, status, 2-3 sentence AI summary, why-it-matters, primary CTA
- Move data completeness to a collapsed footer (not prominent)
- Restructure into logical sections above the fold: Executive Summary → Commercial Relevance → Technical Details
- Add "Related patents" and "Next to investigate" CTAs at bottom
- Bold primary CTA: Save/Follow, secondary: Export/Ask AI

---

## Screen 8: Companies / Assignees (`/companies`)

**File:** `frontend/src/app/(app)/companies/page.tsx` (329 lines)

### Job of the screen
Show what companies are inventing, portfolio strength, and competitive intelligence.

### Current state — KNOWN ISSUE
- Summary cards: Total Companies, Company Patents, High-Score Companies, Avg Patents/Company
- Data Coverage panels: Country Coverage, Entity Type Coverage
- Company Rankings table with pagination
- Country filter dropdown
- Sort options: Company Score, Patent Count, Name
- Supplier map visualization
- **KNOWN ISSUE:** Country Coverage shows "0 of X" — all companies show "Metadata pending"

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Company/assignee intelligence |
| Who is it for? | Competitive analysts, investors |
| Primary action? | Browse companies, filter, click into detail |
| What is broken? | **Country and entity-type coverage shows 0%.** All companies display "Metadata pending." This is a P0 trust issue — the page looks broken even though the underlying data (16,723 companies, 50,293 patent links) is real. |
| What feels clunky? | "0 of 16,723 companies" coverage bar is actively misleading |
| What would make someone come back? | Follow company button creates a return path |

### Root cause (from investigation)

The `supplier_normalized` table has 16,723 rows with company names but the `country` and `entity_type` columns are never populated by the current ingestion pipeline. The `SupplierNormalized` model exists but the enrichment backfill never ran or failed silently. `MAX(a.country)` in the SQL query returns NULL for all rows.

### Revamp priorities (P0 — HIGHEST)
- **Fix country/entity_type backfill** — this is the #1 trust-breaking issue in the app
- Add "What changed recently" section to company pages
- Add follow/watch company button
- Add expiry exposure metrics per company
- Improve empty state: explain WHY data is missing, not just show "0 of 0"

---

## Screen 9: Company Detail (`/companies/[name]`)

**File:** `frontend/src/app/(app)/companies/[name]/page.tsx`

### Job of the screen
Deep dive into a single company's patent portfolio.

### Current state
- Company profile with stats
- Patent list filtered by assignee
- Links to public SEO version (`/c/[name]`)

### Revamp priorities (MEDIUM)
- Add portfolio summary (tech concentration, filing trends)
- Add top inventors section
- Add citation influence metrics
- Add expiry exposure (which patents are expiring soon)
- Add competitor comparison
- Add follow/alert actions

---

## Screen 10: Expiry Radar (`/expiry`)

**File:** `frontend/src/app/(app)/expiry/page.tsx` (600 lines)

### Job of the screen
Present expiring patents as commercial opportunities.

### Current state
- `ExpirySummaryCards` — summary bar (total, expiring_soon, expired, unknown)
- `ExpiryRadarSection` — timeline of expiring patents
- Cliff clusters from `useCliffs`
- Filters: time window, confidence, active family risk
- Each card shows: title, assignee, expiry date, days until, status badge, confidence, family risk flag, opportunity score, usage signal count

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Expiry opportunity discovery |
| Who is it for? | Licensing professionals, competitive analysts |
| Primary action? | Browse expiring patents, filter, click into detail |
| What is good? | Rich card data: opportunity score, family risk, usage signals, confidence levels |
| What is missing? | Why-it-matters explanation per patent |
| What would make someone come back? | Alerts on expiring patents, saved expiry watchlist |

### Revamp priorities (MEDIUM-HIGH)
- Add commercial relevance explanation per card ("Why this expiry may matter")
- Add save/export per card
- Add alert creation ("Alert me when this expires")
- Add company/theme filters
- Empty state should explain why no data exists, not just show empty

---

## Screen 11: Themes (`/themes`, `/themes/[id]`)

**File:** `frontend/src/app/(app)/themes/page.tsx`, `themes/[id]/page.tsx`

### Job of the screen
Explore technology themes (CPC categories grouped into human-readable topics).

### Current state
- Theme list with patent counts
- Theme detail with patent list
- Public SEO page at `/t/[slug]`

### Analysis
Themes are a good organizational layer between raw CPC codes and user interests. Currently they're primarily a classification system — they need to become a monitoring surface.

### Revamp priorities (LOW-MEDIUM)
- Add "Recent activity" per theme
- Add follow/watch theme button
- Add theme trend visualizations

---

## Screen 12: Trends (`/trends`, `/trends/[surface]/[key]`)

**File:** `frontend/src/app/(app)/trends/page.tsx`

### Job of the screen
Show filing momentum and trend changes over time.

### Current state
- Trend list with surface/key drilldown
- Uses `useTrends` / `useCliffs` hooks
- Z-scores, 4-week counts, top assignees

### Revamp priorities (LOW)
- Add trend narratives (already have `trend_narrative.py` in backend)
- Link trends to related patents on Today page
- Add trend-to-expiry linkage

---

## Screen 13: Opportunity (`/opportunity`)

**File:** `frontend/src/app/(app)/opportunity/page.tsx`

### Job of the screen
Discover high-opportunity patents.

### Current state
- Filtered list of patents sorted by opportunity score
- `_filters.tsx` for filter components

### Revamp priorities (MEDIUM)
- Add opportunity narrative per card
- Add save/export CTAs
- Link to expiry radar

---

## Screen 14: Watchlist (`/watchlist`)

**File:** `frontend/src/app/(app)/watchlist/page.tsx` (167 lines)

### Job of the screen
User's saved/followed patents.

### Current state
- Paginated grid of saved patents
- Remove button per card
- Empty state: bookmark icon + "Your watchlist is empty" + suggestion copy
- Loading state: 6 skeleton cards

### Analysis

| Question | Answer |
|----------|--------|
| What is this screen for? | Personal workspace |
| Who is it for? | Returning users |
| Primary action? | Review saved patents, click into detail |
| What is good? | Clean empty state, skeleton loading |
| What is missing? | No notes, no collections/folders, no recently viewed, no followed companies/themes |

### Revamp priorities (MEDIUM-HIGH)
This is central to retention. The current implementation only tracks saved patents. It should expand to:
- Followed companies
- Followed inventors
- Followed themes
- Saved searches
- Recently viewed items
- Notes
- Alert subscriptions

---

## Screen 15: Chat (`/chat`)

**File:** `frontend/src/app/(app)/chat/page.tsx`

### Job of the screen
AI-powered Q&A about patents, companies, trends, and opportunities.

### Current state (from V3 audit)
- SSE streaming chat with Claude
- Tool calls: search_patents, open_patent, compare_companies
- Citation extraction with soft enforcement
- Redis conversation memory (30-min TTL, 10-turn cap)
- Quota enforcement (Free: 5/day, Basic: 50/day)
- "Ask AI" deep-link from patent detail pages
- Usage warning banner at 80% quota

### Known issues
- Chat memory TTL is 30 min — returning after 31 min gets blank slate with no notice
- `_check_chat_quota_stub` dead code still in chat.py
- Patent-detail chat drawer deferred to Phase 3.5
- No news retrieval integration (deferred)

### Revamp priorities (MEDIUM)
- Add "Welcome back, continue previous conversation?" prompt
- Remove dead stub code
- Add chat cost tracking
- Consider embedding relevant patent links in chat responses

---

## Screen 16: Account / Billing / Admin

### Account (`/account`)
- User settings, delete account
- Email preferences
- Webhook alert configs (Lifetime+)
- API key management

### Billing (`/account/billing`)
- Stripe integration (currently TEST mode)
- Usage bars with limits
- Tier badge
- Pricing table
- Upgrade flow with success/cancelled toasts
- `UsageWarningBanner` at 80% threshold

### Admin (`/admin`, `/admin/ai-runs`, `/admin/data-health`)
- Admin-only endpoints
- AI run monitoring
- Data health dashboards
- Trigger endpoints (needs `require_admin` guard — PRE-01)

### Revamp priorities (LOW)
- Stripe LIVE flip (Andy action)
- Add `require_admin` to trigger endpoints
- Build D30 retention dashboard
- Build chat cost tracking

---

## Cross-Cutting Issues

### 1. Empty States Are Mixed Quality

| Surface | Empty State | Quality |
|---------|-------------|---------|
| Watchlist | Bookmark icon + "Your watchlist is empty. Save patents as you browse to collect them here." | ✅ Good — explains what to do |
| Companies coverage | "0 of 16,723 companies" | ❌ Bad — looks broken, no explanation |
| Expiry (When null) | "No high-value patents expiring... As v3 scoring reaches more patents, this card will populate." | ⚠️ OK — honest but reads like "product not ready" |
| Search no-results | No special handling visible in code | ❌ Missing — needs recovery suggestions |
| Today (when cards null) | Each card handles null individually | ⚠️ Mixed — some cards show "no data yet," others show nothing |

### 2. Loading States

- Some surfaces use `Skeleton`, others use inline spinners
- Today page has no unified loading state — 7+ SWR fetches cause cascading layout shifts
- Patent detail page has loading but the massive component count means many panels load independently

### 3. "Why Should I Care?" Is the Missing Layer

The app has rich data. It has AI-generated narratives. But across most surfaces, the connection between "here's data" and "here's why it matters to you" is weak or absent. The insight card pattern from the revamp plan (type, title, summary, why_it_matters, evidence, confidence, primary_action) doesn't exist as a reusable component.

### 4. Follow/Save Infrastructure Is Limited

- Watchlist exists but only for patents
- No company follow (backend `follow_company.py` exists but frontend usage unclear)
- No theme follow
- No inventor follow
- No saved searches

### 5. No "Since Your Last Visit" Tracking

The app has no mechanism to show what changed since the user's last session. This is the #1 retention feature — without it, the Today page is just "here's what's in the database" rather than "here's what's new for you."

---

## User Journey Maps

### Journey 1: First-Time User

```
Landing → "What is this?" → Sign up → Magic link email → Verify → 
Onboarding (4 steps) → Today page → "What do I do?" → Search → 
Patent detail → Follow a patent → Return?
```

**Friction points:**
- Onboarding is mandatory (4 steps, can't skip)
- Today page doesn't guide the first action
- No "getting started" tour content (Tour component exists but unknown if effective)

### Journey 2: Returning Professional User

```
Login (magic link again) → Today → "What changed?" → (no clear answer) →
Browse patents/companies → Find something interesting → Save → Leave
```

**Friction points:**
- Must re-authenticate every session (magic link)
- No "what changed" on Today
- Can't follow companies/themes from main surfaces
- No alert/notification system to pull user back

### Journey 3: Power User

```
Login → Today (scan) → Search (filtered, saved searches) → 
Patent detail (deep analysis) → Chat (ask follow-up questions) → 
Export/save → Configure alerts → Return when notified
```

**Friction points:**
- No saved searches
- No alerts on followed entities (alert webhooks exist but are Lifetime+-only)
- Chat quota limits (5/day on Free) feel restrictive for power users
- No export workflow for findings

---

## Priority Summary

| Priority | Screen | Issue | User Impact |
|----------|--------|-------|-------------|
| **P0** | Companies | "0 of 0" coverage bars | Looks broken, kills trust |
| **P0** | Today | No "what changed" synthesis | No reason to return |
| **P1** | Patent Detail | Intelligence buried, no executive summary | Value not visible without scrolling |
| **P1** | All | Why-it-matters layer missing everywhere | Data without interpretation |
| **P1** | Today | Persona null after onboarding skip | Unpersonalized experience |
| **P2** | Today | Cascading SWR loads, no unified skeleton | Layout shift, feels janky |
| **P2** | Search | No filters, saved searches, no-results recovery | Exploration friction |
| **P2** | Watchlist | Only patents, no companies/themes/searches | Limited retention loop |
| **P2** | Companies Detail | No portfolio movement, expiry exposure, competitor comparison | Shallow intelligence |
| **P3** | Expiry | No why-it-matters per card, no alerts | Missed conversion opportunity |
| **P3** | Chat | 30-min memory TTL, no continuation prompt | Disrupted research flow |
| **P3** | Blog | Placeholder patent IDs | Broken links if published |
