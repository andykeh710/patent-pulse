"use client";

/**
 * EvidenceRail — the signature visual spine for every intelligence card.
 * Renders a 2px accent-color left border + provenance line in --provenance.
 *
 * "Every claim literally has a backbone."
 *
 * Usage: wrap any card content:
 *   <EvidenceRail source="USPTO" docId="US12345678" confidence="high">
 *     <YourCardContent />
 *   </EvidenceRail>
 */

import { ConfidenceMark } from "./ConfidenceMark";
import type { ConfidenceLevel } from "./ConfidenceMark";

interface EvidenceRailProps {
  /** Patent office source (USPTO, EPO, WIPO) */
  source?: string;
  /** Document identifier */
  docId?: string;
  /** Confidence level */
  confidence?: ConfidenceLevel;
  /** Optional link to verify at source */
  verifyUrl?: string;
  /** Card content */
  children: React.ReactNode;
  /** Override the spine color (defaults to accent) */
  spineColor?: string;
  className?: string;
}

export function EvidenceRail({
  source,
  docId,
  confidence,
  verifyUrl,
  children,
  spineColor = "var(--accent)",
  className = "",
}: EvidenceRailProps) {
  const showProvenance = source || docId || confidence;

  return (
    <div
      className={`rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] ${className}`}
    >
      {/* Spine + content */}
      <div className="flex">
        {/* The evidence spine — 2px accent rule */}
        <div
          className="w-0.5 shrink-0 rounded-l-[var(--radius-md)]"
          style={{ backgroundColor: spineColor }}
        />

        <div className="flex-1 min-w-0 p-4">{children}</div>
      </div>

      {/* Provenance line — source metadata in signature color */}
      {showProvenance && (
        <div className="px-4 pb-3 pt-0 flex items-center gap-2 text-xs font-mono text-[var(--provenance)] border-t border-[var(--border)] mx-4">
          {source && <span>{source}</span>}
          {docId && (
            <>
              {source && <span>·</span>}
              <span>{docId}</span>
            </>
          )}
          {confidence && (
            <>
              <span>·</span>
              <ConfidenceMark level={confidence} size="sm" />
            </>
          )}
          {verifyUrl && (
            <span className="ml-auto">
              <span
                className="underline cursor-pointer hover:text-[var(--text-2)] transition-colors"
                onClick={() => {
                  window.open(verifyUrl, "_blank", "noopener,noreferrer");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter")
                    window.open(verifyUrl, "_blank", "noopener,noreferrer");
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
