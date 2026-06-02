"use client";

import { Button } from "@/components/ui/Button";

interface ErrorDisplayProps {
  error: Error | undefined;
  onRetry?: () => void;
  title?: string;
}

export function ErrorDisplay({
  error,
  onRetry,
  title = "Something went wrong",
}: ErrorDisplayProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center min-h-[200px]">
      <div className="rounded-lg border border-[var(--expiry-lapsed-confirmed)]/30 bg-[var(--expiry-lapsed-confirmed)]/10 p-6 max-w-md w-full">
        <h2 className="text-lg font-semibold text-[var(--expiry-lapsed-confirmed)] mb-2">{title}</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-4">
          {error?.message || "An unexpected error occurred. Please try again."}
        </p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm">
            Retry
          </Button>
        )}
      </div>
    </div>
  );
}
