type LiveState = "live" | "scanning" | "updated" | "idle";

interface LiveIndicatorProps {
  state?: LiveState;
  label?: string;
}

const stateConfig: Record<LiveState, { dotColor: string; glowColor: string; label: string }> = {
  live:     { dotColor: "bg-[var(--score-high)]", glowColor: "shadow-[0_0_8px_var(--score-high)]", label: "Live" },
  scanning: { dotColor: "bg-[var(--signal-blue)]", glowColor: "shadow-[0_0_8px_var(--signal-blue)]", label: "Scanning…" },
  updated:  { dotColor: "bg-[var(--text-muted)]",   glowColor: "", label: "" },
  idle:     { dotColor: "bg-[var(--text-disabled)]", glowColor: "", label: "No signal yet" },
};

export function LiveIndicator({ state = "live", label }: LiveIndicatorProps) {
  const config = stateConfig[state];

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
      <span
        className={`inline-block w-2 h-2 rounded-full ${config.dotColor} ${config.glowColor} ${state === "live" ? "animate-[signalPulse_2s_ease-in-out_infinite]" : ""}`}
      />
      {label || config.label}
    </span>
  );
}
