"use client";

import Link from "next/link";
import { formatDate } from "@/lib/utils";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { StatusBadge, expiryStatusTone, confidenceTone } from "@/components/ui/StatusBadge";

// Allowed values from backend Sprint 2A.
const STATUS_LABELS: Record<string, string> = {
  active_estimated: "Active (est.)",
  expiring_soon: "Expiring Soon",
  expired_estimated: "Expired (est.)",
  lapsed_possible: "Lapsed (possible)",
  lapsed_confirmed: "Lapsed (confirmed)",
  expired_confirmed: "Expired (confirmed)",
  unknown: "Unknown",
};

export interface ExpiryRadarCardProps {
  id: string;
  docId: string;
  title: string | null;
  assignee: string;
  estimatedExpiryDate: string | null;
  daysUntilExpiry: number | null;
  expiryStatus: string;
  expiryConfidence: string;
  activeFamilyRisk: boolean;
  opportunityScore: number | null;
  expiryOpportunityScore: number | null;
  legalStatus: string | null;
  legalStatusConfidence: string;
  usageSignalCount?: number | null;
  usageHasSelfCitationRisk?: boolean | null;
  /** Whether this patent is in the user's watchlist */
  isSaved?: boolean;
  /** Called when the user toggles save/unsave */
  onToggleSave?: (patentId: string) => void;
}

/** Derive a brief commercial-relevance sentence from the card data.
 *  Deterministic, evidence-backed — no LLM. */
function whyItMatters(props: ExpiryRadarCardProps): string | null {
  const reasons: string[] = [];
  if (props.expiryOpportunityScore != null && props.expiryOpportunityScore >= 70) {
    reasons.push("strong expiry opportunity score");
  }
  if (props.usageSignalCount != null && props.usageSignalCount > 0) {
    reasons.push(`${props.usageSignalCount} commercial usage ${props.usageSignalCount === 1 ? "signal" : "signals"}`);
  }
  if (props.expiryStatus === "expiring_soon" && props.daysUntilExpiry != null && props.daysUntilExpiry <= 90) {
    reasons.push("expiring within 90 days");
  }
  if (props.activeFamilyRisk) {
    reasons.push("active family members in other jurisdictions");
  }
  if (reasons.length === 0) return null;
  return "Why this may matter: " + reasons.join(", ") + ".";
}

export function ExpiryRadarCard({
  id, docId, title, assignee, estimatedExpiryDate, daysUntilExpiry,
  expiryStatus, expiryConfidence, activeFamilyRisk, opportunityScore,
  expiryOpportunityScore, legalStatus, legalStatusConfidence,
  usageSignalCount, usageHasSelfCitationRisk,
  isSaved, onToggleSave,
}: ExpiryRadarCardProps) {
  const statusLabel = daysUntilExpiry != null && daysUntilExpiry <= 0
    ? "Expired"
    : STATUS_LABELS[expiryStatus] || expiryStatus;
  const statusTone = daysUntilExpiry != null && daysUntilExpiry <= 0
    ? expiryStatusTone("expired_confirmed")
    : expiryStatusTone(expiryStatus);
  const confTone = confidenceTone(expiryConfidence);

  const expiryDateDisplay = estimatedExpiryDate ? formatDate(estimatedExpiryDate) : "Unknown";
  const relevanceSentence = whyItMatters({
    id, docId, title, assignee, estimatedExpiryDate, daysUntilExpiry,
    expiryStatus, expiryConfidence, activeFamilyRisk, opportunityScore,
    expiryOpportunityScore, legalStatus, legalStatusConfidence,
    usageSignalCount, usageHasSelfCitationRisk,
  });

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:shadow-sm transition-shadow relative">
      {/* Save/bookmark button */}
      {onToggleSave && (
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleSave(id); }}
          className={`absolute top-3 right-3 p-1.5 rounded-lg transition-colors ${
            isSaved
              ? "text-[var(--accent)] bg-[var(--accent-muted)]"
              : "text-[var(--text-muted)] hover:text-[var(--accent)] hover:bg-[var(--accent-muted)]"
          }`}
          title={isSaved ? "Remove from watchlist" : "Save to watchlist"}
          aria-label={isSaved ? "Remove from watchlist" : "Save to watchlist"}
        >
          <svg className="w-4 h-4" fill={isSaved ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
        </button>
      )}

      <div className="flex items-start justify-between gap-3">
        {/* Left: patent info */}
        <div className="flex-1 min-w-0 pr-8">
          <Link
            href={`/patents/${id}`}
            className="text-sm font-medium text-[var(--accent)] hover:text-[var(--accent-hover)] truncate block"
          >
            {title || docId}
          </Link>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            {docId} · {assignee || "Unknown assignee"}
          </p>
        </div>

        {/* Right: scores */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {expiryOpportunityScore != null && (
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded ${
                expiryOpportunityScore >= 70
                  ? "bg-emerald-100 text-emerald-700"
                  : expiryOpportunityScore >= 40
                  ? "bg-[var(--score-medium-bg)] text-[var(--score-medium)]"
                  : "bg-[var(--bg-elevated)] text-[var(--text-muted)]"
              }`}
            >
              {expiryOpportunityScore.toFixed(0)}
            </span>
          )}
        </div>
      </div>

      {/* Status row — uses StatusBadge from Sprint 2 */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3">
        <StatusBadge label={statusLabel} tone={statusTone} />
        <StatusBadge label={expiryConfidence} tone={confTone} />
        {activeFamilyRisk && (
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded bg-red-100 text-red-700"
            title="Active family members may exist in other jurisdictions"
          >
            ⚠ Family risk
          </span>
        )}
        {legalStatus && (
          <span className="text-xs text-[var(--text-muted)]">
            {legalStatus}
          </span>
        )}
      </div>

      {/* Dates row */}
      <div className="flex items-center gap-3 mt-2 text-xs text-[var(--text-muted)]">
        <span>Expiry: {expiryDateDisplay}</span>
        {daysUntilExpiry != null && (
          <span
            className={
              daysUntilExpiry <= 90
                ? "text-red-600 font-medium"
                : daysUntilExpiry <= 365
                ? "text-amber-600 font-medium"
                : ""
            }
          >
            {daysUntilExpiry > 365
              ? `${(daysUntilExpiry / 365).toFixed(1)} yr remaining`
              : `${daysUntilExpiry} days remaining`}
          </span>
        )}
      </div>

      {/* Why it matters */}
      {relevanceSentence && (
        <p className="mt-2 text-xs text-[var(--text-secondary)] italic border-l-2 border-[var(--accent)]/30 pl-2">
          {relevanceSentence}
        </p>
      )}

      {/* Usage signals */}
      <div className="mt-2 text-xs">
        {usageSignalCount != null && usageSignalCount > 0 ? (
          <span className="inline-flex items-center gap-1">
            <span className="text-[var(--text-muted)]">Usage signals:</span>
            <span className="font-medium text-[var(--text-secondary)]">{usageSignalCount}</span>
          </span>
        ) : usageSignalCount != null && usageSignalCount === 0 ? (
          <span className="text-[var(--text-muted)]">Usage signals: none detected</span>
        ) : (
          <span className="text-[var(--text-muted)]">Usage signals assessed — check patent detail</span>
        )}
        {usageHasSelfCitationRisk && (
          <span className="text-xs text-amber-600 ml-2">⚠ Self-cite</span>
        )}
      </div>

      {/* Source + legal caveat */}
      <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
        <SourceAttribution docId={docId} />
        <p className="text-xs text-[var(--text-muted)]">
          Verify with official registers before relying on expiry status.{" "}
          <a
            href={`https://patents.google.com/patent/${encodeURIComponent(docId)}/en`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--accent)] hover:underline"
          >
            View at Google Patents →
          </a>
        </p>
      </div>
    </div>
  );
}
