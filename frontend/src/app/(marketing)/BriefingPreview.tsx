"use client";

const PREVIEW_ITEMS = [
  {
    docId: "US 12,144,033",
    signal: "3x filing surge in quantum error correction",
    score: 89,
    tier: "strong" as const,
    confidence: "high",
  },
  {
    docId: "US 12,144,068",
    signal: "New entrant in AI chip packaging",
    score: 86,
    tier: "strong" as const,
    confidence: "high",
    selfCite: true,
  },
  {
    docId: "US 12,144,041",
    signal: "Cross-citation spike from Nvidia, Intel",
    score: 82,
    tier: "strong" as const,
    confidence: "medium",
  },
  {
    docId: "US 12,144,022",
    signal: "Assignee expanding into medical imaging",
    score: 78,
    tier: "medium" as const,
    confidence: "high",
  },
  {
    docId: "US 12,144,055",
    signal: "Divisional filing suggests portfolio build",
    score: 75,
    tier: "medium" as const,
    confidence: "medium",
  },
];

export function BriefingPreview() {
  const tierColor = (t: string) =>
    t === "strong"
      ? "bg-[var(--score-high-bg)] text-[var(--score-high)]"
      : "bg-[var(--score-medium-bg)] text-[var(--score-medium)]";

  return (
    <div className="w-[360px] surface-card rounded-[var(--radius-lg)] shadow-[var(--shadow-md)] overflow-hidden" aria-label="Weekly briefing preview">
      {/* Header */}
      <div className="bg-[var(--accent)] px-5 py-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-white/90">
          Weekly briefing preview
        </p>
        <p className="text-xs text-white/70 mt-0.5">
          Computing &amp; AI patents · G06F
        </p>
      </div>

      {/* Items */}
      <div className="divide-y divide-[var(--border-subtle)]">
        {PREVIEW_ITEMS.map((item, i) => (
          <div
            key={item.docId}
            className={`px-5 py-3 ${i >= 2 ? "opacity-40" : ""}`}
            aria-label={`Patent ${item.docId}: ${item.signal}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono text-[var(--text-muted)]">
                {item.docId}
              </span>
              <span className="text-xs font-bold text-[var(--accent)]">
                Score {item.score}
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mb-1.5 leading-snug">
              {item.signal}
            </p>
            <div className="flex items-center gap-2">
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${tierColor(
                  item.tier
                )}`}
              >
                {item.tier}
              </span>
              <span className="text-[10px] text-[var(--text-muted)]">
                confidence: {item.confidence}
              </span>
              {item.selfCite && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--warning)]/15 text-[var(--warning)] border border-[var(--warning)]/40">
                  self-citation risk
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 bg-[var(--bg-elevated)] border-t border-[var(--border-subtle)] text-right">
        <span className="text-xs text-[var(--accent)] font-medium">
          {PREVIEW_ITEMS.length - 2} more signals · view all →
        </span>
      </div>
    </div>
  );
}
