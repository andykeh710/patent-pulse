"use client";

import { useFreshness } from "@/hooks/useFreshness";

// Patent/trend data older than this is flagged loudly so the product never
// silently implies live intelligence. The free Google Patents BigQuery dataset
// lags real-time, so stale windows are expected and must be disclosed.
const STALE_AFTER_DAYS = 7;

function daysSince(isoString: string | null): number | null {
  if (!isoString) return null;
  const ms = Date.now() - new Date(isoString).getTime();
  if (Number.isNaN(ms)) return null;
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

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

  // Loud stale-data disclosure. Based on ingestion recency (created_at) and
  // trend recompute time. Only shown for sources the caller asked about.
  const patentAgeDays = show.includes("patents") ? daysSince(data.latest_patent_created_at) : null;
  const trendAgeDays = show.includes("trends") ? daysSince(data.latest_trend_snapshot_at) : null;
  const patentsStale = patentAgeDays !== null && patentAgeDays > STALE_AFTER_DAYS;
  const trendsStale = trendAgeDays !== null && trendAgeDays > STALE_AFTER_DAYS;

  if (items.length === 0 && !patentsStale && !trendsStale) return null;

  return (
    <div className={className}>
      {(patentsStale || trendsStale) && (
        <div
          role="status"
          className="mb-2 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"
        >
          <span aria-hidden className="mt-0.5 font-bold">⚠</span>
          <div>
            <span className="font-semibold">Data is not live.</span>{" "}
            {patentsStale && (
              <>Patent ingestion last ran {patentAgeDays}d ago{data.latest_patent_publication_date ? ` (latest publication ${formatRelative(data.latest_patent_publication_date)})` : ""}. </>
            )}
            {trendsStale && <>Trends were last computed {trendAgeDays}d ago. </>}
            Recent filings may be missing — this reflects the current data source&apos;s
            refresh lag, not live intelligence. Verify against official patent
            registers before acting.
          </div>
        </div>
      )}
      {items.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--text-muted)]">
          {items.map((item, i) => (
            <span key={i}>
              <span className="text-[var(--text-secondary)]">{item.label}:</span>{" "}
              {item.value}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
