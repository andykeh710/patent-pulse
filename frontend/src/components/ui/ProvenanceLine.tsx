"use client";

/**
 * ProvenanceLine — standardized "Source · doc_id · confidence · Verify" footer.
 *
 * Renders in --provenance signature color, Geist Mono, on every patent/expiry card.
 * The "Verify at source" link behavior comes from the parent's EvidenceRail.
 * This is the standalone version for use on cards that don't use the full EvidenceRail.
 */

import { ConfidenceMark } from "./ConfidenceMark";
import type { ConfidenceLevel } from "./ConfidenceMark";

interface ProvenanceLineProps {
  source?: string;
  docId?: string;
  confidence?: ConfidenceLevel;
  verifyUrl?: string;
  className?: string;
}

export function ProvenanceLine({
  source,
  docId,
  confidence,
  verifyUrl,
  className = "",
}: ProvenanceLineProps) {
  if (!source && !docId && !confidence) return null;

  return (
    <div
      className={`flex items-center gap-2 text-[10px] font-mono text-[var(--provenance)] ${className}`}
    >
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
          <ConfidenceMark level={confidence} size="dot" />
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
  );
}
