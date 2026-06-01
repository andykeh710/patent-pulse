import Link from "next/link";

export type BriefingItemType =
  | "trend"
  | "notable"
  | "company"
  | "expiring"
  | "foryou"
  | "news";

interface BriefingItemProps {
  type: BriefingItemType;
  label: string;
  title: string;
  subtext?: string;
  reason: string;
  source: string;
  freshness: { updated_at: string; relative: string };
  confidence?: { level: "high" | "medium" | "low"; caveat?: string };
  href?: string;
}

const typeConfig: Record<BriefingItemType, { emoji: string; borderVar: string; bgVar: string }> = {
  trend:    { emoji: "📈", borderVar: "var(--type-trend)",    bgVar: "var(--signal-blue)" },
  notable:  { emoji: "🔍", borderVar: "var(--type-notable)",  bgVar: "var(--score-high)" },
  company:  { emoji: "🏢", borderVar: "var(--type-company)",  bgVar: "var(--type-company)" },
  expiring: { emoji: "⏳", borderVar: "var(--type-expiring)", bgVar: "var(--warning)" },
  foryou:   { emoji: "✨", borderVar: "var(--type-foryou)",   bgVar: "var(--signal-violet)" },
  news:     { emoji: "📰", borderVar: "var(--type-news)",     bgVar: "var(--signal-violet)" },
};

export function BriefingItem({
  type,
  label,
  title,
  subtext,
  reason,
  freshness,
  confidence,
  href,
}: BriefingItemProps) {
  const config = typeConfig[type];
  const isNews = type === "news";

  const inner = (
    <div
      className={`rounded-xl bg-[var(--bg-glass)] backdrop-blur-md border border-[var(--border-subtle)] p-3.5 ${isNews ? "border-dashed" : ""}`}
      style={{ borderLeftWidth: "3px", borderLeftColor: config.borderVar }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm">{config.emoji}</span>
        <span
          className="text-[11px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full"
          style={{
            background: `${config.bgVar}15`,
            color: config.borderVar,
          }}
        >
          {label}
        </span>
        <span className="ml-auto text-[11px] text-[var(--text-muted)]">
          {freshness.relative}
        </span>
      </div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)] leading-snug">
        {title}
      </h3>
      {subtext && (
        <p className="text-xs text-[var(--text-muted)] mt-0.5">{subtext}</p>
      )}
      <p className="text-xs text-[var(--text-muted)] mt-1.5 italic">
        {reason}
      </p>
      {confidence && confidence.level !== "high" && (
        <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded border border-[var(--warning)]/30 text-[var(--warning)]">
          {confidence.level} confidence{confidence.caveat ? ` — ${confidence.caveat}` : ""}
        </span>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {inner}
      </Link>
    );
  }

  return inner;
}
