import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service — Invention Index 8",
};

export default function TermsPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-[var(--text-primary)]">
      <h1 className="text-2xl font-bold mb-6">Terms of Service</h1>
      <p className="text-sm text-[var(--text-muted)] mb-8">Last updated: June 2026</p>

      <section className="space-y-6 text-[var(--text-secondary)] leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">1. Service description</h2>
          <p>Invention Index 8 is a patent intelligence platform. We aggregate and analyze publicly available patent data from USPTO, EPO, WIPO, and other patent offices. We provide AI-powered summaries, trend analysis, and opportunity identification.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">2. Not legal or financial advice</h2>
          <p>Invention Index 8 provides research intelligence only. Nothing on this platform constitutes legal advice, financial advice, or investment advice. Patent expiry status is estimated unless confirmed. Always verify with official patent office registers before relying on any expiry or legal status information.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">3. AI-generated content</h2>
          <p>Patent summaries, opportunity narratives, trend analyses, and other content labeled as &ldquo;AI-generated&rdquo; are produced by large language models. They may contain errors, omissions, or inaccuracies. Confidence levels are displayed where applicable. Do not rely on AI-generated content for critical decisions without independent verification.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">4. Subscription and billing</h2>
          <p>Paid subscriptions (Basic, Lifetime, Enterprise) are processed through Stripe. By subscribing, you agree to Stripe&rsquo;s terms of service. Subscription fees are non-refundable except as stated in our <a href="/refund" className="text-[var(--accent)] underline">Refund Policy</a>.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">5. Cancellation</h2>
          <p>You may cancel your subscription at any time via the Stripe Customer Portal (accessible from /account/billing). Cancellation takes effect at the end of your current billing period. You retain access until then. No prorated refunds for partial periods.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">6. Limitation of liability</h2>
          <p>Invention Index 8 is provided &ldquo;as is&rdquo; without warranty of any kind. We are not liable for any damages arising from use of the platform, including but not limited to decisions made based on patent data, AI analysis, or expiry estimates.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">7. Changes</h2>
          <p>We may update these terms from time to time. Material changes will be communicated via email to active subscribers.</p>
        </div>
      </section>
    </div>
  );
}
