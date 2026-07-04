import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — Invention Index 8",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-[var(--text-primary)]">
      <h1 className="text-2xl font-bold mb-6">Privacy Policy</h1>
      <p className="text-sm text-[var(--text-muted)] mb-8">Last updated: June 2026</p>

      <section className="space-y-6 text-[var(--text-secondary)] leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">1. What we collect</h2>
          <p>We collect your email address when you sign in via magic link. We store your topic subscriptions, followed companies, and saved patents. We do not use tracking cookies, analytics scripts, or advertising pixels.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">2. Data processors</h2>
          <p>We use these third-party services to operate Invention Index 8:</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li><strong>Stripe</strong> — payment processing. Stripe collects your payment method and billing address. We never see your full card number.</li>
            <li><strong>Resend</strong> — transactional email delivery (magic links, weekly briefings).</li>
            <li><strong>DeepSeek</strong> — AI-powered patent analysis.</li>
            <li><strong>Google BigQuery</strong> — patent data retrieval from public datasets.</li>
            <li><strong>EPO OPS</strong> and <strong>USPTO</strong> — patent office data retrieval.</li>
          </ul>
          <p className="mt-2">No patent data you view is shared with these processors beyond what is necessary to deliver the service.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">3. Your rights (GDPR)</h2>
          <p>You may request a copy of your data, correct inaccuracies, or delete your account at any time. Use the account deletion endpoint in your account settings, or email us.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">4. Data retention</h2>
          <p>We retain your account data until you delete your account. Patent data is retained indefinitely as public records. Email delivery records are anonymized on account deletion.</p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">5. Contact</h2>
          <p>Email andy@web3r.tech for privacy-related requests.</p>
        </div>
      </section>
    </div>
  );
}
