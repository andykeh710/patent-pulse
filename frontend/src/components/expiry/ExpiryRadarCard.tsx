"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import { SourceAttribution } from "@/components/ui/SourceAttribution";

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

const STATUS_COLORS: Record<string, string> = {
  active_estimated: "bg-green-100 text-green-700",
  expiring_soon: "bg-amber-100 text-amber-700",
  expired_estimated: "bg-red-100 text-red-700",
  lapsed_possible: "bg-orange-100 text-orange-700",
  lapsed_confirmed: "bg-red-100 text-red-700",
  expired_confirmed: "bg-red-200 text-red-800",
  unknown: "bg-gray-100 text-gray-500",
};

const CONFIDENCE_LABELS: Record<string, string> = {
  confirmed: "Confirmed",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  confirmed: "bg-emerald-100 text-emerald-700",
  high: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-red-100 text-red-700",
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
}

export function ExpiryRadarCard({
  id,
  docId,
  title,
  assignee,
  estimatedExpiryDate,
  daysUntilExpiry,
  expiryStatus,
  expiryConfidence,
  activeFamilyRisk,
  opportunityScore,
  expiryOpportunityScore,
  legalStatus,
  legalStatusConfidence,
  usageSignalCount,  // keep undefined (null check) — render "assessed" empty state
  usageHasSelfCitationRisk,
}: ExpiryRadarCardProps) {
  const statusLabel = STATUS_LABELS[expiryStatus] || expiryStatus;
  const statusColor = STATUS_COLORS[expiryStatus] || "bg-gray-100 text-gray-500";
  const confLabel = CONFIDENCE_LABELS[expiryConfidence] || expiryConfidence;
  const confColor = CONFIDENCE_COLORS[expiryConfidence] || "bg-gray-100 text-gray-500";

  const expiryDateDisplay = estimatedExpiryDate
    ? formatDate(estimatedExpiryDate)
    : "Unknown";

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-3">
        {/* Left: patent info */}
        <div className="flex-1 min-w-0">
          <Link
            href={`/patents/${id}`}
            className="text-sm font-medium text-primary-600 hover:text-primary-800 truncate block"
          >
            {title || docId}
          </Link>
          <p className="text-xs text-gray-500 mt-0.5">
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
                  ? "bg-amber-100 text-amber-700"
                  : "bg-gray-100 text-gray-500"
              }`}
              title="Expiry opportunity score"
            >
              {expiryOpportunityScore.toFixed(0)}
            </span>
          )}
          {opportunityScore != null && (
            <span className="text-xs text-gray-400" title="General opportunity score">
              ({opportunityScore.toFixed(0)})
            </span>
          )}
        </div>
      </div>

      {/* Status row */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3">
        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${statusColor}`}>
          {statusLabel}
        </span>
        <span className={`text-xs px-1.5 py-0.5 rounded ${confColor}`}>
          {confLabel}
        </span>
        {activeFamilyRisk && (
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded bg-red-100 text-red-700"
            title="Active family members may exist in other jurisdictions"
          >
            ⚠ Family risk
          </span>
        )}
        {legalStatus && (
          <span className="text-xs text-gray-400">
            {legalStatus} · {legalStatusConfidence}
          </span>
        )}
      </div>

      {/* Dates row */}
      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
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

      {/* Usage signals (Sprint 5) */}
      <div className="mt-2 text-xs">
        {usageSignalCount != null && usageSignalCount > 0 ? (
          <span className="inline-flex items-center gap-1">
            <span className="text-gray-400">Usage signals:</span>
            <span className="font-medium text-gray-700">{usageSignalCount}</span>
          </span>
        ) : usageSignalCount != null && usageSignalCount === 0 ? (
          <span className="text-gray-400">Usage signals: none detected</span>
        ) : (
          <span className="text-gray-400" title="Usage signals assessed — check patent detail">Usage signals assessed — check patent detail</span>
        )}
        {usageHasSelfCitationRisk && (
          <span className="text-xs text-amber-600 ml-2" title="Some evidence shares assignee with source patent">⚠ Self-cite</span>
        )}
      </div>

      {/* Source attribution + legal caveat + verify-at-source */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <SourceAttribution docId={docId} />
        <p className="text-xs text-gray-400">
          Verify with official registers before relying on expiry status.{" "}
          <a
            href={`https://patents.google.com/patent/${encodeURIComponent(docId)}/en`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:underline"
          >
            View at Google Patents →
          </a>
        </p>
      </div>
    </div>
  );
}
