# Landing Page — Implementation Plan

> **For Hermes:** Execute chunk by chunk per standard operating rules.
> Stop at each verification block. User commits. Do not chain chunks.
> The writing-plans skill's `references/batched-execution.md` applies
> for identically-structured components within a single chunk.

**Goal:** Replace the bare `/ → /today` redirect with a polished
marketing landing page (10 sections) + `/pricing` + 3 legal skeleton
pages, using Next.js route groups.

**Architecture:** Route groups `(marketing)`, `(app)`, `(auth)` split
the layout. Marketing pages use a slim top nav (no sidebar). App pages
keep the existing sidebar. Auth pages keep centered layout. A
middleware reads the auth cookie at `/` and redirects authenticated
users to `/today`.

**Tech Stack:** Next.js 15 (App Router), Tailwind CSS, Server
Components by default (only `BriefingPreview` and mobile hamburger
need `"use client"`).

---

## Pre-existing structure (M0 — survey before touching anything)

### Files to understand before M1

| File | What it does |
|---|---|
| `frontend/src/app/layout.tsx` | Root: imports AuthProvider + NavSidebar, wraps everything in flex with sidebar |
| `frontend/src/app/page.tsx` | Current: `redirect("/today")` |
| `frontend/src/app/NavSidebar.tsx` | 176-line client component, sidebar with 10 nav items + admin + auth state |
| `frontend/src/app/about/page.tsx` | 199-line limitations page — will become `(marketing)/about/page.tsx` |
| `frontend/src/app/login/page.tsx` | Login form — will move to `(auth)/login/page.tsx` |
| `frontend/src/app/login/verify/page.tsx` | Magic-link verify — will move to `(auth)/login/verify/page.tsx` |
| `frontend/src/app/unsubscribed/page.tsx` | Unsubscribe confirmation — will move to `(auth)/unsubscribed/page.tsx` |
| `frontend/src/lib/AuthContext.tsx` | Client-side auth via `authApi.me()`, cookie-based (no cookie name exposed — check api.ts) |
| `frontend/src/lib/api.ts` | API client — find the cookie name for auth_session |
| `frontend/src/app/globals.css` | Tailwind imports + system font stack + dark mode vars |
| `frontend/tailwind.config.ts` | Brand colors: `primary-600` = `#0284c7` (sky-600) |
| `frontend/public/` | Check for existing favicon, robots.txt |

### Check before M1
- Read `frontend/src/lib/api.ts` to find the cookie name used for auth session.
- Run `ls frontend/public/` to see what static assets exist.
- Confirm no middleware file exists at `frontend/src/middleware.ts`.

---

## Chunk M1 — Route group restructure

**LOC:** ~0 new code, all `git mv` operations.

### Steps

1. Create directory structure:
   ```
   frontend/src/app/(marketing)/
   frontend/src/app/(app)/
   frontend/src/app/(auth)/
   frontend/src/app/(auth)/login/
   frontend/src/app/(auth)/login/verify/
   ```

2. Move files via `git mv` (run these in terminal):
   ```
   # App pages → (app)
   git mv frontend/src/app/today frontend/src/app/\(app\)/today
   git mv frontend/src/app/expiry frontend/src/app/\(app\)/expiry
   git mv frontend/src/app/opportunity frontend/src/app/\(app\)/opportunity
   git mv frontend/src/app/trends frontend/src/app/\(app\)/trends
   git mv frontend/src/app/patents frontend/src/app/\(app\)/patents
   git mv frontend/src/app/search frontend/src/app/\(app\)/search
   git mv frontend/src/app/themes frontend/src/app/\(app\)/themes
   git mv frontend/src/app/companies frontend/src/app/\(app\)/companies
   git mv frontend/src/app/watchlist frontend/src/app/\(app\)/watchlist
   git mv frontend/src/app/account frontend/src/app/\(app\)/account
   git mv frontend/src/app/admin frontend/src/app/\(app\)/admin
   git mv frontend/src/app/dashboard frontend/src/app/\(app\)/dashboard
   git mv frontend/src/app/loading.tsx frontend/src/app/\(app\)/loading.tsx
   git mv frontend/src/app/error.tsx frontend/src/app/\(app\)/error.tsx
   # Also move NavSidebar since it belongs to the app group
   git mv frontend/src/app/NavSidebar.tsx frontend/src/app/\(app\)/NavSidebar.tsx

   # Auth pages → (auth)
   git mv frontend/src/app/login/page.tsx frontend/src/app/\(auth\)/login/page.tsx
   git mv frontend/src/app/login/verify/page.tsx frontend/src/app/\(auth\)/login/verify/page.tsx
   git mv frontend/src/app/unsubscribed/page.tsx frontend/src/app/\(auth\)/unsubscribed/page.tsx

   # Marketing pages → (marketing)
   git mv frontend/src/app/about/page.tsx frontend/src/app/\(marketing\)/about/page.tsx
   ```

3. Remove now-empty directories:
   ```
   rmdir frontend/src/app/login/verify
   rmdir frontend/src/app/login
   rmdir frontend/src/app/about
   ```

4. The `/` page (`page.tsx`) stays at the root of `src/app/` — it will be replaced in M4.

5. Run `npm run build` to confirm no import path breakages.

**Verification:**
- `npm run build` passes with zero errors.
- `frontend/src/app/(app)/today/page.tsx` exists and imports NavSidebar from `../(app)/NavSidebar` or a path that resolves correctly.
- `frontend/src/app/(auth)/login/page.tsx` exists.
- `frontend/src/app/(marketing)/about/page.tsx` exists.

---

## Chunk M2 — Route-group layouts

**LOC:** ~80

### Files to create/modify

| File | Action |
|---|---|
| `src/app/layout.tsx` | Slim down — remove NavSidebar import and sidebar flex layout. Keep only `<html>`, `<body>`, `<AuthProvider>`, global CSS link, and `{children}` |
| `src/app/(marketing)/layout.tsx` | New — top nav header + `{children}` in full-width container |
| `src/app/(app)/layout.tsx` | New — wraps existing sidebar layout pattern (NavSidebar + `<main className="flex-1 ml-64 p-8">`) |
| `src/app/(auth)/layout.tsx` | New — centered, no-nav layout |
| `src/app/(app)/NavSidebar.tsx` | Update import paths for any relative imports that broke in M1 |

### `src/app/layout.tsx` — slim root layout

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/AuthContext";

export const metadata: Metadata = {
  title: "Patent Pulse",
  description: "Patent intelligence and summarization system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-white min-h-screen font-[system-ui,-apple-system,BlinkMacSystemFont,'Segoe_UI',Roboto,'Helvetica_Neue',Arial,sans-serif]">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

### `src/app/(app)/layout.tsx` — app layout (sidebar + content)

```tsx
import { NavSidebar } from "./NavSidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <NavSidebar />
      <main className="flex-1 ml-64 p-8">{children}</main>
    </div>
  );
}
```

### `src/app/(marketing)/layout.tsx` — marketing layout (top nav)

```tsx
import { MarketingNav } from "./MarketingNav";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <MarketingNav />
      <main className="pt-16">{children}</main>
    </>
  );
}
```

### `src/app/(marketing)/MarketingNav.tsx` — top nav bar

```tsx
"use client";

import Link from "next/link";
import { useState } from "react";

export function MarketingNav() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="text-xl font-bold text-primary-700">
            Patent Pulse
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="/pricing" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              Pricing
            </Link>
            <Link href="/about" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              About
            </Link>
            <Link href="/login" className="text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors">
              Sign in
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 text-gray-600"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {open
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden pb-4 border-t border-gray-100">
            <Link href="/pricing" className="block py-2 text-sm text-gray-600" onClick={() => setOpen(false)}>
              Pricing
            </Link>
            <Link href="/about" className="block py-2 text-sm text-gray-600" onClick={() => setOpen(false)}>
              About
            </Link>
            <Link href="/login" className="block py-2 text-sm text-primary-600 font-medium" onClick={() => setOpen(false)}>
              Sign in
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
```

### `src/app/(auth)/layout.tsx` — auth layout (centered, no nav)

```tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        {children}
      </div>
    </div>
  );
}
```

**Verification:**
- `npm run build` passes.
- Navigate to `/today` in browser → sidebar renders.
- Navigate to `/login` → centered narrow layout, no sidebar.
- Navigate to `/about` → top nav renders, no sidebar.
- Navigate to `/` → still redirects to `/today` (M4 will change this).

---

## Chunk M3 — Auth-aware middleware on `/`

**LOC:** ~20

### New file: `frontend/src/middleware.ts`

The cookie name must be confirmed from `frontend/src/lib/api.ts` before writing middleware. Let's check:

```ts
// From api.ts — the cookie name for auth session
// Typically "auth_session" but verify by reading the file
```

Assuming the cookie name is `auth_session` (confirm in M3):

```ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "auth_session";  // confirm from api.ts

export function middleware(request: NextRequest) {
  // Only act on root path
  if (request.nextUrl.pathname !== "/") {
    return NextResponse.next();
  }

  const sessionCookie = request.cookies.get(AUTH_COOKIE);

  if (sessionCookie?.value) {
    // Cookie exists — redirect authenticated users to /today
    return NextResponse.redirect(new URL("/today", request.url));
  }

  // No cookie — serve the landing page (do nothing, Next.js handles the route)
  return NextResponse.next();
}

export const config = {
  matcher: "/",
};
```

**Verification:**
- Clear cookies → visit `/` → should show landing page (after M4).
- Set auth_session cookie → visit `/` → redirects to `/today`.
- Visit `/pricing` → never redirects (matcher is `"/"` only).

---

## Chunk M4 — Landing page `(marketing)/page.tsx`

**LOC:** ~350

This is the largest chunk. It creates the full landing page with all 10 sections.

### `src/app/(marketing)/page.tsx` — Server Component (NOT "use client")

The page is a plain server component rendering 10 sections. Only `BriefingPreview` and the mobile hamburger in `MarketingNav` (already built in M2) need `"use client"`.

```tsx
import Link from "next/link";
import { BriefingPreview } from "./BriefingPreview";

export default function LandingPage() {
  return (
    <>
      {/* ─── 1. Hero — split layout ─── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left: copy */}
          <div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 leading-tight tracking-tight">
              Patent intelligence with the receipts.
            </h1>
            <p className="mt-6 text-lg text-gray-600 leading-relaxed max-w-xl">
              Track expiry, usage signals, and filing trends across USPTO, EPO,
              and WIPO data — every claim labeled with confidence, every source
              linked back. Subscribe to your topics for weekly briefings and
              instant alerts.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <Link
                href="/login"
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-primary-600 text-white font-semibold hover:bg-primary-700 transition-colors"
              >
                Get started free
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg border border-gray-300 text-gray-700 font-semibold hover:bg-gray-50 transition-colors"
              >
                See pricing
              </Link>
            </div>
          </div>

          {/* Right: weekly briefing preview card */}
          <div className="hidden md:flex justify-center">
            <BriefingPreview />
          </div>
        </div>
      </section>

      {/* ─── 2. Data strip ─── */}
      <section className="border-y border-gray-200 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-gray-500 text-center flex flex-wrap justify-center gap-x-6 gap-y-2">
            <span>54,903 patents</span>
            <span className="text-gray-300">·</span>
            <span>USPTO</span>
            <span className="text-gray-300">·</span>
            <span>EPO</span>
            <span className="text-gray-300">·</span>
            <span>WIPO</span>
            <span className="text-gray-300">·</span>
            <span>Updated weekly</span>
            <span className="text-gray-300">·</span>
            <span>Evidence-backed</span>
          </p>
        </div>
      </section>

      {/* ─── 3. Value Props — 4 cards, 2×2 grid ─── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="grid sm:grid-cols-2 gap-8">
          {/* Card 1 — Expiry Intelligence */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            {/* Visual: confidence label pill row */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">active_estimated</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">expiring_soon</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">lapsed_possible</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">lapsed_confirmed</span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Expiry intelligence, calibrated.</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Estimated expiry dates with explicit confidence labels — not raw guesses.
              Active family members in other jurisdictions surfaced when relevant.
              Every estimate links to the official register for verification.
            </p>
          </div>

          {/* Card 2 — Usage Signals */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            {/* Visual: tier badges + self-citation chip */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800">strong</span>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">medium</span>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-600">weak</span>
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-300">
                ⚠ self-citation risk
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Usage signals, evidence-backed.</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              See how patent ideas appear in newer art — with a tier
              (strong/medium/weak) on every piece of evidence and a source link
              beneath. No &ldquo;this patent is used by Company X&rdquo; claims.
              Only patterns you can verify.
            </p>
          </div>

          {/* Card 3 — Trend Narratives */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            {/* Visual: AI badge + narrative snippet */}
            <div className="mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                </svg>
                AI-generated · Claude Sonnet
              </span>
              <p className="mt-3 text-sm text-gray-500 italic leading-relaxed line-clamp-2">
                &ldquo;Filing activity in quantum-resistant cryptography surged 42% over the
                trailing 12 months, led by assignees in the US and Japan...&rdquo;
              </p>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Trend narratives, in plain English.</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Filing surges and assignee movement explained by Claude Sonnet —
              the model that follows structured-JSON instructions reliably.
              Every narrative cites the underlying patents. Refreshed as new
              filings drop.
            </p>
          </div>

          {/* Card 4 — Topics & Alerts */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            {/* Visual: subscription card mock */}
            <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs font-mono text-gray-600 space-y-1">
              <div>Topic: <span className="text-primary-700 font-semibold">G06F</span></div>
              <div>Mode: <span className="text-primary-700">weekly_digest + instant_alert</span></div>
              <div>Threshold: <span className="text-primary-700">≥ 60</span></div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Your topics. Briefed weekly. Alerted instantly.</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Subscribe to topics by CPC class, keyword, or assignee — with
              optional opportunity-score thresholds. Get instant alerts on
              high-priority matches and a Sonnet-written briefing every Sunday
              morning.
            </p>
          </div>
        </div>
      </section>

      {/* ─── 4. Use Cases — 3 personas ─── */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
            Who it&rsquo;s for
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Attorneys */}
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-3">For patent attorneys & law firms</h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Surveil portfolios with confidence-labeled expiry estimates.
                Build evidence packets with source citations linked to official
                registers. Hand clients reports they can verify.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> expiry windows · active family risk · cite-graph signals
              </p>
            </div>

            {/* Corporate IP */}
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-3">For corporate IP teams</h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Monitor your CPC areas for filing surges, family expansions, and
                expiry opportunities. Track usage signals showing how your prior
                art shows up in newer filings — with evidence tiers, not claims.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> competitor filings · expiry windows · usage signals
              </p>
            </div>

            {/* Founders */}
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-3">For founders & investors</h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Find ideas approaching estimated expiry in your thesis areas —
                with confidence labels so you know what&rsquo;s open vs.
                uncertain. Subscribe to topics tied to your thesis. Verify before
                you commit.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> expiring opportunities · whitespace topics · weekly briefings
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 5. How It Works — 3 steps ─── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
          How it works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="relative text-center">
            <div className="w-12 h-12 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-4">1</div>
            <h3 className="font-semibold text-gray-900 mb-2">Pick your topics</h3>
            <p className="text-sm text-gray-600">
              Subscribe by CPC class, keyword, assignee, or opportunity-score threshold.
            </p>
          </div>
          <div className="relative text-center">
            <div className="w-12 h-12 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-4">2</div>
            <h3 className="font-semibold text-gray-900 mb-2">Get briefings + alerts</h3>
            <p className="text-sm text-gray-600">
              Sunday morning weekly digest. Instant alerts on high-priority matches.
            </p>
          </div>
          <div className="relative text-center">
            <div className="w-12 h-12 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-4">3</div>
            <h3 className="font-semibold text-gray-900 mb-2">Drill into patents</h3>
            <p className="text-sm text-gray-600">
              Full intelligence per patent — expiry, family, usage signals, AI narratives, source links.
            </p>
          </div>
        </div>
      </section>

      {/* ─── 6. Pricing Teaser — 4 cards ─── */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4">Pricing</h2>
            <p className="text-gray-600 text-lg">Start free. Upgrade when you need more.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Free */}
            <PricingCard
              name="Free"
              price="$0"
              features={["1 topic", "5 alerts/week", "Weekly digest"]}
              cta="Get started"
              href="/login"
            />
            {/* Basic */}
            <PricingCard
              name="Basic"
              price="$8"
              period="/year"
              features={["Unlimited topics", "Unlimited alerts", "CSV export", "Weekly digest"]}
              cta="Choose Basic"
              href="/login"
            />
            {/* Lifetime — highlighted */}
            <PricingCard
              name="Lifetime"
              price="$108"
              period=" once"
              features={["Unlimited topics", "Unlimited alerts", "CSV + PDF export", "Weekly digest"]}
              cta="Choose Lifetime"
              href="/login"
              highlighted={true}
              badge="Best value"
            />
            {/* Enterprise */}
            <PricingCard
              name="Enterprise"
              price="$1,000"
              period="/year"
              features={["Everything in Lifetime", "API access (300/min)", "Admin tools", "Priority support"]}
              cta="Choose Enterprise"
              href="/login"
            />
          </div>
          <div className="text-center mt-8">
            <Link href="/pricing" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
              See full feature comparison →
            </Link>
          </div>
        </div>
      </section>

      {/* ─── 7. Trust Block ─── */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-xl font-bold text-gray-900 text-center mb-6">
          We show our work.
        </h2>
        <p className="text-gray-600 leading-relaxed text-center mb-8">
          Patent Pulse calibrates uncertainty. We label every estimate.
          We cite every source. We don&rsquo;t claim freedom-to-operate, we
          don&rsquo;t invent market data, and we tell you when our confidence
          is low.
        </p>
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-gray-500 mb-6">
          <span>Data: USPTO + EPO + WIPO</span>
          <span className="text-gray-300">·</span>
          <span>Updated weekly</span>
          <span className="text-gray-300">·</span>
          <span>AI: Claude Sonnet narratives</span>
          <span className="text-gray-300">·</span>
          <span>Not legal advice</span>
        </div>
        <div className="text-center">
          <Link href="/about" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            Read the limitations →
          </Link>
        </div>
      </section>

      {/* ─── 8. Final CTA ─── */}
      <section className="bg-primary-600 py-20">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
            Ready to read the patent landscape?
          </h2>
          <Link
            href="/login"
            className="inline-flex items-center justify-center px-8 py-3 rounded-lg bg-white text-primary-700 font-semibold hover:bg-gray-100 transition-colors"
          >
            Get started free
          </Link>
          <p className="mt-4 text-sm text-primary-200">
            No credit card required
          </p>
        </div>
      </section>

      {/* ─── 9. Footer ─── */}
      <footer className="bg-gray-900 text-gray-400 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {/* Product */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors">Sign in</Link></li>
              </ul>
            </div>
            {/* Company */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/about" className="hover:text-white transition-colors">Limitations</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
              </ul>
            </div>
            {/* Legal */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/terms" className="hover:text-white transition-colors">Terms</Link></li>
                <li><Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link></li>
                <li><Link href="/about" className="hover:text-white transition-colors">GDPR / delete</Link></li>
              </ul>
            </div>
            {/* Sources */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Sources</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="https://www.uspto.gov/" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">USPTO</a></li>
                <li><a href="https://www.epo.org/" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">EPO</a></li>
                <li><a href="https://www.wipo.int/" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">WIPO</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-10 pt-8 text-center text-sm">
            <p className="mb-2">Patent Pulse · Evidence-backed patent intelligence · Verify with official registers.</p>
            <p>&copy; 2026</p>
          </div>
        </div>
      </footer>
    </>
  );
}

// ─── PricingCard helper component ───
function PricingCard({
  name,
  price,
  period = "",
  features,
  cta,
  href,
  highlighted = false,
  badge,
}: {
  name: string;
  price: string;
  period?: string;
  features: string[];
  cta: string;
  href: string;
  highlighted?: boolean;
  badge?: string;
}) {
  return (
    <div
      className={`relative bg-white border rounded-xl p-6 flex flex-col ${
        highlighted
          ? "border-primary-500 ring-2 ring-primary-500 shadow-lg"
          : "border-gray-200"
      }`}
    >
      {badge && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-xs font-semibold bg-primary-600 text-white">
          {badge}
        </span>
      )}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
        <div className="mt-2">
          <span className="text-3xl font-bold text-gray-900">{price}</span>
          {period && <span className="text-sm text-gray-500">{period}</span>}
        </div>
      </div>
      <ul className="space-y-2 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
            <svg className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {f}
          </li>
        ))}
      </ul>
      <Link
        href={href}
        className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
          highlighted
            ? "bg-primary-600 text-white hover:bg-primary-700"
            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
        }`}
      >
        {cta}
      </Link>
    </div>
  );
}
```

**Verification:**
- `npm run build` passes.
- Visit `/` → full landing page renders (after middleware M3).
- No sidebar visible.
- Check markup: no `"free to use"`, `"public domain"`, `"is used by"`, `"definitely used"`, `"freedom to operate"` (except in the `Not "this patent is used by"` meta-copy inside value prop 2).
- Run grep: `grep -r "free to use\|public domain\|is used by\|definitely used\|freedom to operate" frontend/src/app/\(marketing\)/` → expected zero hits (value prop 2 uses the phrase inside quotes as a counterexample — acceptable).

---

## Chunk M5 — `/pricing` page + feature matrix + FAQ

**LOC:** ~200

### `src/app/(marketing)/pricing/page.tsx`

Full pricing page with:
1. Same 4 cards at top (reuse PricingCard component — extract it to a shared component in M5)
2. Full feature matrix table
3. 9-question FAQ

(The full TSX is ~200 lines; the plan shows the structure. Implementation will inline all content.)

```tsx
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Patent Pulse",
  description: "Free, Basic ($8/yr), Lifetime ($108 once), and Enterprise ($1,000/yr) plans.",
};

// Extract PricingCard to a shared component to avoid duplication
// Path: src/app/(marketing)/PricingCard.tsx

export default function PricingPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
      {/* ─── Header ─── */}
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">Pricing</h1>
        <p className="text-lg text-gray-600">Start free. Upgrade when you need more.</p>
      </div>

      {/* ─── 4 cards (reuse from landing page) ─── */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
        {/* ... same 4 PricingCard components as M4 ... */}
      </div>

      {/* ─── Feature matrix ─── */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-16">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left p-4 font-semibold text-gray-900">Feature</th>
                <th className="p-4 text-center font-semibold text-gray-900">Free</th>
                <th className="p-4 text-center font-semibold text-gray-900">Basic</th>
                <th className="p-4 text-center font-semibold text-gray-900 bg-primary-50">Lifetime</th>
                <th className="p-4 text-center font-semibold text-gray-900">Enterprise</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {/* Price row */}
              <tr>
                <td className="p-4 text-gray-700">Price</td>
                <td className="p-4 text-center">$0</td>
                <td className="p-4 text-center">$8 / year</td>
                <td className="p-4 text-center bg-primary-50">$108 once</td>
                <td className="p-4 text-center">$1,000 / year</td>
              </tr>
              {/* Topics */}
              <tr>
                <td className="p-4 text-gray-700">Topics</td>
                <td className="p-4 text-center">1</td>
                <td className="p-4 text-center">Unlimited</td>
                <td className="p-4 text-center bg-primary-50">Unlimited</td>
                <td className="p-4 text-center">Unlimited</td>
              </tr>
              {/* Alerts */}
              <tr>
                <td className="p-4 text-gray-700">Alerts</td>
                <td className="p-4 text-center">5 / week</td>
                <td className="p-4 text-center">Unlimited</td>
                <td className="p-4 text-center bg-primary-50">Unlimited</td>
                <td className="p-4 text-center">Unlimited</td>
              </tr>
              {/* Weekly digest */}
              <tr>
                <td className="p-4 text-gray-700">Weekly digest</td>
                <td className="p-4 text-center"><Check /></td>
                <td className="p-4 text-center"><Check /></td>
                <td className="p-4 text-center bg-primary-50"><Check /></td>
                <td className="p-4 text-center"><Check /></td>
              </tr>
              {/* CSV export */}
              <tr>
                <td className="p-4 text-gray-700">CSV export</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center"><Check /></td>
                <td className="p-4 text-center bg-primary-50"><Check /></td>
                <td className="p-4 text-center"><Check /></td>
              </tr>
              {/* PDF reports */}
              <tr>
                <td className="p-4 text-gray-700">PDF reports</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center bg-primary-50"><Check /></td>
                <td className="p-4 text-center"><Check /></td>
              </tr>
              {/* API access */}
              <tr>
                <td className="p-4 text-gray-700">API access</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center bg-primary-50">—</td>
                <td className="p-4 text-center">✓ (300/min)</td>
              </tr>
              {/* Admin tools */}
              <tr>
                <td className="p-4 text-gray-700">Admin tools</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center bg-primary-50">—</td>
                <td className="p-4 text-center"><Check /></td>
              </tr>
              {/* Support */}
              <tr>
                <td className="p-4 text-gray-700">Support</td>
                <td className="p-4 text-center">Community</td>
                <td className="p-4 text-center">Email</td>
                <td className="p-4 text-center bg-primary-50">Email</td>
                <td className="p-4 text-center">Priority email</td>
              </tr>
              {/* Billing */}
              <tr>
                <td className="p-4 text-gray-700">Billing</td>
                <td className="p-4 text-center">—</td>
                <td className="p-4 text-center">Annual</td>
                <td className="p-4 text-center bg-primary-50">One-time</td>
                <td className="p-4 text-center">Annual</td>
              </tr>
              {/* Auth */}
              <tr>
                <td className="p-4 text-gray-700">Auth</td>
                <td className="p-4 text-center">Magic link</td>
                <td className="p-4 text-center">Magic link</td>
                <td className="p-4 text-center bg-primary-50">Magic link</td>
                <td className="p-4 text-center">Magic link</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── FAQ ─── */}
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-8">Frequently asked questions</h2>
        <div className="space-y-6">
          <Faq q="Can I switch tiers?" a="Yes. Upgrade or downgrade at any time..." />
          <Faq q="Can I cancel anytime?" a="Yes. Cancel from your account page. No penalties." />
          <Faq q="What is your refund policy?" a="Refunds are handled case-by-case..." />
          <Faq q="What does 'Lifetime' mean?" a="One payment of $108 gives you lifetime access..." />
          <Faq q="Do you charge tax / VAT?" a="Tax handling depends on your location..." />
          <Faq q="Do you provide invoices?" a="Invoice PDFs are available in the Stripe billing portal..." />
          <Faq q="What happens to my data if I cancel?" a="Your data is retained per our privacy policy..." />
          <Faq q="How do API keys work?" a="Enterprise-tier users can create API keys in their account..." />
          <Faq q="Can I delete my account?" a="Yes. Use the 'Delete my account' button on /account..." />
        </div>
      </div>
    </div>
  );
}

function Check() {
  return (
    <svg className="w-5 h-5 text-green-500 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <details className="group border-b border-gray-200 pb-6">
      <summary className="flex items-center justify-between cursor-pointer">
        <h3 className="text-sm font-semibold text-gray-900">{q}</h3>
        <svg className="w-5 h-5 text-gray-400 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </summary>
      <p className="mt-3 text-sm text-gray-600 leading-relaxed">{a}</p>
    </details>
  );
}
```

### Refactor: extract `PricingCard` to shared component

Move the `PricingCard` function from `(marketing)/page.tsx` to `(marketing)/PricingCard.tsx` and import in both pages.

**Verification:**
- `npm run build` passes.
- Visit `/pricing` → full pricing page renders with feature matrix and FAQ.
- The `BriefingPreview` component is used on `/pricing` if specified — DRY check passes.
- Run the AGENTS.md forbidden-phrase grep against `(marketing)/pricing/page.tsx`.

---

## Chunk M6 — BriefingPreview component

**LOC:** ~80

### `src/app/(marketing)/BriefingPreview.tsx`

A `"use client"` component used in the hero section (and potentially pricing page). CSS-rendered weekly briefing card.

```tsx
"use client";

export function BriefingPreview() {
  const items = [
    { docId: "USPTO:20260144033", score: 89, tier: "strong", confidence: "high" },
    { docId: "USPTO:20260144068", score: 86, tier: "strong", confidence: "high", selfCite: true },
    { docId: "USPTO:20260144041", score: 82, tier: "strong", confidence: "medium" },
    { docId: "USPTO:20260144022", score: 78, tier: "medium", confidence: "high" },
    { docId: "USPTO:20260144055", score: 75, tier: "medium", confidence: "medium" },
  ];

  const tierColor = (t: string) =>
    t === "strong" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800";

  return (
    <div className="w-[340px] bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-primary-600 text-white px-5 py-3">
        <p className="text-xs font-semibold uppercase tracking-wider opacity-90">
          Your weekly briefing
        </p>
        <p className="text-sm font-medium mt-0.5">G06F · Computing</p>
      </div>

      {/* Items */}
      <div className="divide-y divide-gray-100">
        {items.slice(0, 5).map((item, i) => (
          <div key={item.docId} className={`px-5 py-3 ${i >= 2 ? "opacity-40" : ""}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono text-gray-500">{item.docId}</span>
              <span className="text-xs font-bold text-primary-700">Score {item.score}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${tierColor(item.tier)}`}>
                {item.tier}
              </span>
              <span className="text-[10px] text-gray-400">confidence: {item.confidence}</span>
              {item.selfCite && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-100 text-yellow-800 border border-yellow-300">
                  ⚠ self-citation risk
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 text-right">
        {/* The opacity-40 dimming shows rows 3-5 are partially visible */}
        <span className="text-xs text-primary-600 font-medium">
          {items.length - 2} more · view all →
        </span>
      </div>
    </div>
  );
}
```

**Verification:**
- Component renders visible on the landing page hero at `/`.
- No AGENTS.md forbidden phrases in component text.
- The card uses real-looking doc IDs (USPTO: prefix), real confidence labels, real evidence tiers, and the self-citation risk chip.

---

## Chunk M7 — Skeleton legal pages (`/terms`, `/privacy`, `/contact`)

**LOC:** ~120

Three pages from the design spec's "Skeleton legal content" section.

### Files to create

| File | Content |
|---|---|
| `src/app/(marketing)/terms/page.tsx` | Terms of Service (scrubbed of real jurisdiction until counsel reviews) |
| `src/app/(marketing)/privacy/page.tsx` | Privacy Policy (with V1-specific data disclosures: Stripe, Resend, Anthropic, OpenAI) |
| `src/app/(marketing)/contact/page.tsx` | Contact page (mailto link) |

**Content detail:** See the design spec §"Skeleton legal content (M7)". Each page gets:
- Correct metadata export
- Proper legal disclaimer header ("This is placeholder content — counsel review pending")
- Complete section structure with V1-specific details where the spec specifies them (e.g., privacy page names Stripe, Resend, Anthropic, OpenAI as third-party processors)

**Verification:**
- `npm run build` passes.
- Visit `/terms` → full TOS renders.
- Visit `/privacy` → privacy policy renders with V1 subprocessor list.
- Visit `/contact` → mailto link works.
- All three pages are accessible from the footer.

---

## Chunk M8 — Metadata + OG image + favicon + robots.txt

**LOC:** ~40

### Steps

1. **Metadata exports per page** — already done in M4 (landing page), M5 (pricing). Check M7 pages have metadata.

2. **OG image generation** — use Sharp to create a 1200×630 PNG with sky-600 background, white "Patent Pulse" text, and tagline.

   Run in terminal:
   ```bash
   cd frontend
   node -e "
   const sharp = require('sharp');
   // ... render SVG to PNG at 1200×630
   "
   ```

   Alternative: write a one-off script `scripts/generate-og-image.mjs` that creates `public/og-image.png`.

3. **Favicon** — check if `public/favicon.ico` exists. If not, generate a text-mark SVG favicon and place it.

4. **robots.txt** — create `public/robots.txt`:
   ```
   User-agent: *
   Allow: /
   Allow: /pricing
   Allow: /about
   Allow: /terms
   Allow: /privacy
   Disallow: /admin/
   ```

**Verification:**
- Run `ls frontend/public/og-image.png` → exists, 1200×630.
- Run `ls frontend/public/favicon.ico` → exists (or SVG equivalent).
- Visit `/robots.txt` → returns the expected content.
- `npm run build` passes.

---

## Chunk M9 — Mobile responsive testing + polish

**LOC:** ~50

### Steps

1. **Mobile-first sweep** — per the spec's responsiveness table:

   | Section | Breakpoint check |
   |---|---|
   | Hero | At 375px: copy stacks above, CTA buttons full-width. BriefingPreview hidden below md. |
   | Data strip | Wraps to multiple lines cleanly at < sm. |
   | Value props | 1 column at < sm, 2 at sm-md, 2×2 at md+. |
   | Use cases | 1 column all the way to md, then 3 columns. |
   | How-it-works | Vertical stack at < md, horizontal row at md+. |
   | Pricing 4-up | 1 column at < sm, 2×2 at sm-lg, 4 at lg+. |
   | Footer | 2 columns at < md, 4 at md+. No accordion needed for V1. |
   | Nav | Hamburger at < md, full links at md+. |

2. **Polish fixes** — adjust any Tailwind classes that cause overflow, text clipping, or bad spacing on mobile.

3. **Lighthouse audit** — run `npx lighthouse http://localhost:3000/ --chrome-flags="--headless" --output json --output-path /tmp/lh.json`. Target ≥ 90 on landing page.

**Verification:**
- `npm run build` passes.
- Chrome DevTools responsive mode at 375px: each section renders cleanly, no horizontal scroll.
- Lighthouse score ≥ 90 on landing page (report the actual score).

---

## Full M1-M9 verification checklist (run after M9)

- [ ] `npm run build` — zero errors, zero warnings
- [ ] Docker `docker compose up -d` → `curl localhost:3000/` → 200 with full landing HTML
- [ ] Visit `/` unauthenticated → landing page renders
- [ ] Visit `/` with auth_session cookie → redirect to `/today`
- [ ] Visit `/pricing` → full pricing page with feature matrix + FAQ
- [ ] Visit `/about` → limitations page (moved from old route)
- [ ] Visit `/terms` → terms page
- [ ] Visit `/privacy` → privacy page
- [ ] Visit `/contact` → contact page with mailto
- [ ] Visit `/login` → login page in centered layout, no sidebar
- [ ] Visit `/today` → app page with sidebar
- [ ] OG image loads at `/og-image.png`
- [ ] Robots.txt loads at `/robots.txt`
- [ ] Language audit grep against all new files: zero forbidden phrases
- [ ] Lighthouse landing page score ≥ 90
- [ ] Mobile responsive at 375px for all 10 sections
- [ ] `BriefingPreview` component reused (only defined once, imported where used)

---

## Estimated cumulative LOC

| Chunk | LOC |
|---|---|
| M1 | 0 (file moves) |
| M2 | ~80 |
| M3 | ~20 |
| M4 | ~350 |
| M5 | ~200 |
| M6 | ~80 |
| M7 | ~120 |
| M8 | ~40 |
| M9 | ~50 (fixes) |
| **Total** | **~940** |
