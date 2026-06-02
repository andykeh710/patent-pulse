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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authApi.requestLink({ email });
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
        <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-8 max-w-md w-full text-center space-y-4">
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">Check your email</h1>
            <p className="text-[var(--text-secondary)]">
              We sent a magic link to <strong>{email}</strong>. Click the link
              to sign in. It expires in 15 minutes.
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              Didn&apos;t get it? Check spam or{" "}
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
