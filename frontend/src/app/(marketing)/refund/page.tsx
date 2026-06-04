import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Refund Policy — Invention Index 8",
};

export default function RefundPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-[var(--text-primary)]">
      <h1 className="text-2xl font-bold mb-6">Refund Policy</h1>
      <p className="text-sm text-[var(--text-muted)] mb-8">Last updated: June 2026</p>

      <section className="space-y-6 text-[var(--text-secondary)] leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">1. Basic subscription ($8/year)</h2>
          <p>You may request a full refund within 7 days of your initial purchase. After 7 days, subscriptions are non-refundable. Refund requests after 7 days are evaluated case-by-case at our discretion. Contact andy@web3r.tech.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">2. Lifetime ($108 one-time)</h2>
          <p>You may request a full refund within 14 days of purchase. After 14 days, Lifetime purchases are non-refundable.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">3. Enterprise ($1,000/year)</h2>
          <p>Enterprise subscriptions include a 30-day money-back guarantee. If you&rsquo;re not satisfied within the first 30 days, contact us for a full refund. After 30 days, you may cancel at any time with access continuing until the end of the billing period. No prorated refunds.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">4. How to request a refund</h2>
          <p>Email andy@web3r.tech with your account email and the reason for your refund request. Refunds are processed through Stripe and typically appear on your statement within 5-10 business days.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">5. Chargebacks</h2>
          <p>If you initiate a chargeback through your bank or card issuer instead of contacting us for a refund, your account will be immediately suspended pending resolution. Please contact us first — we&rsquo;ll make it right.</p>
        </div>
      </section>
    </div>
  );
}
