"use client";

import { humanizeTag } from "@/lib/utils";

interface RiskFlagsBadgeProps {
  flags: string[] | null | undefined;
  /** When true, render only the first flag + "+N" overflow chip. */
  collapse?: boolean;
}

/** Severity bucket per risk-flag value, drives badge color. */
function severity(flag: string): "high" | "med" | "low" {
  if (
    flag === "active_family_risk" ||
    flag === "needs_legal_review" ||
    flag === "unknown_legal_status"
  ) {
    return "high";
  }
  if (flag === "regulatory_dependency" || flag === "crowded_space") {
    return "med";
  }
  return "low";
}

function severityClass(s: "high" | "med" | "low"): string {
  if (s === "high") return "bg-red-100 text-red-700 border border-red-300";
  if (s === "med") return "bg-[var(--score-medium-bg)] text-[var(--score-medium)]";
  return "bg-gray-100 text-gray-700";
}

export function RiskFlagsBadge({ flags, collapse = false }: RiskFlagsBadgeProps) {
  if (!flags || flags.length === 0) return null;

  const items = collapse ? flags.slice(0, 1) : flags;
  const remainder = collapse ? flags.length - items.length : 0;

  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((flag) => {
        const s = severity(flag);
        return (
          <span
            key={flag}
            className={
              "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium " +
              severityClass(s)
            }
            title={`Risk flag: ${flag}`}
          >
            {s === "high" && <span aria-hidden>⚠</span>}
            {humanizeTag(flag)}
          </span>
        );
      })}
      {remainder > 0 && (
        <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
          +{remainder} more
        </span>
      )}
    </div>
  );
}
