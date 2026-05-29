import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { PricingCard } from "./PricingCard";
import { BriefingPreview } from "./BriefingPreview";

export const metadata: Metadata = {
  title: "Patent Pulse — Patent intelligence with the receipts",
  description:
    "Track expiry, usage signals, and filing trends across USPTO, EPO, and WIPO data — every claim labeled with confidence, every source linked back.",
  openGraph: {
    title: "Patent Pulse — Patent intelligence with the receipts",
    description:
      "Track expiry, usage signals, and filing trends across USPTO, EPO, and WIPO data.",
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
          1. HERO — split layout
          ═══════════════════════════════════════════ */}
      <Section className="pt-24 pb-20">
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

          {/* Right: briefing preview card placeholder */}
          <div className="hidden md:flex justify-center">
            <BriefingPreview />
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          2. DATA STRIP
          ═══════════════════════════════════════════ */}
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

      {/* ═══════════════════════════════════════════
          3. VALUE PROPS — 4 cards, 2×2 grid
          ═══════════════════════════════════════════ */}
      <Section className="py-20">
        <div className="grid sm:grid-cols-2 gap-8">
          {/* Card 1 — Expiry Intelligence */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
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
              Expiry intelligence, calibrated.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Estimated expiry dates with explicit confidence labels — not raw
              guesses. Active family members in other jurisdictions surfaced
              when relevant. Every estimate links to the official register for
              verification.
            </p>
          </div>

          {/* Card 2 — Usage Signals */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            <div className="flex flex-wrap gap-1.5 mb-4">
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
              Usage signals, evidence-backed.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              See how patent ideas appear in newer art — with a tier
              (strong/medium/weak) on every piece of evidence and a source link
              beneath. No &ldquo;this patent is used by Company X&rdquo; claims.
              Only patterns you can verify.
            </p>
          </div>

          {/* Card 3 — Trend Narratives */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            <div className="mb-4">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                <svg
                  className="w-3 h-3"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
                AI-generated · Claude Sonnet
              </span>
              <p className="mt-3 text-sm text-gray-500 italic leading-relaxed line-clamp-2">
                &ldquo;Filing activity in quantum-resistant cryptography surged
                42% over the trailing 12 months, led by assignees in the US and
                Japan...&rdquo;
              </p>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Trend narratives, in plain English.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Filing surges and assignee movement explained by Claude Sonnet —
              the model that follows structured-JSON instructions reliably.
              Every narrative cites the underlying patents. Refreshed as new
              filings drop.
            </p>
          </div>

          {/* Card 4 — Topics & Alerts */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
            <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs font-mono text-gray-600 space-y-1">
              <div>
                Topic:{" "}
                <span className="text-primary-700 font-semibold">G06F</span>
              </div>
              <div>
                Mode:{" "}
                <span className="text-primary-700">
                  weekly_digest + instant_alert
                </span>
              </div>
              <div>
                Threshold: <span className="text-primary-700">≥ 60</span>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Your topics. Briefed weekly. Alerted instantly.
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Subscribe to topics by CPC class, keyword, or assignee — with
              optional opportunity-score thresholds. Get instant alerts on
              high-priority matches and a Sonnet-written briefing every Sunday
              morning.
            </p>
          </div>
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
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-3">
                For patent attorneys & law firms
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
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-3">
                For corporate IP teams
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                Monitor your CPC areas for filing surges, family expansions, and
                expiry opportunities. Track usage signals showing how your prior
                art shows up in newer filings — with evidence tiers, not claims.
              </p>
              <p className="text-xs text-gray-400">
                <em className="not-italic text-gray-500">Tracks:</em> competitor
                filings · expiry windows · usage signals
              </p>
            </div>

            {/* Founders */}
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-3">
                For founders & investors
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
          Patent Pulse calibrates uncertainty. We label every estimate. We cite
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
              Patent Pulse · Evidence-backed patent intelligence · Verify with
              official registers.
            </p>
            <p>&copy; 2026</p>
          </div>
        </div>
      </footer>
    </>
  );
}
