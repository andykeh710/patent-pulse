"use client";

interface AISourceFooterProps {
  className?: string;
}

/**
 * Standard footer for AI-generated patent analysis panels.
 * Bench provenance styling — warm neutral, labeled, never disguised as source data.
 */
export function AISourceFooter({ className = "" }: AISourceFooterProps) {
  return (
    <div className={`mt-4 pt-3 border-t flex items-start gap-2 ${className}`}
      style={{ borderColor: "var(--bench-line)" }}
    >
      <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0"
        style={{ color: "var(--bench-provenance)" }}
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p className="text-[11px] leading-relaxed"
        style={{ color: "var(--bench-ink-muted)" }}
      >
        <span style={{ color: "var(--bench-provenance)", fontWeight: 500 }}>AI-Generated</span>
        {" "}from patent metadata and claims. May contain inaccuracies.
        Not legal advice. Verify with official patent registers before acting.
      </p>
    </div>
  );
}
