"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { Badge } from "./Badge";

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

interface InsightCardProps {
  /** Category label: signal, risk, opportunity, update, recommendation */
  type: InsightType;
  /** Primary heading */
  title: string;
  /** 1-2 sentence summary of what this means */
  summary: string;
  /** Optional: why this matters to the user */
  whyItMatters?: string;
  /** Optional: evidence backing (e.g., "14 patents, 5 assignees") */
  evidence?: string;
  /** Optional: confidence level (high, medium, low) */
  confidence?: "high" | "medium" | "low";
  /** Optional: timestamp for when this insight was generated */
  timestamp?: string;
  /** Primary CTA */
  primaryAction?: InsightAction;
  /** Secondary action */
  secondaryAction?: InsightAction;
  /** Optional: source IDs or attribution */
  sourceIds?: string[];
  /** Optional: personalization context (why this was shown to THIS user) */
  personalization?: {
    whyShown: string;
    rank?: number;
    signals?: string[];
  };
  /** Optional: extra content at the bottom */
  children?: ReactNode;
  className?: string;
}

// -- Styling ---------------------------------------------------------------

const TYPE_STYLES: Record<InsightType, { badge: string; border: string; bg: string }> = {
  signal: {
    badge: "bg-[var(--accent-muted)] text-[var(--type-trend)]",
    border: "border-l-[var(--accent)]",
    bg: "bg-[var(--bg-glass)]",
  },
  risk: {
    badge: "bg-[var(--warning)]/12 text-[var(--warning)]",
    border: "border-l-[var(--warning)]",
    bg: "bg-[var(--bg-glass)]",
  },
  opportunity: {
    badge: "bg-[var(--score-high-bg)] text-[var(--score-high)]",
    border: "border-l-[var(--score-high)]",
    bg: "bg-[var(--bg-glass)]",
  },
  update: {
    badge: "bg-[var(--text-muted)]/12 text-[var(--text-muted)]",
    border: "border-l-[var(--text-muted)]",
    bg: "bg-[var(--bg-glass)]",
  },
  recommendation: {
    badge: "bg-[var(--accent-muted)] text-[var(--text-2)]",
    border: "border-l-[var(--accent)]",
    bg: "bg-[var(--bg-elevated)]",
  },
};

const CONFIDENCE_LABELS: Record<string, { label: string; color: string }> = {
  high: { label: "High confidence", color: "text-[var(--score-high)]" },
  medium: { label: "Medium confidence", color: "text-[var(--score-medium)]" },
  low: { label: "Low confidence", color: "text-[var(--text-muted)]" },
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
    "text-sm font-medium text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors";
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
  children,
  className = "",
}: InsightCardProps) {
  const style = TYPE_STYLES[type];

  return (
    <div
      className={`rounded-lg border border-[var(--border-subtle)] ${style.border} ${style.bg} border-l-2 p-4 ${className}`}
    >
      {/* Header row: type badge + confidence + timestamp */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span
          className={`text-xs font-medium px-1.5 py-0.5 rounded ${style.badge}`}
        >
          {TYPE_LABELS[type]}
        </span>
        {confidence && (
          <span className={`text-xs ${CONFIDENCE_LABELS[confidence].color}`}>
            {CONFIDENCE_LABELS[confidence].label}
          </span>
        )}
        {timestamp && (
          <span className="text-xs text-[var(--text-muted)] ml-auto">
            {timestamp}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
        {title}
      </h3>

      {/* Summary */}
      <p className="text-sm text-[var(--text-secondary)] mb-2">{summary}</p>

      {/* Why it matters */}
      {whyItMatters && (
        <p className="text-xs text-[var(--text-muted)] mb-2">
          Why it matters: {whyItMatters}
        </p>
      )}

      {/* Personalization — why shown for this user */}
      {personalization && (
        <div className="mb-2 rounded-[var(--radius-sm)] bg-[var(--bg-glass-strong)] px-3 py-2">
          <p className="text-[11px] text-[var(--text-2)] leading-relaxed">
            {personalization.whyShown}
          </p>
          {personalization.signals && personalization.signals.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {personalization.signals.map((s, i) => (
                <span
                  key={i}
                  className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-glass)] px-1.5 py-0.5 rounded"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Evidence */}
      {evidence && (
        <p className="text-xs text-[var(--text-muted)] mb-2 italic">
          Evidence: {evidence}
        </p>
      )}

      {/* Actions */}
      {(primaryAction || secondaryAction) && (
        <div className="flex items-center gap-4 mt-2 pt-2 border-t border-[var(--border-subtle)]">
          {primaryAction && <ActionLink action={primaryAction} />}
          {secondaryAction && (
            <ActionLink action={secondaryAction} />
          )}
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
  );
}
