"use client";

/**
 * Score — unified score display. Never shows decimals (renders Math.round).
 *
 * Variants:
 *   chip — colored dot + integer + optional label (compact badge)
 *   dial — larger circular score with tier ring
 *   bar  — horizontal bar with tier-colored fill
 *
 * Scale:
 *   "0-1"   — raw 0..1 scores (multiplied to 0..100)
 *   "0-100" — already in 0..100 range
 */

export type ScoreKind = "opportunity" | "interesting" | "composite";
export type ScoreTier = "strong" | "medium" | "weak";
export type ScoreVariant = "chip" | "dial" | "bar";
export type ScoreScale = "0-1" | "0-100";

interface ScoreProps {
  value: number | null;
  kind?: ScoreKind;
  tier?: ScoreTier;
  variant?: ScoreVariant;
  scale?: ScoreScale;
  size?: "sm" | "md";
  showLabel?: boolean;
  label?: string;
  className?: string;
}

const KIND_LABELS: Record<ScoreKind, string> = {
  opportunity: "opp",
  interesting: "int",
  composite: "score",
};

function resolveTier(value: number): ScoreTier {
  if (value >= 70) return "strong";
  if (value >= 35) return "medium";
  return "weak";
}

function tierColor(tier: ScoreTier): string {
  switch (tier) {
    case "strong":
      return "var(--score-high)";
    case "medium":
      return "var(--score-medium)";
    case "weak":
      return "var(--score-low)";
  }
}

function tierBg(tier: ScoreTier): string {
  switch (tier) {
    case "strong":
      return "var(--score-high-bg)";
    case "medium":
      return "var(--score-medium-bg)";
    case "weak":
      return "var(--score-low-bg)";
  }
}

export function Score({
  value,
  kind = "opportunity",
  tier,
  variant = "chip",
  scale = "0-1",
  size = "sm",
  showLabel = true,
  label,
  className = "",
}: ScoreProps) {
  if (value === null || value === undefined) {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[var(--bench-ink-muted)] ${size === "md" ? "text-sm" : "text-xs"} ${className}`}
      >
        <span className="font-mono tabular-nums">&mdash;</span>
      </span>
    );
  }

  const normalized = scale === "0-1" ? Math.round(value * 100) : Math.round(value);
  const effectiveTier = tier || resolveTier(normalized);
  const color = tierColor(effectiveTier);

  if (variant === "dial") {
    return <ScoreDial value={normalized} tier={effectiveTier} kind={kind} size={size} className={className} />;
  }

  if (variant === "bar") {
    return <ScoreBar value={normalized} tier={effectiveTier} kind={kind} size={size} className={className} />;
  }

  // Default: chip
  return <ScoreChip value={normalized} tier={effectiveTier} kind={kind} size={size} showLabel={showLabel} label={label} className={className} color={color} />;
}

/* ── Chip variant ── */

function ScoreChip({
  value, tier, kind, size, showLabel, label, className, color,
}: {
  value: number; tier: ScoreTier; kind: ScoreKind; size: string; showLabel: boolean; label?: string; className: string; color: string;
}) {
  const textSize = size === "md" ? "text-sm" : "text-xs";
  const dotSize = size === "md" ? 8 : 6;
  return (
    <span
      className={`inline-flex items-center gap-1 font-mono font-semibold ${textSize} tabular-nums ${className}`}
      style={{ color }}
      title={`${label || KIND_LABELS[kind]}: ${value}/100 (${tier})`}
    >
      <span
        className="inline-block rounded-full shrink-0"
        style={{ width: dotSize, height: dotSize, backgroundColor: color }}
        aria-hidden="true"
      />
      <span>{value}</span>
      {showLabel && (
        <span className="opacity-60 font-normal" style={{ color: "var(--bench-ink-secondary)" }}>
          {label || KIND_LABELS[kind]}
        </span>
      )}
    </span>
  );
}

/* ── Dial variant ── */

function ScoreDial({
  value, tier, kind, size, className,
}: {
  value: number; tier: ScoreTier; kind: ScoreKind; size: string; className: string;
}) {
  const dim = size === "md" ? 48 : 36;
  const strokeW = size === "md" ? 4 : 3;
  const r = (dim - strokeW) / 2;
  const circ = 2 * Math.PI * r;
  const pct = value / 100;
  const offset = circ * (1 - pct);
  const color = tierColor(tier);

  return (
    <span className={`inline-flex items-center gap-2 ${className}`} title={`${KIND_LABELS[kind]}: ${value}/100 (${tier})`}>
      <svg width={dim} height={dim} className="shrink-0" aria-hidden="true">
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={tierBg(tier)} strokeWidth={strokeW} />
        <circle
          cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={color}
          strokeWidth={strokeW} strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
        />
      </svg>
      <span className="font-mono font-bold tabular-nums" style={{ color, fontSize: size === "md" ? "1.125rem" : "0.8125rem" }}>
        {value}
      </span>
    </span>
  );
}

/* ── Bar variant ── */

function ScoreBar({
  value, tier, kind, size, className,
}: {
  value: number; tier: ScoreTier; kind: ScoreKind; size: string; className: string;
}) {
  const color = tierColor(tier);
  const h = size === "md" ? 8 : 6;
  return (
    <span className={`inline-flex items-center gap-2 ${className}`} title={`${KIND_LABELS[kind]}: ${value}/100 (${tier})`}>
      <span className="inline-block rounded-full overflow-hidden" style={{ width: 64, height: h, backgroundColor: tierBg(tier) }}>
        <span className="block h-full rounded-full" style={{ width: `${value}%`, backgroundColor: color }} />
      </span>
      <span className="font-mono font-semibold tabular-nums text-xs" style={{ color }}>
        {value}
      </span>
    </span>
  );
}
