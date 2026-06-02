"use client";

import { getOpportunityBgClass, getOpportunityLabel } from "@/lib/utils";

interface OpportunityScoreBadgeProps {
  score: number | null;
  showLabel?: boolean;
  size?: "sm" | "md";
}

/**
 * Visual badge for the rules-based opportunity_score (0..100 scale).
 * Distinct from ScoreBadge (which renders the legacy 0..1 interesting_score).
 */
export function OpportunityScoreBadge({
  score,
  showLabel = true,
  size = "sm",
}: OpportunityScoreBadgeProps) {
  if (score === null) {
    return (
      <span
        className={`inline-flex items-center rounded-full font-medium bg-gray-100 text-[var(--text-muted)] ${
          size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"
        }`}
        title="Opportunity score not yet computed"
      >
        — opp
      </span>
    );
  }

  const label = getOpportunityLabel(score);
  const bg = getOpportunityBgClass(score);
  const rounded = Math.round(score);

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${bg} ${
        size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs"
      }`}
      title={`Opportunity score: ${rounded}/100 (${label})`}
    >
      <span className="font-bold mr-1">{rounded}</span>
      <span className="opacity-75">opp</span>
      {showLabel && <span className="ml-1.5 opacity-75">· {label}</span>}
    </span>
  );
}
