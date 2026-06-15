import Link from "next/link";
import type { Metadata } from "next";
import { PricingCard } from "../PricingCard";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Free, Basic ($8/yr), Lifetime ($108 once), and Enterprise ($1,000/yr) plans.",
};

// ─── Helpers ───

interface FeatureRow {
  feature: string;
  free: string;
  basic: string;
  lifetime: string;
  enterprise: string;
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <details className="group border-b border-[var(--border-subtle)] pb-6">
      <summary className="flex items-center justify-between cursor-pointer marker:content-none">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] pr-4">{q}</h3>
        <svg
          className="w-5 h-5 text-[var(--text-muted)] flex-shrink-0 group-open:rotate-180 transition-transform"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </summary>
      <p className="mt-3 text-sm text-[var(--text-secondary)] leading-relaxed">{a}</p>
    </details>
  );
}

// ─── Feature matrix data ───

const MATRIX: FeatureRow[] = [
  {
    feature: "Price",
    free: "$0",
    basic: "$8 / year",
    lifetime: "$108 once",
    enterprise: "$1,000 / year",
  },
  {
    feature: "Topics",
    free: "1",
    basic: "Unlimited",
    lifetime: "Unlimited",
    enterprise: "Unlimited",
  },
  {
    feature: "Alerts",
    free: "5 / week",
    basic: "Unlimited",
    lifetime: "Unlimited",
    enterprise: "Unlimited",
  },
  {
    feature: "Weekly digest",
    free: "✓",
    basic: "✓",
    lifetime: "✓",
    enterprise: "✓",
  },
  {
    feature: "CSV export",
    free: "—",
    basic: "✓",
    lifetime: "✓",
    enterprise: "✓",
  },
  {
    feature: "PDF reports",
    free: "—",
    basic: "—",
    lifetime: "✓",
    enterprise: "✓",
  },
  {
    feature: "API access",
    free: "—",
    basic: "—",
    lifetime: "—",
    enterprise: "✓ (300/min)",
  },
  {
    feature: "Admin tools",
    free: "—",
    basic: "—",
    lifetime: "—",
    enterprise: "✓",
  },
  {
    feature: "Support",
    free: "Community",
    basic: "Email",
    lifetime: "Email",
    enterprise: "Priority email",
  },
  {
    feature: "Billing",
    free: "—",
    basic: "Annual",
    lifetime: "One-time",
    enterprise: "Annual",
  },
  {
    feature: "Auth",
    free: "Magic link",
    basic: "Magic link",
    lifetime: "Magic link",
    enterprise: "Magic link",
  },
];

interface FaqItem {
  q: string;
  a: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    q: "Can I switch tiers?",
    a: "Yes. You can upgrade or downgrade at any time from your account page. Upgrades take effect immediately; downgrades apply at the end of your current billing period.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Cancel from your account page. No penalties or fees. Your subscription remains active until the end of your current billing period.",
  },
  {
    q: "What is your refund policy?",
    a: "Refunds are handled on a case-by-case basis. Contact support. For annual plans, prorated refunds may be available within the first 30 days. Lifetime purchases are non-refundable after 30 days.",
  },
  {
    q: "What does Lifetime mean?",
    a: `One payment of $108 gives you lifetime access to the Lifetime features while Invention Index 8 is actively maintained. It is not a contractual guarantee of perpetual service — it means no recurring charges for as long as the product exists.`,
  },
  {
    q: "Do you charge tax / VAT?",
    a: "Tax handling depends on your location and is applied by Stripe at checkout. Prices shown are exclusive of applicable taxes.",
  },
  {
    q: "Do you provide invoices?",
    a: "Invoice PDFs are available through the Stripe billing portal accessible from your account page. Receipts are emailed automatically at checkout.",
  },
  {
    q: "What happens to my data if I cancel?",
    a: "Your data is retained according to our privacy policy. You can export your data (CSV or PDF where applicable) or delete your account at any time from the account page.",
  },
  {
    q: "How do API keys work?",
    a: "Enterprise-tier users can create and manage API keys from the account page. Keys are SHA-256 hashed at rest. You can create, list, and revoke keys at any time. Rate limit: 300 requests/minute per key.",
  },
  {
    q: "Can I delete my account?",
    a: "Yes. Use the Delete my account button on the account page. This cascade-deletes your subscriptions and anonymizes your data. See our privacy policy for details.",
  },
];

// ─── Page ───

export default function PricingPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-3xl sm:text-4xl font-bold text-[var(--text-primary)] mb-4">
          Pricing
        </h1>
        <p className="text-lg text-[var(--text-secondary)]">
          Start free. Upgrade when you need more.
        </p>
      </div>

      {/* ─── 4 cards ─── */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
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

      {/* ─── Feature matrix ─── */}
      <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-xl overflow-hidden mb-16">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--bg-base)] border-b border-[var(--border-subtle)]">
                <th className="text-left p-4 font-semibold text-[var(--text-primary)]">
                  Feature
                </th>
                <th className="p-4 text-center font-semibold text-[var(--text-primary)]">
                  Free
                </th>
                <th className="p-4 text-center font-semibold text-[var(--text-primary)]">
                  Basic
                </th>
                <th className="p-4 text-center font-semibold text-[var(--text-primary)] bg-bg-[var(--bg-elevated)]">
                  Lifetime
                </th>
                <th className="p-4 text-center font-semibold text-[var(--text-primary)]">
                  Enterprise
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {MATRIX.map((row, i) => (
                <tr key={row.feature} className={i % 2 === 0 ? "" : "bg-gray-50/50"}>
                  <td className="p-4 text-[var(--text-secondary)] font-medium">
                    {row.feature}
                  </td>
                  <td className="p-4 text-center text-[var(--text-secondary)]">{row.free}</td>
                  <td className="p-4 text-center text-[var(--text-secondary)]">{row.basic}</td>
                  <td className="p-4 text-center text-[var(--text-secondary)] bg-bg-[var(--bg-elevated)]/50">
                    {row.lifetime}
                  </td>
                  <td className="p-4 text-center text-[var(--text-secondary)]">
                    {row.enterprise}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── FAQ ─── */}
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-8">
          Frequently asked questions
        </h2>
        <div className="space-y-6">
          {FAQ_ITEMS.map((item) => (
            <Faq key={item.q} q={item.q} a={item.a} />
          ))}
        </div>
      </div>

      {/* ─── Bottom CTA ─── */}
      <div className="text-center mt-16 pt-12 border-t border-[var(--border-subtle)]">
        <p className="text-[var(--text-secondary)] mb-4">Ready to get started?</p>
        <Link
          href="/login"
          className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent)] transition-colors"
        >
          Get started free
        </Link>
        <p className="mt-3 text-sm text-[var(--text-muted)]">No credit card required</p>
      </div>
    </div>
  );
}
