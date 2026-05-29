"use client";

import { ErrorDisplay } from "@/components/ErrorDisplay";
import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Page error:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <ErrorDisplay error={error} onRetry={reset} title="Page Error" />
    </div>
  );
}
