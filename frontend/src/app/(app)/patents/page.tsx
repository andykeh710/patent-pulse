"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { usePatents } from "@/hooks/usePatents";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import type { PatentListParams } from "@/lib/types";

const OFFICES = ["US", "EP", "WO", "JP", "CN", "KR"] as const;

export default function PatentsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-[var(--text-muted)]">Loading...</div>}>
      <PatentsContent />
    </Suspense>
  );
}

function PatentsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [params, setParams] = useState<PatentListParams>({
    sort_by: (searchParams.get("sort_by") as PatentListParams["sort_by"]) || "publication_date",
    sort_order: (searchParams.get("sort_order") as PatentListParams["sort_order"]) || "desc",
    page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
    page_size: 20,
  });

  const [filters, setFilters] = useState({
    cpc_prefix: searchParams.get("cpc_prefix") || "",
    assignee: searchParams.get("assignee") || "",
    office: searchParams.get("office") || "",
    min_score: searchParams.get("min_score") || "",
    max_score: searchParams.get("max_score") || "",
  });

  const mergedParams: PatentListParams = {
    ...params,
    ...(filters.cpc_prefix && { cpc_prefix: filters.cpc_prefix }),
    ...(filters.assignee && { assignee: filters.assignee }),
    ...(filters.office && { office: filters.office }),
    ...(filters.min_score && { min_score: Number(filters.min_score) }),
    ...(filters.max_score && { max_score: Number(filters.max_score) }),
  };

  useEffect(() => {
    const sp = new URLSearchParams();
    if (params.sort_by !== "publication_date") sp.set("sort_by", params.sort_by!);
    if (params.sort_order !== "desc") sp.set("sort_order", params.sort_order!);
    if ((params.page ?? 1) > 1) sp.set("page", String(params.page));
    if (filters.cpc_prefix) sp.set("cpc_prefix", filters.cpc_prefix);
    if (filters.assignee) sp.set("assignee", filters.assignee);
    if (filters.office) sp.set("office", filters.office);
    if (filters.min_score) sp.set("min_score", filters.min_score);
    if (filters.max_score) sp.set("max_score", filters.max_score);
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [params, filters, pathname, router]);

  const { data, isLoading, error, mutate } = usePatents(mergedParams);

  const handleSortChange = (sortBy: string) => {
    setParams((prev) => ({
      ...prev,
      sort_by: sortBy as PatentListParams["sort_by"],
      page: 1,
    }));
  };

  const handlePageChange = (page: number) => {
    setParams((prev) => ({ ...prev, page }));
  };

  const handleFilterChange = useCallback(
    (key: keyof typeof filters, value: string) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
      setParams((prev) => ({ ...prev, page: 1 }));
    },
    []
  );

  const hasActiveFilters =
    filters.cpc_prefix || filters.assignee || filters.office || filters.min_score || filters.max_score;

  const clearFilters = () => {
    setFilters({ cpc_prefix: "", assignee: "", office: "", min_score: "", max_score: "" });
    setParams((prev) => ({ ...prev, page: 1 }));
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Patents</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            {data?.total ? `${data.total} patents` : "Browse all patents"}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <select
            value={params.sort_by}
            onChange={(e) => handleSortChange(e.target.value)}
            className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          >
            <option value="publication_date">Publication Date</option>
            <option value="interesting_score">Interest Score</option>
            <option value="opportunity_score">Opportunity Score</option>
            <option value="created_at">Recently Added</option>
          </select>
        </div>
      </div>

      {/* Filter controls */}
      <div className="mb-4 p-4 bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)]">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--text-secondary)]">CPC Prefix</label>
            <input
              type="text"
              placeholder="e.g. G06F"
              value={filters.cpc_prefix}
              onChange={(e) => handleFilterChange("cpc_prefix", e.target.value)}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--text-secondary)]">Assignee</label>
            <input
              type="text"
              placeholder="e.g. Google"
              value={filters.assignee}
              onChange={(e) => handleFilterChange("assignee", e.target.value)}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--text-secondary)]">Office</label>
            <select
              value={filters.office}
              onChange={(e) => handleFilterChange("office", e.target.value)}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="">All</option>
              {OFFICES.map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--text-secondary)]">Score Min</label>
            <input
              type="number"
              min="0"
              max="100"
              placeholder="0"
              value={filters.min_score}
              onChange={(e) => handleFilterChange("min_score", e.target.value)}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--text-secondary)]">Score Max</label>
            <input
              type="number"
              min="0"
              max="100"
              placeholder="100"
              value={filters.max_score}
              onChange={(e) => handleFilterChange("max_score", e.target.value)}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="px-3 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-[var(--border-default)] rounded-lg hover:bg-[var(--bg-glass)]"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {error ? (
        <ErrorState message="Failed to load patents." onRetry={() => mutate()} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(9)].map((_, i) => (
            <PatentCardSkeleton key={i} />
          ))}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon="patent"
          title="No patents found"
          message={hasActiveFilters ? "Try clearing filters or adjusting your sort." : "Check back after the next ingestion run."}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {data?.items.map((patent) => (
              <PatentCard key={patent.id} patent={patent} />
            ))}
          </div>

          {data && data.pages > 1 && (
            <div className="flex justify-center gap-2">
              <button
                onClick={() => handlePageChange(params.page! - 1)}
                disabled={params.page === 1}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-[var(--text-secondary)]">
                Page {params.page} of {data.pages}
              </span>
              <button
                onClick={() => handlePageChange(params.page! + 1)}
                disabled={params.page === data.pages}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
