import type { Metadata } from "next";
import { BRAND, EMAIL } from "@/lib/brand";

export const metadata: Metadata = {
  title: `Privacy Policy`,
  description: `Privacy Policy for ${BRAND.name}.`,
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
      <p className="text-sm text-amber-600 bg-[var(--score-medium-bg)] border border-[var(--score-medium)]/30 rounded-lg p-4 mb-8">
        This is placeholder content — counsel review pending before public
        launch.
      </p>

      <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-8">
        Privacy Policy
      </h1>

      <div className="prose prose-gray max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            What we collect
          </h2>
          <ul className="list-disc pl-5 space-y-2 text-[var(--text-secondary)]">
            <li>
              <strong>Email address</strong> — used for magic-link sign-in and
              alert delivery.
            </li>
            <li>
              <strong>Magic-link sign-in metadata</strong> — token creation and
              verification timestamps.
            </li>
            <li>
              <strong>Topic subscriptions</strong> — CPC classes, keywords, and
              alert preferences you configure.
            </li>
            <li>
              <strong>Stripe customer ID</strong> — for paid subscription
              management. Full payment details are handled by Stripe and never
              touch our servers.
            </li>
            <li>
              <strong>Usage logs</strong> — API request metadata for rate
              limiting and abuse prevention.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            What we don&rsquo;t collect
          </h2>
          <ul className="list-disc pl-5 space-y-2 text-[var(--text-secondary)]">
            <li>No third-party tracking pixels.</li>
            <li>No analytics SDKs by default.</li>
            <li>No browsing history or cross-site tracking.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            How we use your data
          </h2>
          <p className="text-[var(--text-secondary)] leading-relaxed">
            Your data is used solely to deliver the Service: sending alerts and
            weekly digests based on your topic subscriptions, managing your
            billing, and providing support.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            Third-party processors
          </h2>
          <p className="text-[var(--text-secondary)] leading-relaxed mb-3">
            We use the following services to operate {BRAND.name}:
          </p>
          <ul className="list-disc pl-5 space-y-2 text-[var(--text-secondary)]">
            <li>
              <strong>Stripe</strong> — payment processing. Stripe receives
              your email and payment method. See{" "}
              <a
                href="https://stripe.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] hover:text-[var(--accent)] underline"
              >
                Stripe&rsquo;s privacy policy
              </a>
              .
            </li>
            <li>
              <strong>Resend</strong> — email delivery for magic links, alerts,
              and digests. Resend receives your email address for delivery.
              See{" "}
              <a
                href="https://resend.com/legal/privacy-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] hover:text-[var(--accent)] underline"
              >
                Resend&rsquo;s privacy policy
              </a>
              .
            </li>
            <li>
              <strong>Anthropic</strong> — AI narrative generation (Claude
              Sonnet). Patent data is sent to Anthropic for summarization and
              trend analysis. No personally identifiable information is
              included in AI prompts. Outputs are cached server-side.
            </li>
            <li>
              <strong>OpenAI</strong> — text embeddings for semantic search
              (text-embedding-3-small). Patent text is processed for vector
              embeddings. No PII is included.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            Data retention
          </h2>
          <p className="text-[var(--text-secondary)] leading-relaxed">
            Email delivery records are retained for audit purposes with
            user IDs anonymized upon account deletion. Account deletion
            cascades to subscriptions and magic-link tokens.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            Your rights (GDPR)
          </h2>
          <p className="text-[var(--text-secondary)] leading-relaxed mb-2">
            If you are located in the EEA or UK, you have the right to:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-[var(--text-secondary)] mb-3">
            <li>Access your data — via your account page.</li>
            <li>Delete your data — via the &ldquo;Delete my account&rdquo;
            button on the account page.</li>
            <li>Export your data — CSV and PDF exports are available depending
            on your tier.</li>
          </ul>
          <p className="text-[var(--text-secondary)] leading-relaxed">
            For GDPR inquiries, contact{" "}
            <a
              href={`mailto:${EMAIL.privacy}`}
              className="text-[var(--accent)] hover:text-[var(--accent)] underline"
            >
              {EMAIL.privacy}
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-3">
            Contact
          </h2>
          <p className="text-[var(--text-secondary)] leading-relaxed">
            Privacy questions? Email{" "}
            <a
              href={`mailto:${EMAIL.privacy}`}
              className="text-[var(--accent)] hover:text-[var(--accent)] underline"
            >
              {EMAIL.privacy}
            </a>
          </p>
        </section>

        <div className="border-t border-[var(--border-subtle)] pt-8 mt-8">
          <p className="text-xs text-[var(--text-muted)]">
            Last updated: May 2026. This is placeholder content pending counsel
            review.
          </p>
        </div>
      </div>
    </div>
  );
}
