"use client";

/**
 * Score — unified score display. Never shows decimals (renders Math.round).
 *
 * Kills the three-format inconsistency across pages:
 *   - No more "29 opp / 29%" vs "75 opp · strong" vs "75.04"
 *   - No more two-decimal noise
 *
 * Props:
 *   value  — raw score (0..100 or 0..1), rendered as integer
 *   kind   — "opportunity" | "interesting" | "composite" (affects label)
 *   tier   — "strong" | "medium" | "weak" (affects color + dot)
 *   size   — "sm" | "md"
 *   showLabel — include the label text
 */

export type ScoreKind = "opportunity" | "interesting" | "composite";
export type ScoreTier = "strong" | "medium" | "weak";

interface ScoreProps {
  value: number | null;
  kind?: ScoreKind;
  tier?: ScoreTier;
  size?: "sm" | "md";
  showLabel?: boolean;
  className?: string;
}

const KIND_LABELS: Record<ScoreKind, string> = {
  opportunity: "opp",
  interesting: "int",
  composite: "score",
};

function resolveTier(value: number | null): ScoreTier {
  if (value === null) return "weak";
  if (value >= 70) return "strong";
  if (value >= 35) return "medium";
  return "weak";
}

function tierColor(tier: ScoreTier): string {
  switch (tier) {
    case "strong":
      return "var(--ok)";
    case "medium":
      return "var(--warn)";
    case "weak":
      return "var(--text-muted)";
  }
}

export function Score({
  value,
  kind = "opportunity",
  tier,
  size = "sm",
  showLabel = true,
  className = "",
}: ScoreProps) {
  if (value === null || value === undefined) {
    return (
      <span className={`inline-flex items-center gap-1 text-[var(--text-muted)] ${size === "md" ? "text-sm" : "text-xs"} ${className}`}>
        <span className="font-mono">—</span>
      </span>
    );
  }

  // Always round to integer. Normalize 0..1 → 0..100.
  const normalized = value <= 1 ? Math.round(value * 100) : Math.round(value);
  const effectiveTier = tier || resolveTier(normalized);
  const color = tierColor(effectiveTier);

  const textSize = size === "md" ? "text-sm" : "text-xs";
  const dotSize = size === "md" ? 8 : 6;

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-semibold ${textSize} tabular-nums ${className}`}
      style={{ color }}
      title={`${KIND_LABELS[kind]}: ${normalized}/100 (${effectiveTier})`}
    >
      <span
        className="inline-block rounded-full shrink-0"
        style={{
          width: dotSize,
          height: dotSize,
          backgroundColor: color,
        }}
        aria-hidden="true"
      />
      <span>{normalized}</span>
      {showLabel && (
        <span className="opacity-60 font-normal" style={{ color: "var(--text-2)" }}>
          {KIND_LABELS[kind]}
        </span>
      )}
    </span>
  );
}
