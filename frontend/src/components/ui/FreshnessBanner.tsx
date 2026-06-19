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

  // Show ingestion status clearly
  if (show.includes("patents")) {
    if (data.last_ingestion_status === "success") {
      const newCount = data.last_ingestion_new_records ?? 0;
      const when = formatRelative(data.last_ingestion_finished_at);
      items.push({
        label: "Ingestion",
        value: `Last ran ${when}${newCount > 0 ? ` (${newCount} new)` : " (no new records)"}`,
      });
    } else if (data.last_ingestion_status === "failed") {
      items.push({
        label: "Ingestion",
        value: `Failed — ${data.last_ingestion_error || "unknown error"}`,
      });
    } else {
      // never_run or null — use legacy created_at as fallback
      if (data.latest_patent_created_at) {
        items.push({
          label: "Patents updated",
          value: formatRelative(data.latest_patent_created_at),
        });
      }
    }
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

  // Stale-data disclosure: separate ingestion staleness from source lag
  const ingestionAgeDays =
    show.includes("patents") && data.last_ingestion_finished_at
      ? daysSince(data.last_ingestion_finished_at)
      : data.latest_patent_created_at
        ? daysSince(data.latest_patent_created_at)
        : null;
  const trendAgeDays = show.includes("trends") ? daysSince(data.latest_trend_snapshot_at) : null;
  const ingestionStale = ingestionAgeDays !== null && ingestionAgeDays > STALE_AFTER_DAYS;
  const trendsStale = trendAgeDays !== null && trendAgeDays > STALE_AFTER_DAYS;

  // Source lag: publication date vs today
  const pubDate = data.latest_patent_publication_date
    ? new Date(data.latest_patent_publication_date)
    : null;
  const pubAgeDays = pubDate ? Math.floor((Date.now() - pubDate.getTime()) / (1000 * 60 * 60 * 24)) : null;
  // USPTO publishes weekly; anything > 10 days from today is source lag
  const sourceLag = pubAgeDays !== null && pubAgeDays > 10;

  if (items.length === 0 && !ingestionStale && !trendsStale && !sourceLag && data.last_ingestion_status !== "failed") return null;

  return (
    <div className={className}>
      {/* Failed/degraded ingestion — always show regardless of staleness */}
      {(data.last_ingestion_status === "failed" || data.last_ingestion_status === "partial_success" || data.last_ingestion_status === "degraded") && (
        <div
          role="status"
          className="mb-2 flex items-start gap-2 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-700 dark:text-red-300"
        >
          <span aria-hidden className="mt-0.5 font-bold">⚠</span>
          <div>
            <span className="font-semibold">
              {data.last_ingestion_status === "partial_success"
                ? "Ingestion partially failed."
                : "Ingestion sources unavailable."}
            </span>{" "}
            {data.last_ingestion_error || "USPTO data APIs are currently unreachable."}
            {" "}Patent data may be out of date. Verify against official patent registers.
          </div>
        </div>
      )}

      {/* Source lag: last successful run but no new data */}
      {data.last_ingestion_status === "success" && data.last_ingestion_new_records === 0 && (
        <div
          role="status"
          className="mb-2 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"
        >
          <span aria-hidden className="mt-0.5 font-bold">ⓘ</span>
          <div>
            <span className="font-semibold">No new patent data available.</span>{" "}
            Ingestion ran but USPTO data sources did not return newer records.
            Latest patent in database is from {data.latest_patent_publication_date || "unknown"}.
          </div>
        </div>
      )}

      {/* Strong warning: ingestion stale */}
      {ingestionStale && data.last_ingestion_status === "success" && data.last_ingestion_new_records === 0 && (
        <div
          role="status"
          className="mb-2 flex items-start gap-2 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-700 dark:text-red-300"
        >
          <span aria-hidden className="mt-0.5 font-bold">⚠</span>
          <div>
            <span className="font-semibold">Ingestion pipeline has been unable to fetch new data for {ingestionAgeDays}d.</span>{" "}
            Last successful ingestion was {ingestionAgeDays}d ago
            {data.last_ingestion_status === "failed" && ` (last attempt failed: ${data.last_ingestion_error || "unknown"})`}.
            {" "}Verify patent data against official registers.
          </div>
        </div>
      )}

      {/* Softer notice: ingestion ran but source data has inherent lag */}
      {!ingestionStale && sourceLag && (
        <div
          role="status"
          className="mb-2 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"
        >
          <span aria-hidden className="mt-0.5 font-bold">ℹ</span>
          <div>
            <span className="font-semibold">Source data lag.</span>{" "}
            Ingestion ran successfully{data.last_ingestion_finished_at ? ` ${formatRelative(data.last_ingestion_finished_at)}` : ""}
            , but the latest patent publication in our database is from {pubDate?.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            {" "}({pubAgeDays}d ago). USPTO publishes new patents weekly on Tuesdays and Thursdays.
          </div>
        </div>
      )}

      {trendsStale && (
        <div
          role="status"
          className="mb-2 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"
        >
          <span aria-hidden className="mt-0.5 font-bold">⚠</span>
          <div>
            <span className="font-semibold">Trends are stale.</span>{" "}
            Trends were last computed {trendAgeDays}d ago.
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
