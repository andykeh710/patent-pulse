"use client";

import { Skeleton } from "./Skeleton";

// -- Types ----------------------------------------------------------------

interface LoadingStateProps {
  /** What kind of content is loading (affects skeleton shape) */
  variant?: "card" | "table" | "detail" | "grid";
  /** Number of skeleton items to show */
  count?: number;
  className?: string;
}

// -- Component -------------------------------------------------------------

export function LoadingState({
  variant = "card",
  count = 3,
  className = "",
}: LoadingStateProps) {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <LoadingSkeleton key={i} variant={variant} />
      ))}
      <span className="sr-only">Loading content...</span>
    </div>
  );
}

// -- Skeleton variants -----------------------------------------------------

function LoadingSkeleton({ variant }: { variant: LoadingStateProps["variant"] }) {
  switch (variant) {
    case "card":
      return (
        <div className="bg-[var(--bg-glass)] rounded-lg border border-[var(--border-subtle)] p-4">
          <div className="flex items-center gap-2 mb-3">
            <Skeleton className="h-4 w-16 rounded-full" />
            <Skeleton className="h-3 w-20 rounded" />
          </div>
          <Skeleton className="h-5 w-3/4 mb-2" />
          <Skeleton className="h-4 w-full mb-1" />
          <Skeleton className="h-4 w-2/3 mb-3" />
          <div className="flex gap-3">
            <Skeleton className="h-8 w-24 rounded" />
            <Skeleton className="h-8 w-20 rounded" />
          </div>
        </div>
      );

    case "table":
      return <Skeleton className="h-16 w-full rounded-lg" />;

    case "detail":
      return (
        <div className="space-y-4">
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-24 w-full" />
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
          </div>
        </div>
      );

    case "grid":
      return <Skeleton className="h-48 w-full rounded-lg" />;

    default:
      return <Skeleton className="h-20 w-full rounded-lg" />;
  }
}
