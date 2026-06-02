"use client";

import type { LegalStatusConfidence } from "@/lib/types";

interface LegalConfidenceBadgeProps {
  confidence: LegalStatusConfidence | null | undefined;
  legalStatus?: string | null;
}

/**
 * Indicates whether ``legal_status`` came from a confirmed PAIR/INPADOC
 * lookup ("confirmed") or a date-based heuristic ("estimated").
 *
 * Phase 1 default for backfilled data is ``estimated``; the Phase 0
 * legal-status pipeline lifts rows to ``confirmed`` once it has a real
 * source.
 */
export function LegalConfidenceBadge({
  confidence,
  legalStatus,
}: LegalConfidenceBadgeProps) {
  const conf = confidence || "estimated";
  const isConfirmed = conf === "confirmed";

  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium " +
        (isConfirmed
          ? "bg-[var(--accent-muted)] text-[var(--accent)]"
          : "bg-gray-100 text-gray-600 border border-dashed border-[var(--border-default)]")
      }
      title={
        isConfirmed
          ? `Legal status confirmed via official source${
              legalStatus ? `: ${legalStatus}` : ""
            }`
          : `Legal status is a date-based estimate${
              legalStatus ? ` (${legalStatus})` : ""
            } — verify before relying on it`
      }
    >
      <span
        className={
          "h-1.5 w-1.5 rounded-full " +
          (isConfirmed ? "bg-blue-500" : "bg-gray-400")
        }
      />
      {isConfirmed ? "Confirmed" : "Estimated"}
    </span>
  );
}
