type LiveState = "live" | "scanning" | "updated" | "idle";

interface LiveIndicatorProps {
  state?: LiveState;
  label?: string;
}

const stateConfig: Record<LiveState, { dotColor: string; glowColor: string; label: string }> = {
  live:     { dotColor: "bg-[var(--score-high)]", glowColor: "", label: "Live" },
  scanning: { dotColor: "bg-[var(--accent)]", glowColor: "", label: "Scanning…" },
  updated:  { dotColor: "bg-[var(--text-muted)]",   glowColor: "", label: "" },
  idle:     { dotColor: "bg-[var(--text-disabled)]", glowColor: "", label: "No signal yet" },
};

export function LiveIndicator({ state = "live", label }: LiveIndicatorProps) {
  const config = stateConfig[state];

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
      <span
        className={`inline-block w-2 h-2 rounded-full ${config.dotColor} ${config.glowColor}`}
      />
      {label || config.label}
    </span>
  );
}
