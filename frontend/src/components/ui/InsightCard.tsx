"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { Badge } from "./Badge";
import { ConfidenceMark } from "./ConfidenceMark";
import type { ConfidenceLevel } from "./ConfidenceMark";

// -- Types ----------------------------------------------------------------

export type InsightType =
  | "signal"
  | "risk"
  | "opportunity"
  | "update"
  | "recommendation";

interface InsightAction {
  label: string;
  href?: string;
  onClick?: () => void;
}

/** Personalization context — "why you're seeing this" affordance. */
export interface InsightCardPersonalization {
  whyShown: string;
  rank?: number;
  signals?: string[];
}

interface InsightCardProps {
  type: InsightType;
  title: string;
  summary: string;
  whyItMatters?: string;
  /** Evidence backing — rendered in provenance mono style */
  evidence?: string;
  /** Confidence level — rendered with ConfidenceMark texture grammar */
  confidence?: "high" | "medium" | "low";
  timestamp?: string;
  primaryAction?: InsightAction;
  secondaryAction?: InsightAction;
  sourceIds?: string[];
  /** Personalization context (why shown for this user) */
  personalization?: InsightCardPersonalization;
  /** Source provenance for provenance footer */
  provenance?: {
    source?: string;
    docId?: string;
    confidence?: ConfidenceLevel;
    verifyUrl?: string;
  };
  children?: ReactNode;
  className?: string;
}

// -- Styling ---------------------------------------------------------------

const TYPE_STYLES: Record<
  InsightType,
  { badge: string; spine: string; bg: string }
> = {
  signal: {
    badge: "bg-[var(--accent-muted)] text-[var(--type-trend)]",
    spine: "var(--accent)",
    bg: "bg-[var(--bench-glass)]",
  },
  risk: {
    badge: "bg-[var(--warning)]/12 text-[var(--warning)]",
    spine: "var(--warning)",
    bg: "bg-[var(--bench-glass)]",
  },
  opportunity: {
    badge: "bg-[var(--bench-score-high-bg)] text-[var(--bench-score-high)]",
    spine: "var(--bench-score-high)",
    bg: "bg-[var(--bench-glass)]",
  },
  update: {
    badge: "bg-[var(--bench-ink-muted)]/12 text-[var(--bench-ink-muted)]",
    spine: "var(--bench-ink-muted)",
    bg: "bg-[var(--bench-glass)]",
  },
  recommendation: {
    badge: "bg-[var(--accent-muted)] text-[var(--bench-ink-secondary)]",
    spine: "var(--accent)",
    bg: "bg-[var(--bench-raised)]",
  },
};

const TYPE_LABELS: Record<InsightType, string> = {
  signal: "Signal",
  risk: "Risk",
  opportunity: "Opportunity",
  update: "Update",
  recommendation: "Recommendation",
};

// -- Action rendering helper -----------------------------------------------

function ActionLink({ action }: { action: InsightAction }) {
  const className =
    "text-xs font-medium text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors";
  if (action.href) {
    return (
      <Link href={action.href} className={className}>
        {action.label} →
      </Link>
    );
  }
  return (
    <button onClick={action.onClick} className={className}>
      {action.label}
    </button>
  );
}

// -- Component -------------------------------------------------------------

export function InsightCard({
  type,
  title,
  summary,
  whyItMatters,
  evidence,
  confidence,
  timestamp,
  primaryAction,
  secondaryAction,
  sourceIds,
  personalization,
  provenance,
  children,
  className = "",
}: InsightCardProps) {
  const style = TYPE_STYLES[type];

  return (
    <div
      className={`rounded-[var(--radius-md)] border border-[var(--bench-line)] ${style.bg} ${className}`}
    >
      {/* Evidence spine — 2px left rule in type color */}
      <div className="flex">
        <div
          className="w-0.5 shrink-0 rounded-l-[var(--radius-md)]"
          style={{ backgroundColor: style.spine }}
        />

        <div className="flex-1 min-w-0 p-4">
          {/* Header row: type badge + confidence + timestamp */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span
              className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${style.badge}`}
            >
              {TYPE_LABELS[type]}
            </span>
            {confidence && (
              <ConfidenceMark
                level={confidence as ConfidenceLevel}
                size="sm"
              />
            )}
            {timestamp && (
              <span className="text-[11px] text-[var(--bench-ink-muted)] ml-auto font-mono tabular-nums">
                {timestamp}
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="text-sm font-semibold text-[var(--bench-ink)] mb-1">
            {title}
          </h3>

          {/* Summary */}
          <p className="text-[13px] text-[var(--bench-ink-secondary)] mb-2 leading-relaxed">
            {summary}
          </p>

          {/* Why it matters */}
          {whyItMatters && (
            <p className="text-xs text-[var(--bench-ink-muted)] mb-2 leading-relaxed">
              Why it matters: {whyItMatters}
            </p>
          )}

          {/* Personalization — "why you're seeing this" affordance */}
          {personalization && (
            <div className="mb-2 rounded-[var(--radius-sm)] bg-[var(--bench-glass-strong)] px-3 py-2">
              <p className="text-[11px] text-[var(--bench-ink-secondary)] leading-relaxed">
                {personalization.whyShown}
              </p>
              {personalization.signals &&
                personalization.signals.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {personalization.signals.map((s, i) => (
                      <span
                        key={i}
                        className="text-[10px] text-[var(--bench-ink-muted)] bg-[var(--bench-glass)] px-1.5 py-0.5 rounded"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
            </div>
          )}

          {/* Actions */}
          {(primaryAction || secondaryAction) && (
            <div className="flex items-center gap-4 mt-2 pt-2 border-t border-[var(--bench-line)]">
              {primaryAction && <ActionLink action={primaryAction} />}
              {secondaryAction && <ActionLink action={secondaryAction} />}
            </div>
          )}

          {/* Source IDs */}
          {sourceIds && sourceIds.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {sourceIds.map((id) => (
                <Badge key={id} variant="default" size="sm">
                  {id}
                </Badge>
              ))}
            </div>
          )}

          {/* Extra content */}
          {children}
        </div>
      </div>

      {/* Provenance footer — source/evidence metadata */}
      {(evidence || provenance) && (
        <div className="px-4 pb-3 flex items-center gap-2 text-[10px] font-mono text-[var(--bench-provenance)]">
          {evidence && <span className="text-[var(--bench-ink-muted)]">{evidence}</span>}
          {provenance?.source && (
            <>
              {evidence && <span className="text-[var(--bench-ink-muted)]">·</span>}
              <span>{provenance.source}</span>
            </>
          )}
          {provenance?.docId && (
            <>
              <span>·</span>
              <span>{provenance.docId}</span>
            </>
          )}
          {provenance?.confidence && (
            <>
              <span>·</span>
              <ConfidenceMark level={provenance.confidence} size="dot" />
            </>
          )}
          {provenance?.verifyUrl && (
            <span className="ml-auto">
              <span
                className="underline cursor-pointer hover:text-[var(--bench-ink-secondary)] transition-colors"
                onClick={() =>
                  window.open(
                    provenance.verifyUrl!,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter" && provenance.verifyUrl)
                    window.open(
                      provenance.verifyUrl,
                      "_blank",
                      "noopener,noreferrer"
                    );
                }}
                tabIndex={0}
                role="link"
              >
                Verify at source ↗
              </span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
