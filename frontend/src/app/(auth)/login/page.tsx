"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { BRAND } from "@/lib/brand";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // null = unknown; true = real email delivery active; false = dev/preview
  // mode (no email actually sent — magic link is in the backend logs).
  const [emailDeliveryActive, setEmailDeliveryActive] = useState<boolean | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authApi.requestLink({ email });
      // Detect whether this environment actually delivers email via Resend.
      // In dev/preview mode (or when Resend is unauthorized/disabled), no
      // email is sent — we must not claim one was.
      try {
        const res = await fetch("/health");
        const health = await res.json();
        setEmailDeliveryActive(health?.resend === "ok");
      } catch {
        setEmailDeliveryActive(null);
      }
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    const realEmailSent = emailDeliveryActive === true;
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
        <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-8 max-w-md w-full text-center space-y-4">
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">
              {realEmailSent ? "Check your email" : "Dev mode — check the backend logs"}
            </h1>
            {realEmailSent ? (
              <p className="text-[var(--text-secondary)]">
                We sent a magic link to <strong>{email}</strong>. Click the link
                to sign in. It expires in 15 minutes.
              </p>
            ) : (
              <div className="text-[var(--text-secondary)] space-y-2 text-sm">
                <p>
                  This environment does <strong>not</strong> send real emails. A
                  sign-in link for <strong>{email}</strong> was printed to the
                  backend logs.
                </p>
                <p className="text-[var(--text-muted)]">
                  Look for a line beginning with{" "}
                  <code className="px-1 py-0.5 rounded bg-[var(--bg-glass)] text-[var(--text-primary)]">
                    DEV MAGIC LINK:
                  </code>{" "}
                  and open that URL to sign in. It expires in 15 minutes.
                </p>
              </div>
            )}
            <p className="text-xs text-[var(--text-muted)]">
              Wrong address?{" "}
              <button
                onClick={() => setSubmitted(false)}
                className="text-[var(--accent)] hover:underline"
              >
                try again
              </button>
              .
            </p>
            <Link href="/" className="text-sm text-[var(--accent)] hover:underline block">
              Back to {BRAND.name}
            </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
      <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-8 max-w-md w-full space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">Sign in</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Enter your email to receive a magic link.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-[var(--bg-glass)] border border-[var(--border-default)] rounded-[var(--radius-md)] px-4 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            autoFocus
          />

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full bg-[var(--accent)] text-white rounded-[var(--radius-md)] py-2 text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-50 transition-colors"
          >
            {loading ? "Sending…" : "Send magic link"}
          </button>

          {error && <p className="text-red-400 text-xs">{error}</p>}
        </form>

        <Link href="/" className="text-sm text-[var(--accent)] hover:underline block text-center">
          Back to {BRAND.name}
        </Link>
      </div>
    </div>
  );
}
