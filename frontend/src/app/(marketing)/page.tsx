import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { PricingCard } from "./PricingCard";
import { BriefingPreview } from "./BriefingPreview";
import { BRAND, COPY } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — ${COPY.tagline}`,
  description: COPY.description,
  openGraph: {
    title: BRAND.name,
    description: COPY.description,
    images: [{ url: "/og-image.svg", width: 1200, height: 630 }],
  },
};

// ─── Confidence pill helpers ───

const CONFIDENCE_PILLS = [
  { label: "active_estimated", color: "bg-green-100 text-green-800" },
  { label: "expiring_soon", color: "bg-amber-100 text-amber-800" },
  { label: "lapsed_possible", color: "bg-orange-100 text-orange-800" },
  { label: "lapsed_confirmed", color: "bg-red-100 text-red-800" },
];

const TIER_BADGES = [
  { label: "strong", color: "bg-green-100 text-green-800" },
  { label: "medium", color: "bg-amber-100 text-amber-800" },
  { label: "weak", color: "bg-gray-100 text-gray-600" },
];

// ─── Section wrapper ───

function Section({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 ${className}`}>
      {children}
    </section>
  );
}

// ─── Main landing page ───

export default function LandingPage() {
  return (
    <>
      {/* ═══════════════════════════════════════════
          1. HERO — premium dark with animated background
          ═══════════════════════════════════════════ */}
      <section className="relative overflow-hidden bg-[#0a0e27] text-white pt-28 pb-24">
        {/* Animated grid background */}
        <div className="absolute inset-0 hero-grid-bg" />

        {/* Signal orbs */}
        <div
          className="hero-signal-orb w-[500px] h-[500px] animate-drift-slow"
          style={{
            background: "radial-gradient(circle, rgba(99,102,241,0.4), transparent)",
            top: "10%",
            left: "-10%",
          }}
        />
        <div
          className="hero-signal-orb w-[400px] h-[400px] animate-drift-slower"
          style={{
            background: "radial-gradient(circle, rgba(139,92,246,0.3), transparent)",
            bottom: "-15%",
            right: "-5%",
          }}
        />
        <div
          className="hero-signal-orb w-[300px] h-[300px]"
          style={{
            background: "radial-gradient(circle, rgba(6,182,212,0.25), transparent)",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          }}
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left: copy */}
            <div>
              <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full border border-indigo-400/20 bg-white/5 text-xs text-indigo-300">
                <span className="signal-pulse" />
                Intelligence platform · {BRAND.name}
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight tracking-tight">
                {COPY.heroHeadline}
              </h1>
              <p className="mt-6 text-lg text-indigo-200/80 leading-relaxed max-w-xl">
                {COPY.heroSubheadline}
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-4">
                <Link
                  href="/login"
                  className="shine-cta inline-flex items-center justify-center px-7 py-3.5 rounded-lg text-white font-semibold text-base"
                >
                  {COPY.ctaPrimary}
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center px-7 py-3.5 rounded-lg border border-indigo-400/20 text-indigo-200 font-semibold hover:bg-white/5 transition-colors"
                >
                  See pricing
                </Link>
              </div>
              <p className="mt-6 text-xs text-indigo-300/50">
                No credit card required
              </p>
            </div>

            {/* Right: briefing preview card placeholder */}
            <div className="hidden md:flex justify-center">
              <BriefingPreview />
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          2. DATA STRIP
          ═══════════════════════════════════════════ */}
      <section className="border-y border-gray-200 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-gray-500 text-center flex flex-wrap justify-center gap-x-6 gap-y-2">
            <span>64,231 patents</span>
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

      {/* ═══════════════════════════════════════════
          3. VALUE PROPS — 4 premium cards, 2×2 grid
          ═══════════════════════════════════════════ */}
      <Section className="py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4">
            An intelligence layer for patents, ideas, and emerging opportunities.
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Four core modules — each calibrated, evidence-backed, and honest about
            its confidence.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-8">
          {/* Card 1 — Filing Trends */}
          <div className="signal-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
                Filing Trends
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Spot unusual invention movement.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Track filing surges across patent classes before the trend becomes
              mainstream. Every narrative cites the underlying patents and is
              refreshed as new filings drop.
            </p>
          </div>

          {/* Card 2 — Company Moves */}
          <div className="signal-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-violet-100 text-violet-700">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 2a4 4 0 00-4 4v1H5a1 1 0 00-.994.89l-1 9A1 1 0 004 18h12a1 1 0 00.994-1.11l-1-9A1 1 0 0015 7h-1V6a4 4 0 00-4-4zm2 5V6a2 2 0 10-4 0v1h4z" />
                </svg>
                Company Moves
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Track where companies are inventing.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Monitor where assignees are increasing invention activity and
              shifting R&D focus across patent classes, with deltas and trend
              direction surfaced automatically.
            </p>
          </div>

          {/* Card 3 — Notable Patents */}
          <div className="signal-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-cyan-100 text-cyan-700">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                Notable Patents
              </span>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Find the ideas companies are quietly betting on.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Surface individual filings that may signal meaningful technology,
              product, or market movement — with AI narratives, expiry status,
              family risk, and source links to verify.
            </p>
          </div>

          {/* Card 4 — Expiring Opportunities */}
          <div className="signal-card p-6">
            <div className="flex flex-wrap gap-1.5 mb-4">
              {CONFIDENCE_PILLS.map((p) => (
                <span
                  key={p.label}
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${p.color}`}
                >
                  {p.label}
                </span>
              ))}
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Expiring opportunities, honestly scored.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Identify patents approaching expiration that may create whitespace
              for builders, operators, and investors. Every estimate labeled with
              explicit confidence, active family risk surfaced, and official
              registers linked for verification.
            </p>
          </div>
        </div>

        {/* Usage signals standalone card */}
        <div className="mt-8 signal-card p-6">
          <div className="flex flex-wrap gap-1.5 mb-4 items-center">
            {TIER_BADGES.map((b) => (
              <span
                key={b.label}
                className={`px-2 py-0.5 rounded text-xs font-semibold ${b.color}`}
              >
                {b.label}
              </span>
            ))}
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-300">
              ⚠ self-citation risk
            </span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Commercial usage signals, evidence-backed.
          </h3>
          <p className="text-sm text-gray-600 leading-relaxed max-w-3xl">
            See where patent ideas show up in newer art — with a tier (strong /
            medium / weak) on every piece of evidence and a source link beneath.
            No &ldquo;this patent is used by Company X&rdquo; claims. Only patterns
            you can verify.
          </p>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          4. USE CASES — 3 personas
          ═══════════════════════════════════════════ */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
            Who it&rsquo;s for
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Attorneys */}
            <div className="signal-card p-6">
              <h3 className="font-semibold text-gray-900 mb-3">
                For patent attorneys &amp; law firms
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Surveil portfolios with confidence-labeled expiry estimates.
                Build evidence packets with source citations linked to official
                registers. Hand clients reports they can verify.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> expiry
                windows · active family risk · cite-graph signals
              </p>
            </div>

            {/* Corporate IP */}
            <div className="signal-card p-6">
              <h3 className="font-semibold text-gray-900 mb-3">
                For corporate IP teams
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Monitor your CPC areas for filing surges, family expansions, and
                emerging opportunity zones. Track where your prior art appears in
                newer filings — with evidence tiers, not claims.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> competitor
                filings · expiry windows · usage signals
              </p>
            </div>

            {/* Founders */}
            <div className="signal-card p-6">
              <h3 className="font-semibold text-gray-900 mb-3">
                For founders &amp; investors
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Find ideas approaching estimated expiry in your thesis areas —
                with confidence labels so you know what&rsquo;s open vs.
                uncertain. Subscribe to topics tied to your thesis. Verify
                before you commit.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> expiring
                opportunities · whitespace topics · weekly briefings
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          5. HOW IT WORKS — 3 steps
          ═══════════════════════════════════════════ */}
      <Section className="py-20">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-12">
          How it works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              step: "1",
              title: "Pick your topics",
              desc: "Subscribe by CPC class, keyword, assignee, or opportunity-score threshold.",
            },
            {
              step: "2",
              title: "Get briefings + alerts",
              desc: "Sunday morning weekly digest. Instant alerts on high-priority matches.",
            },
            {
              step: "3",
              title: "Drill into patents",
              desc: "Full intelligence per patent — expiry, family, usage signals, AI narratives, source links.",
            },
          ].map((s) => (
            <div key={s.step} className="relative text-center">
              <div className="w-12 h-12 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-4">
                {s.step}
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{s.title}</h3>
              <p className="text-sm text-gray-600">{s.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          6. PRICING TEASER — 4 cards
          ═══════════════════════════════════════════ */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4">
              Pricing
            </h2>
            <p className="text-gray-600 text-lg">
              Start free. Upgrade when you need more.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <PricingCard
              name="Free"
              price="$0"
              features={["1 topic", "5 alerts/week", "Weekly digest"]}
              cta="Get started"
              href="/login"
            />
            <PricingCard
              name="Basic"
              price="$8"
              period="/year"
              features={[
                "Unlimited topics",
                "Unlimited alerts",
                "CSV export",
                "Weekly digest",
              ]}
              cta="Choose Basic"
              href="/login"
            />
            <PricingCard
              name="Lifetime"
              price="$108"
              period=" once"
              features={[
                "Unlimited topics",
                "Unlimited alerts",
                "CSV + PDF export",
                "Weekly digest",
              ]}
              cta="Choose Lifetime"
              href="/login"
              highlighted
              badge="Best value"
            />
            <PricingCard
              name="Enterprise"
              price="$1,000"
              period="/year"
              features={[
                "Everything in Lifetime",
                "API access (300/min)",
                "Admin tools",
                "Priority support",
              ]}
              cta="Choose Enterprise"
              href="/login"
            />
          </div>
          <div className="text-center mt-8">
            <Link
              href="/pricing"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              See full feature comparison →
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          7. TRUST BLOCK
          ═══════════════════════════════════════════ */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-xl font-bold text-gray-900 text-center mb-6">
          We show our work.
        </h2>
        <p className="text-gray-600 leading-relaxed text-center mb-8">
          {BRAND.name} calibrates uncertainty. We label every estimate. We cite
          every source. We don&rsquo;t claim freedom-to-operate, we don&rsquo;t
          invent market data, and we tell you when our confidence is low.
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
          <Link
            href="/about"
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            Read the limitations →
          </Link>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          8. FINAL CTA
          ═══════════════════════════════════════════ */}
      <section className="bg-primary-700 py-20">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
            Ready to track the world&rsquo;s invention signals?
          </h2>
          <Link
            href="/login"
            className="shine-cta inline-flex items-center justify-center px-8 py-3.5 rounded-lg text-white font-semibold text-base"
          >
            {COPY.ctaPrimary}
          </Link>
          <p className="mt-4 text-sm text-primary-200">
            No credit card required
          </p>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          9. FOOTER
          ═══════════════════════════════════════════ */}
      <footer className="bg-gray-900 text-gray-400 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {/* Product */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/pricing" className="hover:text-white transition-colors">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href="/login" className="hover:text-white transition-colors">
                    Sign in
                  </Link>
                </li>
              </ul>
            </div>
            {/* Company */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Company</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/about" className="hover:text-white transition-colors">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="/about" className="hover:text-white transition-colors">
                    Limitations
                  </Link>
                </li>
                <li>
                  <Link href="/contact" className="hover:text-white transition-colors">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            {/* Legal */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/terms" className="hover:text-white transition-colors">
                    Terms
                  </Link>
                </li>
                <li>
                  <Link href="/privacy" className="hover:text-white transition-colors">
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link href="/about" className="hover:text-white transition-colors">
                    GDPR / delete
                  </Link>
                </li>
              </ul>
            </div>
            {/* Sources */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Sources</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <a
                    href="https://www.uspto.gov/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    USPTO
                  </a>
                </li>
                <li>
                  <a
                    href="https://www.epo.org/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    EPO
                  </a>
                </li>
                <li>
                  <a
                    href="https://www.wipo.int/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-white transition-colors"
                  >
                    WIPO
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-10 pt-8 text-center text-sm">
            <p className="mb-2">
              {COPY.footerDisclaimer}
            </p>
            <p>&copy; {BRAND.year}</p>
          </div>
        </div>
      </footer>
    </>
  );
}
