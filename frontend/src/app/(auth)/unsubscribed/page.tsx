"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function Content() {
  const searchParams = useSearchParams();
  const theme = searchParams.get("theme") || "this topic";

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
      <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-8 max-w-md w-full text-center space-y-4">
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Unsubscribed</h1>
        <p className="text-[var(--text-secondary)]">
          You&apos;ve been unsubscribed from <strong>{theme}</strong>. You can
          resubscribe anytime from your account page.
        </p>
        <Link
          href="/account"
          className="inline-block text-sm text-[var(--accent)] hover:underline"
        >
          Go to Account
        </Link>
      </div>
    </div>
  );
}

export default function UnsubscribedPage() {
  return (
    <Suspense>
      <Content />
    </Suspense>
  );
}
