"use client";

import { useState } from "react";
import { useFreshness } from "@/hooks/useFreshness";

/**
 * FreshnessBanner — Tier-3 hard-banner only.
 *
 * Only renders for TRUE full-source failures (all sources down).
 * Dismissible and remembered per session (doesn't reappear until reload).
 *
 * Normal staleness, source lag, and amber warnings are handled by the
 * always-on FreshnessChip in the PageHeader. This is the nuclear option.
 */

interface FreshnessBannerProps {
  /** Which indicators to monitor. Defaults to all. */
  show?: ("patents" | "summaries" | "trends" | "ai_runs")[];
  className?: string;
}

export function FreshnessBanner({
  show = ["patents", "summaries", "trends", "ai_runs"],
  className = "",
}: FreshnessBannerProps) {
  const { data, error } = useFreshness();
  const [dismissed, setDismissed] = useState(false);

  if (error || !data || dismissed) return null;

  // Only render for full-source failure — not partial, not stale, not success-no-data
  const isTotalFailure =
    data.last_ingestion_status === "failed" || data.last_ingestion_status === "degraded";
  if (!isTotalFailure) return null;

  // Only show if the relevant sources are affected
  const monitorsPatents = show.includes("patents");
  if (!monitorsPatents) return null;

  return (
    <div className={className}>
      <div
        role="alert"
        className="flex items-start gap-3 rounded-[var(--radius-md)] border border-[var(--danger)]/40 bg-[var(--danger-bg)] px-4 py-3 text-xs"
      >
        <svg
          className="w-4 h-4 mt-0.5 shrink-0"
          style={{ color: "var(--danger)" }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>

        <div className="flex-1 min-w-0" style={{ color: "var(--danger)" }}>
          <p className="font-semibold">
            Patent data sources are currently unavailable.
          </p>
          <p className="mt-0.5 opacity-80">
            {data.last_ingestion_error ||
              "USPTO data APIs are unreachable."}{" "}
            Patent data and intelligence may be out of date. Verify against
            official patent registers before relying on this data.
          </p>
        </div>

        <button
          onClick={() => setDismissed(true)}
          className="shrink-0 p-1 rounded hover:bg-[var(--danger)]/20 transition-colors"
          style={{ color: "var(--danger)" }}
          aria-label="Dismiss"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
