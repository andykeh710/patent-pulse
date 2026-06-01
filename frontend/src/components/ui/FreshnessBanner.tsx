"use client";

import { useFreshness } from "@/hooks/useFreshness";

function formatRelative(isoString: string | null): string {
  if (!isoString) return "Unknown";
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 30) {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  return "Just now";
}

interface FreshnessBannerProps {
  /** Which indicators to show. Defaults to all. */
  show?: ("patents" | "summaries" | "trends" | "ai_runs")[];
  className?: string;
}

export function FreshnessBanner({
  show = ["patents", "summaries", "trends", "ai_runs"],
  className = "",
}: FreshnessBannerProps) {
  const { data, error } = useFreshness();

  if (error || !data) return null;

  const items: { label: string; value: string }[] = [];

  if (show.includes("patents") && data.latest_patent_created_at) {
    items.push({
      label: "Patents updated",
      value: formatRelative(data.latest_patent_created_at),
    });
  }

  if (show.includes("summaries") && data.total_summarized > 0) {
    items.push({
      label: "Summaries",
      value: `${data.total_summarized.toLocaleString()} / ${data.total_patents.toLocaleString()}`,
    });
  }

  if (show.includes("trends") && data.latest_trend_snapshot_at) {
    items.push({
      label: "Trends computed",
      value: formatRelative(data.latest_trend_snapshot_at),
    });
  }

  if (show.includes("ai_runs") && data.latest_ai_run_at) {
    items.push({
      label: "Last AI run",
      value: formatRelative(data.latest_ai_run_at),
    });
  }

  if (items.length === 0) return null;

  return (
    <div
      className={`flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--text-muted)] ${className}`}
    >
      {items.map((item, i) => (
        <span key={i}>
          <span className="text-[var(--text-secondary)]">{item.label}:</span>{" "}
          {item.value}
        </span>
      ))}
    </div>
  );
}
