"use client";

import { ReactNode, useMemo } from "react";
import { FreshnessChip } from "./FreshnessChip";
import type { FreshnessState, FreshnessSource } from "./FreshnessChip";
import { useFreshness } from "@/hooks/useFreshness";

interface PageHeaderProps {
  /** Page title (h1) */
  title: string;
  /** Subtitle / description line */
  description?: string;
  /** Primary CTA button or action node */
  primaryAction?: ReactNode;
  /** Secondary action node */
  secondaryAction?: ReactNode;
  /** Show data freshness chip for these sources */
  freshnessSources?: ("patents" | "summaries" | "trends" | "ai_runs")[];
  /** Optional badge/label above the title */
  label?: string;
  /** Optional metadata below description */
  meta?: string;
  className?: string;
}

/**
 * Formats a relative time string from an ISO timestamp.
 */
function formatRelative(isoString: string | null): string | null {
  if (!isoString) return null;
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 30)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  return "Just now";
}

const STALE_AFTER_DAYS = 7;

export function PageHeader({
  title,
  description,
  primaryAction,
  secondaryAction,
  freshnessSources,
  label,
  meta,
  className = "",
}: PageHeaderProps) {
  const { data } = useFreshness();

  // Build FreshnessChip state from freshness data
  const freshnessState = useMemo(() => {
    if (!data || !freshnessSources || freshnessSources.length === 0)
      return "fresh" as FreshnessState;

    // Full-source failure → degraded
    if (data.last_ingestion_status === "failed" || data.last_ingestion_status === "degraded") {
      return "degraded" as FreshnessState;
    }

    // Stale check
    const ageTarget =
      data.last_ingestion_finished_at || data.latest_patent_created_at;
    if (ageTarget) {
      const days = Math.floor(
        (Date.now() - new Date(ageTarget).getTime()) / (1000 * 60 * 60 * 24)
      );
      if (days > STALE_AFTER_DAYS) return "stale" as FreshnessState;
    }

    return "fresh" as FreshnessState;
  }, [data, freshnessSources]);

  const freshnessLabel = useMemo(() => {
    if (!data || !freshnessSources) return "Loading...";

    if (freshnessState === "degraded") {
      return data.last_ingestion_error || "Sources unavailable";
    }

    const rel = formatRelative(
      data.last_ingestion_finished_at || data.latest_patent_created_at
    );
    if (rel) {
      const newCount = data.last_ingestion_new_records ?? 0;
      return `Updated ${rel}${newCount > 0 ? ` · ${newCount} new` : ""}`;
    }
    return "Unknown";
  }, [data, freshnessSources, freshnessState]);

  const freshnessPopoverSources = useMemo(() => {
    if (!data || !freshnessSources) return undefined;
    const sources: FreshnessSource[] = [];

    if (freshnessSources.includes("patents")) {
      const rel = formatRelative(
        data.last_ingestion_finished_at || data.latest_patent_created_at
      );
      sources.push({
        label: "Patent Ingestion",
        status:
          data.last_ingestion_status === "success"
            ? "up"
            : data.last_ingestion_status === "failed" || data.last_ingestion_status === "degraded"
              ? "down"
              : "stale",
        lastRun: rel || "Unknown",
        newRecords: data.last_ingestion_new_records ?? 0,
        detail:
          data.last_ingestion_status === "failed"
            ? data.last_ingestion_error || "Ingestion failed"
            : data.last_ingestion_status === "degraded"
              ? "Partial failure — some sources unavailable"
              : undefined,
      });
    }

    if (freshnessSources.includes("summaries") && data.total_summarized > 0) {
      sources.push({
        label: "AI Summaries",
        status: "up",
        detail: `${data.total_summarized.toLocaleString()} / ${data.total_patents.toLocaleString()} summarized`,
      });
    }

    if (freshnessSources.includes("trends") && data.latest_trend_snapshot_at) {
      const rel = formatRelative(data.latest_trend_snapshot_at);
      sources.push({
        label: "Trends",
        status: "up",
        lastRun: rel || undefined,
      });
    }

    if (
      freshnessSources.includes("patents") &&
      data.latest_patent_publication_date
    ) {
      const pubDate = new Date(data.latest_patent_publication_date);
      const pubAgeDays = Math.floor(
        (Date.now() - pubDate.getTime()) / (1000 * 60 * 60 * 24)
      );
      if (pubAgeDays > 10) {
        sources.push({
          label: "Source Lag",
          status: "stale",
          detail: `Latest patent publication: ${pubDate.toLocaleDateString("en-US", { month: "short", day: "numeric" })} (${pubAgeDays}d ago). USPTO publishes Tue/Thu.`,
        });
      }
    }

    return sources.length > 0 ? sources : undefined;
  }, [data, freshnessSources]);

  return (
    <div className={`mb-6 ${className}`}>
      {label && (
        <span className="text-[10px] uppercase tracking-[0.12em] text-[var(--text-muted)] block mb-1">
          {label}
        </span>
      )}

      {/* Header row: H1 left, actions + chip right */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-[var(--text)]">{title}</h1>
          {description && (
            <p className="text-[var(--text-2)] mt-1">{description}</p>
          )}
          {meta && (
            <p className="text-xs text-[var(--text-muted)] mt-1">{meta}</p>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {freshnessSources && freshnessSources.length > 0 && data && (
            <FreshnessChip
              state={freshnessState}
              label={freshnessLabel}
              sources={freshnessPopoverSources}
            />
          )}
          {secondaryAction}
          {primaryAction}
        </div>
      </div>

    </div>
  );
}
