import { Counter } from "./Counter";

interface StatTileProps {
  label: string;
  value: number;
  subtext?: string;
  accent?: "default" | "signal" | "warning";
}

export function StatTile({ label, value, subtext, accent = "default" }: StatTileProps) {
  const accentBorder = {
    default: "border-[var(--border-subtle)]",
    signal: "border-[var(--signal-blue)]/40",
    warning: "border-[var(--warning)]/40",
  }[accent];

  return (
    <div
      className={`rounded-xl bg-[var(--bg-glass)] backdrop-blur-md border ${accentBorder} p-4`}
    >
      <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-muted)]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-[var(--text-primary)] font-mono tabular-nums">
        <Counter value={value} duration={1200} />
      </div>
      {subtext && (
        <div className="mt-0.5 text-xs text-[var(--text-muted)]">{subtext}</div>
      )}
    </div>
  );
}
