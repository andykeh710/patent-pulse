"use client";

import { Button } from "./Button";

interface ErrorStateProps {
  message?: string;
  detail?: string;
  onRetry?: () => void;
  title?: string;
}

export function ErrorState({
  message = "Something went wrong loading this data.",
  detail,
  onRetry,
  title = "Error",
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 bg-[var(--bg-glass)] rounded-lg border border-[var(--border-subtle)]">
      <svg
        className="w-10 h-10 text-[var(--expiry-lapsed-confirmed)] mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h3 className="text-lg font-semibold text-[var(--expiry-lapsed-confirmed)] mb-1">
        {title}
      </h3>
      <p className="text-sm text-[var(--text-secondary)] text-center max-w-md mb-1">
        {message}
      </p>
      {detail && (
        <p className="text-xs text-[var(--text-muted)] text-center max-w-md mb-4">
          {detail}
        </p>
      )}
      {onRetry && (
        <Button onClick={onRetry} variant="outline" size="sm">
          Retry
        </Button>
      )}
    </div>
  );
}
