"use client";

import type { OpportunityBreakdown as OpportunityBreakdownT } from "@/lib/types";
import { humanizeTag } from "@/lib/utils";

interface OpportunityBreakdownProps {
  breakdown: OpportunityBreakdownT | null | undefined;
  /** Display the top N components, ordered by absolute contribution. */
  topN?: number;
}

/**
 * Renders the per-component contribution chart that backs the headline
 * opportunity_score badge. Each row shows the sub_score (0..1) bar and the
 * weighted contribution percentage. Components are ordered by contribution
 * descending so the dominant drivers are at the top.
 */
export function OpportunityBreakdown({
  breakdown,
  topN,
}: OpportunityBreakdownProps) {
  if (!breakdown) {
    return (
      <div className="rounded-md border border-dashed border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-muted)]">
        Opportunity score not yet computed.
      </div>
    );
  }

  const entries = Object.entries(breakdown.components)
    .map(([name, c]) => ({ name, ...c }))
    .sort((a, b) => b.contribution - a.contribution);

  const visible = topN ? entries.slice(0, topN) : entries;
  const totalContribution = entries.reduce((s, e) => s + e.contribution, 0);

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h4 className="text-sm font-semibold text-[var(--text-primary)]">
          Opportunity score breakdown
        </h4>
        <span className="text-xs text-[var(--text-muted)]">
          v{breakdown.version} · {Math.round(breakdown.score)}/100
        </span>
      </div>

      <div className="space-y-1.5">
        {visible.map((c) => {
          const subPct = Math.round(c.sub_score * 100);
          const contribPct = Math.round((c.contribution / Math.max(totalContribution, 0.0001)) * 100);
          return (
            <div key={c.name} className="text-xs">
              <div className="mb-0.5 flex items-center justify-between">
                <span className="font-medium text-[var(--text-secondary)]">
                  {humanizeTag(c.name)}
                </span>
                <span className="tabular-nums text-[var(--text-muted)]">
                  {subPct}% · weight {Math.round(c.weight * 100)}% ·{" "}
                  <span className="font-semibold text-[var(--text-secondary)]">
                    {contribPct}% of score
                  </span>
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded bg-[var(--bg-elevated)]">
                <div
                  className={
                    "h-full rounded " +
                    (c.sub_score >= 0.7
                      ? "bg-[var(--score-high)]"
                      : c.sub_score >= 0.4
                        ? "bg-[var(--score-medium)]"
                        : "bg-[var(--text-muted)]")
                  }
                  style={{ width: `${subPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {topN && entries.length > visible.length && (
        <div className="text-xs text-[var(--text-muted)]">
          + {entries.length - visible.length} more components
        </div>
      )}
    </div>
  );
}
