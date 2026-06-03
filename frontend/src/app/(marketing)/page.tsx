import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { PricingCard } from "./PricingCard";
import { BriefingPreview } from "./BriefingPreview";
import { BRAND, COPY } from "@/lib/brand";
import { Reveal } from "@/components/ui/Reveal";

export const metadata: Metadata = {
  title: {
    default: `${BRAND.name}: ${COPY.tagline}`,
    template: `%s: ${BRAND.name}`,
  },
  description: COPY.description,
  metadataBase: new URL(BRAND.url),
  openGraph: {
    title: BRAND.name,
    description: COPY.description,
    siteName: BRAND.name,
    images: [{ url: "/og-image.svg", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: BRAND.name,
    description: COPY.description,
    images: ["/og-image.svg"],
  },
};

// ─── Confidence pill helpers ───

const CONFIDENCE_PILLS = [
  { label: "active_estimated", color: "bg-[var(--score-high-bg)] text-[var(--score-high)]" },
  { label: "expiring_soon", color: "bg-[var(--score-medium-bg)] text-[var(--score-medium)]" },
  { label: "lapsed_possible", color: "bg-orange-500/15 text-orange-400" },
  { label: "lapsed_confirmed", color: "bg-red-500/15 text-red-400" },
];

const TIER_BADGES = [
  { label: "strong", color: "bg-[var(--score-high-bg)] text-[var(--score-high)]" },
  { label: "medium", color: "bg-[var(--score-medium-bg)] text-[var(--score-medium)]" },
  { label: "weak", color: "bg-[var(--bg-elevated)] text-[var(--text-secondary)]" },
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
      <section className="relative overflow-hidden bg-[var(--bg-base)] pt-24 pb-20">
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left: copy */}
            <div>
              <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-[var(--radius-full)] border border-[var(--border-subtle)] bg-[var(--bg-glass)] text-xs text-[var(--text-secondary)]">
                <span className="status-dot status-dot--live" />
                Patent intelligence platform
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight tracking-tight text-[var(--text-primary)]">
                {COPY.heroHeadline}
              </h1>
              <p className="mt-6 text-lg text-[var(--text-secondary)] leading-relaxed max-w-xl">
                {COPY.heroSubheadline}
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-4">
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center px-7 py-3.5 rounded-[var(--radius-md)] bg-[var(--accent)] text-white font-semibold text-base hover:bg-[var(--accent-hover)] active:scale-[0.98] transition-all"
                >
                  {COPY.ctaPrimary}
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center px-7 py-3.5 rounded-[var(--radius-md)] border border-[var(--border-default)] text-[var(--text-secondary)] font-semibold hover:bg-[var(--bg-glass)] hover:border-[var(--accent)]/30 transition-all"
                >
                  See pricing
                </Link>
              </div>
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
      <section className="border-y border-[var(--border-subtle)] bg-[var(--bg-base)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-sm text-[var(--text-muted)] text-center flex flex-wrap justify-center gap-x-6 gap-y-2">
            <span>64,231 patents</span>
            <span>USPTO</span>
            <span>EPO</span>
            <span>WIPO</span>
            <span>Updated weekly</span>
            <span>Evidence-backed</span>
          </p>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          3. VALUE PROPS — 4 premium cards, 2×2 grid
          ═══════════════════════════════════════════ */}
      <section className="bg-[var(--bg-elevated)] py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-4">
            An intelligence layer for patents, ideas, and emerging opportunities.
          </h2>
          <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
            Four core modules. Each calibrated, evidence-backed, and honest about
            its confidence.
          </p>
        </div>

        <Reveal>
          <div className="grid sm:grid-cols-2 gap-8">
          {/* Card 1 — Filing Trends */}
          <div className="surface-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[var(--accent-muted)] text-[var(--accent)]">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
                Filing Trends
              </span>
            </div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Spot unusual invention movement.
            </h3>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              Track filing surges across patent classes before the trend becomes
              mainstream. Every narrative cites the underlying patents and is
              refreshed as new filings drop.
            </p>
          </div>

          {/* Card 2 — Company Moves */}
          <div className="surface-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[var(--accent-muted)] text-[var(--accent)]">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M10 2a4 4 0 00-4 4v1H5a1 1 0 00-.994.89l-1 9A1 1 0 004 18h12a1 1 0 00.994-1.11l-1-9A1 1 0 0015 7h-1V6a4 4 0 00-4-4zm2 5V6a2 2 0 10-4 0v1h4z" />
                </svg>
                Company Moves
              </span>
            </div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Track where companies are inventing.
            </h3>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              Monitor where assignees are increasing invention activity and
              shifting R&D focus across patent classes, with deltas and trend
              direction surfaced automatically.
            </p>
          </div>

          {/* Card 3 — Notable Patents */}
          <div className="surface-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[var(--accent-muted)] text-[var(--accent)]">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                Notable Patents
              </span>
            </div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Find the ideas companies are quietly betting on.
            </h3>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              Surface individual filings that may signal meaningful technology,
              product, or market movement. With AI narratives, expiry status,
              family risk, and source links to verify.
            </p>
          </div>

          {/* Card 4 — Expiring Opportunities */}
          <div className="surface-card p-6">
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
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Expiring opportunities, honestly scored.
            </h3>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              Identify patents approaching expiration that may create whitespace
              for builders, operators, and investors. Every estimate labeled with
              explicit confidence, active family risk surfaced, and official
              registers linked for verification.
            </p>
          </div>
        </div>

        {/* Usage signals standalone card */}
        <div className="mt-8 surface-card p-6">
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
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
            Commercial usage signals, evidence-backed.
          </h3>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-3xl">
            See where patent ideas show up in newer art. With a tier (strong /
            medium / weak) on every piece of evidence and a source link beneath.
            No &ldquo;this patent is used by Company X&rdquo; claims. Only patterns
            you can verify.
          </p>
        </div>
        </Reveal>
      </section>

      {/* ═══════════════════════════════════════════
          4. USE CASES — 3 personas
          ═══════════════════════════════════════════ */}
      <section className="bg-[var(--bg-elevated)] py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] text-center mb-12">
            Who it&rsquo;s for
          </h2>
          <Reveal delay={0.1}>
          <div className="space-y-6">
            {/* Top row: Attorneys — full width */}
            <div className="surface-card p-6">
              <h3 className="font-semibold text-[var(--text-primary)] mb-3">
                For patent attorneys &amp; law firms
              </h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-3xl">
                Surveil portfolios with confidence-labeled expiry estimates.
                Build evidence packets with source citations linked to official
                registers. Hand clients reports they can verify.
              </p>
              <p className="text-xs text-[var(--text-muted)] mt-3">
                Tracks: expiry windows, active family risk, cite-graph signals
              </p>
            </div>

            {/* Bottom row: 2-up */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="surface-card p-6">
                <h3 className="font-semibold text-[var(--text-primary)] mb-3">
                  For corporate IP teams
                </h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Monitor your CPC areas for filing surges, family expansions, and
                  emerging opportunity zones. Track where your prior art appears in
                  newer filings with evidence tiers, not claims.
                </p>
                <p className="text-xs text-[var(--text-muted)] mt-3">
                  Tracks: competitor filings, expiry windows, usage signals
                </p>
              </div>

              <div className="surface-card p-6">
                <h3 className="font-semibold text-[var(--text-primary)] mb-3">
                  For founders &amp; investors
                </h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Find ideas approaching estimated expiry in your thesis areas
                  with confidence labels so you know what&rsquo;s open vs.
                  uncertain. Subscribe to topics tied to your thesis.
                </p>
                <p className="text-xs text-[var(--text-muted)] mt-3">
                  Tracks: expiring opportunities, whitespace topics, weekly briefings
                </p>
              </div>
            </div>
          </div>
          </Reveal>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          5. HOW IT WORKS — 3 steps
          ═══════════════════════════════════════════ */}
      <Section className="py-20">
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] text-center mb-12">
          How it works
        </h2>
        <Reveal delay={0.15}>
        <div className="flex flex-col md:flex-row gap-4 md:gap-0 max-w-4xl mx-auto">
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
              desc: "Full intelligence per patent. Expiry, family, usage signals, AI narratives, source links.",
            },
          ].map((s, i) => (
            <div key={s.step} className="flex-1 flex flex-col md:flex-row items-center gap-4">
              <div className="flex flex-col items-center text-center md:text-left md:items-start gap-2">
                <div className="w-10 h-10 rounded-[var(--radius-md)] bg-[var(--accent)] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {s.step}
                </div>
                <div>
                  <h3 className="font-semibold text-[var(--text-primary)] text-sm">{s.title}</h3>
                  <p className="text-xs text-[var(--text-muted)] mt-1 max-w-[200px]">{s.desc}</p>
                </div>
              </div>
              {i < 2 && (
                <div className="hidden md:block w-12 h-px bg-[var(--border-default)] mt-5 flex-shrink-0" aria-hidden="true" />
              )}
            </div>
          ))}
        </div>
        </Reveal>
      </Section>

      {/* ═══════════════════════════════════════════
          6. PRICING TEASER — 4 cards
          ═══════════════════════════════════════════ */}
      <section className="bg-[var(--bg-base)] py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-4">
              Pricing
            </h2>
            <p className="text-[var(--text-secondary)] text-lg">
              Start free. Upgrade when you need more.
            </p>
          </div>
          <Reveal delay={0.1}>
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
          </Reveal>
          {/* Feature comparison table */}
          <div className="mt-12 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  <th className="text-left py-3 pr-4 text-[var(--text-muted)] font-medium">Feature</th>
                  <th className="text-center py-3 px-3 text-[var(--text-muted)] font-medium">Free</th>
                  <th className="text-center py-3 px-3 text-[var(--text-muted)] font-medium">Basic</th>
                  <th className="text-center py-3 px-3 text-[var(--accent)] font-medium">Lifetime</th>
                  <th className="text-center py-3 pl-3 text-[var(--text-muted)] font-medium">Enterprise</th>
                </tr>
              </thead>
              <tbody className="text-[var(--text-secondary)]">
                {[
                  ["Topics", "1", "Unlimited", "Unlimited", "Unlimited"],
                  ["Alerts / week", "5", "Unlimited", "Unlimited", "Unlimited"],
                  ["Weekly digest", "✓", "✓", "✓", "✓"],
                  ["CSV export", "—", "✓", "✓", "✓"],
                  ["PDF export", "—", "—", "✓", "✓"],
                  ["API access", "—", "—", "—", "300/min"],
                  ["Admin tools", "—", "—", "—", "✓"],
                  ["Priority support", "—", "—", "—", "✓"],
                ].map((row, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-glass)] transition-colors">
                    <td className="py-2.5 pr-4 text-[var(--text-primary)]">{row[0]}</td>
                    <td className="text-center py-2.5 px-3">{row[1]}</td>
                    <td className="text-center py-2.5 px-3">{row[2]}</td>
                    <td className="text-center py-2.5 px-3 bg-[var(--accent-muted)] text-[var(--accent)]">{row[3]}</td>
                    <td className="text-center py-2.5 pl-3">{row[4]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-center mt-8">
            <Link
              href="/pricing"
              className="text-sm text-[var(--accent)] hover:text-[var(--accent)] font-medium"
            >
              See full feature comparison →
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          7. TRUST BLOCK
          ═══════════════════════════════════════════ */}
      <Reveal delay={0.1}>
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20 border-t border-[var(--border-subtle)]">
        <h2 className="text-xl font-bold text-[var(--text-primary)] text-center mb-6">
          We show our work.
        </h2>
        <p className="text-[var(--text-secondary)] leading-relaxed text-center mb-8">
          {BRAND.name} calibrates uncertainty. We label every estimate. We cite
          every source. We don&rsquo;t claim freedom-to-operate, we don&rsquo;t
          invent market data, and we tell you when our confidence is low.
        </p>
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-[var(--text-muted)] mb-6">
          <span>Data: USPTO + EPO + WIPO</span>
          <span>Updated weekly</span>
          <span>AI: Claude Sonnet narratives</span>
          <span>Not legal advice</span>
        </div>
        <div className="text-center">
          <Link
            href="/about"
            className="text-sm text-[var(--accent)] hover:text-[var(--accent)] font-medium"
          >
            Read the limitations →
          </Link>
        </div>
      </section>
      </Reveal>

      {/* ═══════════════════════════════════════════
          8. FINAL CTA
          ═══════════════════════════════════════════ */}
      <section className="bg-[var(--accent)] py-24">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
            Ready to track the world&rsquo;s invention signals?
          </h2>
          <Link
            href="/login"
            className="inline-flex items-center justify-center px-8 py-3.5 rounded-[var(--radius-md)] bg-white text-[var(--accent)] font-semibold text-base hover:bg-white/90 active:scale-[0.98] transition-all"
          >
            {COPY.ctaPrimary}
          </Link>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          9. FOOTER
          ═══════════════════════════════════════════ */}
      <footer className="bg-[var(--bg-elevated)] text-[var(--text-muted)] py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8">
            {/* Product */}
            <div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/pricing" className="hover:text-[var(--text-primary)] transition-colors">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href="/login" className="hover:text-[var(--text-primary)] transition-colors">
                    Sign in
                  </Link>
                </li>
              </ul>
            </div>
            {/* Company */}
            <div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Company</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/about" className="hover:text-[var(--text-primary)] transition-colors">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="/about" className="hover:text-[var(--text-primary)] transition-colors">
                    Limitations
                  </Link>
                </li>
                <li>
                  <Link href="/contact" className="hover:text-[var(--text-primary)] transition-colors">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            {/* Legal */}
            <div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/terms" className="hover:text-[var(--text-primary)] transition-colors">
                    Terms
                  </Link>
                </li>
                <li>
                  <Link href="/privacy" className="hover:text-[var(--text-primary)] transition-colors">
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link href="/about" className="hover:text-[var(--text-primary)] transition-colors">
                    GDPR / delete
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-[var(--border-default)] mt-10 pt-8 text-center text-sm">
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
