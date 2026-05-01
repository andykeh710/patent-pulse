"use client";

import { useState } from "react";
import { usePatents, usePatentStats, useExpirySummary, usePatentTrend, usePriorityWatch } from "@/hooks/usePatents";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { formatNumber } from "@/lib/utils";
import type { TrendPoint } from "@/lib/types";

export default function DashboardPage() {
  const [priorityBucket, setPriorityBucket] = useState<"expiring_soon" | "recent" | "all">("expiring_soon");
  const { data: stats, isLoading: statsLoading } = usePatentStats();
  const { data: patents, isLoading: patentsLoading } = usePatents({
    sort_by: "interesting_score",
    sort_order: "desc",
    page_size: 12,
  });
  const { data: expirySummary, isLoading: expiryLoading } = useExpirySummary();
  const { data: trend, isLoading: trendLoading } = usePatentTrend();
  const { data: priority, isLoading: priorityLoading } = usePriorityWatch(priorityBucket, 12);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Patent intelligence at a glance
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Patents"
          value={stats?.total_patents}
          isLoading={statsLoading}
        />
        <StatCard
          label="Grants"
          value={stats?.total_grants}
          isLoading={statsLoading}
        />
        <StatCard
          label="Applications"
          value={stats?.total_applications}
          isLoading={statsLoading}
        />
        <StatCard
          label="This Week"
          value={stats?.patents_this_week}
          isLoading={statsLoading}
          highlight
        />
      </div>

      {/* Priority Watch — patents that need immediate attention */}
      <div className="mb-6 bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Priority Watch</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {priorityBucket === "expiring_soon" && "Granted patents expiring within 5 years, soonest first"}
              {priorityBucket === "recent" && "Patents published in the last 90 days, ranked by interest score"}
              {priorityBucket === "all" && "Combined view: top expiring + most recent"}
            </p>
          </div>
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setPriorityBucket("expiring_soon")}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                priorityBucket === "expiring_soon"
                  ? "bg-white text-primary-700 shadow-sm font-medium"
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              Expiring Soon
            </button>
            <button
              onClick={() => setPriorityBucket("recent")}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                priorityBucket === "recent"
                  ? "bg-white text-primary-700 shadow-sm font-medium"
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              Recent
            </button>
            <button
              onClick={() => setPriorityBucket("all")}
              className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                priorityBucket === "all"
                  ? "bg-white text-primary-700 shadow-sm font-medium"
                  : "text-gray-600 hover:text-gray-800"
              }`}
            >
              All
            </button>
          </div>
        </div>
        {priorityLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {[...Array(6)].map((_, i) => (
              <PatentCardSkeleton key={i} />
            ))}
          </div>
        ) : (priority?.items?.length ?? 0) === 0 ? (
          <div className="text-center py-8 text-sm text-gray-400">
            No patents in this bucket yet
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {priority?.items.map((patent) => (
              <PatentCard key={patent.id} patent={patent} />
            ))}
          </div>
        )}
        {priority && priority.total > 12 && (
          <p className="text-xs text-gray-400 mt-3 text-right">
            Showing 12 of {priority.total.toLocaleString()} patents
          </p>
        )}
      </div>

      {/* AI Summarization Progress */}
      <div className="mb-6 bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">AI Summaries</span>
          <span className="text-sm text-gray-500">
            {stats?.summarized_count ?? 0} / {stats?.total_patents ?? 0}
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-2 bg-primary-500 rounded-full transition-all duration-500"
            style={{
              width: `${stats && stats.total_patents > 0
                ? Math.round((stats.summarized_count / stats.total_patents) * 100)
                : 0}%`
            }}
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {stats && stats.total_patents > 0
            ? `${Math.round((stats.summarized_count / stats.total_patents) * 100)}% complete`
            : "No patents ingested yet"}
        </p>
      </div>

      {/* Expiry Summary */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Patent Expiry Outlook</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard label="Expiring in 5 Years" value={expirySummary?.within_5_years} isLoading={expiryLoading} highlight />
          <StatCard label="Expiring in 10 Years" value={expirySummary?.within_10_years} isLoading={expiryLoading} />
          <StatCard label="Expiring in 20 Years" value={expirySummary?.within_20_years} isLoading={expiryLoading} />
          <StatCard label="Total with Expiry" value={expirySummary?.total_with_expiry} isLoading={expiryLoading} />
        </div>
      </div>

      {/* Publication Trend */}
      <div className="mb-6 bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Publication Trend</h2>
        {trendLoading ? (
          <div className="h-32 bg-gray-50 rounded animate-pulse" />
        ) : trend && trend.points.length > 0 ? (
          <TrendChart points={trend.points} />
        ) : (
          <p className="text-sm text-gray-400 text-center py-8">No trend data yet</p>
        )}
      </div>

      {/* Top CPC Sections & Top Assignees */}
      {((stats?.top_cpc_sections?.length ?? 0) > 0 || (stats?.top_assignees?.length ?? 0) > 0) && (
        <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Top CPC Sections */}
          {(stats?.top_cpc_sections?.length ?? 0) > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Technology Sections</h3>
              <div className="space-y-2">
                {(stats?.top_cpc_sections ?? []).map((item: { section: string; count: number }) => {
                  const pct = Math.round((item.count / (stats?.total_patents || 1)) * 100);
                  return (
                    <div key={item.section} className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-primary-700 w-6">{item.section}</span>
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-2 bg-primary-300 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-500 w-12 text-right">{item.count.toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {/* Top Assignees */}
          {(stats?.top_assignees?.length ?? 0) > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Patent Holders</h3>
              <div className="space-y-2">
                {(stats?.top_assignees ?? []).map((item: { assignee: string; count: number }, idx: number) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-4">{idx + 1}.</span>
                    <span className="text-xs text-gray-700 flex-1 truncate">{item.assignee}</span>
                    <span className="text-xs text-gray-500 shrink-0">{item.count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Top Patents by Interest Score
        </h2>

        {patentsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <PatentCardSkeleton key={i} />
            ))}
          </div>
        ) : patents?.items.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <p className="text-gray-500">No patents found</p>
            <p className="text-sm text-gray-400 mt-1">
              Patents will appear here after ingestion
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {patents?.items.map((patent) => (
              <PatentCard key={patent.id} patent={patent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  isLoading,
  highlight,
}: {
  label: string;
  value?: number;
  isLoading: boolean;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        highlight
          ? "bg-primary-50 border-primary-200"
          : "bg-white border-gray-200"
      }`}
    >
      <p className="text-sm text-gray-500">{label}</p>
      {isLoading ? (
        <div className="h-8 w-20 bg-gray-200 animate-pulse rounded mt-1" />
      ) : (
        <p
          className={`text-2xl font-bold ${
            highlight ? "text-primary-700" : "text-gray-900"
          }`}
        >
          {value !== undefined ? formatNumber(value) : "—"}
        </p>
      )}
    </div>
  );
}

function TrendChart({ points }: { points: TrendPoint[] }) {
  const max = Math.max(...points.map((p) => p.count), 1);
  return (
    <div className="flex items-end gap-1 h-32">
      {points.map((p) => (
        <div key={p.period} className="flex-1 flex flex-col items-center gap-1 min-w-0">
          <span className="text-xs text-gray-500 font-medium">{p.count.toLocaleString()}</span>
          <div
            className="w-full bg-primary-400 hover:bg-primary-500 rounded-t transition-colors"
            style={{ height: `${Math.max((p.count / max) * 100, 2)}%` }}
            title={`${p.period}: ${p.count}`}
          />
          <span className="text-[10px] text-gray-400 truncate w-full text-center">
            {p.period.slice(5)}
          </span>
        </div>
      ))}
    </div>
  );
}
