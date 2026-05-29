import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact — Patent Pulse",
  description: "Get in touch with Patent Pulse.",
};

export default function ContactPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Contact</h1>

      <p className="text-lg text-gray-600 leading-relaxed mb-8">
        Questions, feedback, or support requests? Send us an email and
        we&rsquo;ll get back to you within 1-2 business days.
      </p>

      <a
        href="mailto:support@patentpulse.dev"
        className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-primary-600 text-white font-semibold hover:bg-primary-700 transition-colors"
      >
        Email support@patentpulse.dev
      </a>

      <div className="mt-16 border-t border-gray-200 pt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Other contacts
        </h2>
        <div className="space-y-3 text-sm text-gray-600">
          <p>
            Privacy inquiries:{" "}
            <a
              href="mailto:privacy@patentpulse.dev"
              className="text-primary-600 hover:text-primary-700 underline"
            >
              privacy@patentpulse.dev
            </a>
          </p>
          <p>
            Legal:{" "}
            <a
              href="mailto:legal@patentpulse.dev"
              className="text-primary-600 hover:text-primary-700 underline"
            >
              legal@patentpulse.dev
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
