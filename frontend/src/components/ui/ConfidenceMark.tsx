"use client";

/**
 * ConfidenceMark — renders confidence as texture, not just color.
 *
 * Texture grammar:
 *   confirmed  → solid filled ring  + "Confirmed"
 *   high       → solid ring        + "High confidence"
 *   medium     → dashed ring       + "Medium confidence"
 *   estimated  → dashed ring       + "Estimated"
 *   low        → dotted ring       + "Low confidence"
 *
 * Colorblind-safe (redundant encoding: shape + label).
 * Used by every status/confidence display.
 *
 * Also available: Compact confidence dot (no label) via size="dot".
 */

export type ConfidenceLevel = "confirmed" | "high" | "medium" | "estimated" | "low";

interface ConfidenceMarkProps {
  level: ConfidenceLevel;
  size?: "sm" | "md" | "dot";
  className?: string;
}

const LABELS: Record<ConfidenceLevel, string> = {
  confirmed: "Confirmed",
  high: "High",
  medium: "Medium",
  estimated: "Estimated",
  low: "Low",
};

function ringStyle(level: ConfidenceLevel): React.CSSProperties {
  const base = {
    width: 8,
    height: 8,
    borderRadius: "50%",
    display: "inline-block",
    flexShrink: 0,
  } as React.CSSProperties;

  switch (level) {
    case "confirmed":
      return { ...base, background: "var(--ok)", border: "none" };
    case "high":
      return {
        ...base,
        background: "transparent",
        border: "2px solid var(--ok)",
      };
    case "medium":
    case "estimated":
      return {
        ...base,
        background: "transparent",
        border: "2px dashed var(--warn)",
      };
    case "low":
      return {
        ...base,
        background: "transparent",
        border: "2px dotted var(--text-muted)",
      };
  }
}

export function ConfidenceMark({
  level,
  size = "md",
  className = "",
}: ConfidenceMarkProps) {
  if (size === "dot") {
    return (
      <span
        style={ringStyle(level)}
        className={`${className}`}
        title={LABELS[level]}
        aria-label={LABELS[level]}
      />
    );
  }

  const textSize = size === "sm" ? "text-[10px]" : "text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium ${textSize} ${className}`}
      title={LABELS[level]}
    >
      <span style={ringStyle(level)} aria-hidden="true" />
      <span className="text-[var(--text-2)]">{LABELS[level]}</span>
    </span>
  );
}
