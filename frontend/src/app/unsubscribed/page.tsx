"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function Content() {
  const searchParams = useSearchParams();
  const theme = searchParams.get("theme") || "this topic";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 max-w-md w-full text-center space-y-4">
        <h1 className="text-xl font-semibold text-gray-900">Unsubscribed</h1>
        <p className="text-gray-600">
          You&apos;ve been unsubscribed from <strong>{theme}</strong>. You can
          resubscribe anytime from your account page.
        </p>
        <Link
          href="/account"
          className="inline-block text-sm text-blue-600 hover:underline"
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
