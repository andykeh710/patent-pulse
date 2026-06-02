import { ReactNode } from "react";

type PillTone = "indigo" | "violet" | "cyan" | "green" | "amber" | "red" | "gray";
type PillVariant = "filled" | "outline";

interface PillProps {
  children: ReactNode;
  tone?: PillTone;
  variant?: PillVariant;
  mono?: boolean;
  className?: string;
}

const toneMap: Record<PillTone, { bg: string; text: string; border: string }> = {
  indigo: { bg: "bg-[var(--accent)]/12", text: "text-[var(--accent)]", border: "border-[var(--accent)]/30" },
  violet: { bg: "bg-[var(--type-foryou)]/12", text: "text-[var(--type-foryou)]", border: "border-[var(--type-foryou)]/30" },
  cyan:   { bg: "bg-[var(--type-company)]/12",  text: "text-[var(--type-company)]",  border: "border-[var(--type-company)]/30" },
  green:  { bg: "bg-[var(--score-high)]/12",   text: "text-[var(--score-high)]",   border: "border-[var(--score-high)]/30" },
  amber:  { bg: "bg-[var(--warning)]/12",       text: "text-[var(--warning)]",       border: "border-[var(--warning)]/30" },
  red:    { bg: "bg-[var(--expiry-lapsed-confirmed)]/12", text: "text-[var(--expiry-lapsed-confirmed)]", border: "border-[var(--expiry-lapsed-confirmed)]/30" },
  gray:   { bg: "bg-[var(--text-muted)]/12",    text: "text-[var(--text-muted)]",    border: "border-[var(--text-muted)]/30" },
};

export function Pill({
  children,
  tone = "indigo",
  variant = "filled",
  mono = false,
  className = "",
}: PillProps) {
  const t = toneMap[tone];
  const base = "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium leading-none";
  const font = mono ? "font-mono tabular-nums" : "";

  if (variant === "outline") {
    return (
      <span className={`${base} border ${t.border} ${t.text} ${font} ${className}`}>
        {children}
      </span>
    );
  }

  return (
    <span className={`${base} ${t.bg} ${t.text} ${font} ${className}`}>
      {children}
    </span>
  );
}
