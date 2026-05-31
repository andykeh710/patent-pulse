import type { Metadata } from "next";
import { BRAND, EMAIL } from "@/lib/brand";

export const metadata: Metadata = {
  title: `Terms of Service`,
  description: `Terms of Service for ${BRAND.name}.`,
};

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
      <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-lg p-4 mb-8">
        This is placeholder content — counsel review pending before public
        launch.
      </p>

      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        Terms of Service
      </h1>

      <div className="prose prose-gray max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            1. Acceptance of Terms
          </h2>
          <p className="text-gray-600 leading-relaxed">
            By accessing or using {BRAND.name} (&ldquo;the Service&rdquo;), you
            agree to be bound by these Terms of Service. If you do not agree,
            do not use the Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            2. Description of Service
          </h2>
          <p className="text-gray-600 leading-relaxed">
            {BRAND.name} is a patent intelligence tool that surfaces patent
            filing trends, expiry estimates, usage signals, and AI-generated
            narratives from publicly available patent office data. It is not
            legal advice.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            3. User Accounts
          </h2>
          <p className="text-gray-600 leading-relaxed mb-2">
            Accounts are created via magic-link authentication. You are
            responsible for maintaining the security of the email account used
            for sign-in.
          </p>
          <p className="text-gray-600 leading-relaxed">
            You may delete your account at any time from the account page.
            Deletion cascades to your subscriptions and anonymizes associated
            data.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            4. Paid Subscriptions
          </h2>
          <p className="text-gray-600 leading-relaxed mb-2">
            Paid subscriptions are billed through Stripe. By subscribing, you
            authorize Stripe to charge your payment method according to the
            pricing displayed at checkout.
          </p>
          <p className="text-gray-600 leading-relaxed">
            Refunds are handled on a case-by-case basis. Contact support for
            refund requests.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            5. Acceptable Use
          </h2>
          <p className="text-gray-600 leading-relaxed">
            You agree not to: (a) use the Service for automated scraping or bulk
            data resale; (b) attempt to circumvent tier-based quotas or rate
            limits; (c) use the Service in violation of applicable laws.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            6. Intellectual Property
          </h2>
          <p className="text-gray-600 leading-relaxed mb-2">
            Your account data (topic subscriptions, alert preferences, exports)
            is yours. Aggregated patent data surfaced by the Service originates
            from public patent office feeds and is not claimed as proprietary.
          </p>
          <p className="text-gray-600 leading-relaxed">
            The Service&rsquo;s software, branding, and AI-generated content
            structure are proprietary.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            7. Disclaimer of Warranty
          </h2>
          <p className="text-gray-600 leading-relaxed">
            THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTY OF ANY
            KIND. {BRAND.name.toUpperCase()} IS NOT LEGAL ADVICE. EXPIRY
            ESTIMATES ARE ESTIMATES — NOT GUARANTEES. VERIFY ALL INFORMATION
            WITH OFFICIAL PATENT REGISTERS BEFORE MAKING DECISIONS.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            8. Limitation of Liability
          </h2>
          <p className="text-gray-600 leading-relaxed">
            To the fullest extent permitted by law, {BRAND.name} shall not be
            liable for any indirect, incidental, special, or consequential
            damages arising from your use of the Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            9. Governing Law
          </h2>
          <p className="text-gray-600 leading-relaxed">
            [Jurisdiction TBD — counsel review required.] These Terms shall be
            governed by the laws of the jurisdiction in which the operating
            entity is registered.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            10. Changes to Terms
          </h2>
          <p className="text-gray-600 leading-relaxed">
            We may update these Terms from time to time. Material changes will
            be communicated via email. Continued use after changes constitutes
            acceptance.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            11. Contact
          </h2>
          <p className="text-gray-600 leading-relaxed">
            Questions about these Terms? Email{" "}
            <a
              href={`mailto:${EMAIL.support}`}
              className="text-primary-600 hover:text-primary-700 underline"
            >
              {EMAIL.support}
            </a>
          </p>
        </section>

        <div className="border-t border-gray-200 pt-8 mt-8">
          <p className="text-xs text-gray-400">
            Last updated: May 2026. This is placeholder content pending counsel
            review.
          </p>
        </div>
      </div>
    </div>
  );
}
