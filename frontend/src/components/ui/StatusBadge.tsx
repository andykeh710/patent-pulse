"use client";

import { cn } from "@/lib/utils";

// -- Types ----------------------------------------------------------------

type StatusTone = "positive" | "warning" | "danger" | "neutral" | "info";

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  size?: "sm" | "md";
  className?: string;
}

// -- Styling ---------------------------------------------------------------

const TONE_STYLES: Record<StatusTone, string> = {
  positive: "bg-[var(--score-high-bg)] text-[var(--score-high)]",
  warning: "bg-[var(--warning)]/12 text-[var(--warning)]",
  danger: "bg-[var(--expiry-lapsed-confirmed)]/12 text-[var(--expiry-lapsed-confirmed)]",
  neutral: "bg-[var(--text-muted)]/12 text-[var(--text-muted)]",
  info: "bg-[var(--accent-muted)] text-[var(--accent)]",
};

const SIZE_STYLES = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

// -- Component -------------------------------------------------------------

export function StatusBadge({
  label,
  tone = "neutral",
  size = "sm",
  className,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded-full",
        TONE_STYLES[tone],
        SIZE_STYLES[size],
        className,
      )}
    >
      {label}
    </span>
  );
}

// -- Presets for common patent/company states -------------------------------

/**
 * Maps expiry status strings from the backend to appropriate tones.
 * Use with the label from ExpiryRadarCard STATUS_LABELS.
 */
export function expiryStatusTone(status: string): StatusTone {
  if (status.startsWith("active")) return "positive";
  if (status.startsWith("expiring")) return "warning";
  if (status.startsWith("lapsed") || status.startsWith("expired")) return "danger";
  return "neutral";
}

/**
 * Maps legal status confidence to appropriate tones.
 */
export function confidenceTone(confidence: string): StatusTone {
  if (confidence === "confirmed") return "positive";
  if (confidence === "estimated") return "warning";
  return "neutral";
}
