"use client";

import { usePatents, usePatentStats } from "@/hooks/usePatents";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { formatNumber } from "@/lib/utils";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = usePatentStats();
  const { data: patents, isLoading: patentsLoading } = usePatents({
    sort_by: "interesting_score",
    sort_order: "desc",
    page_size: 12,
  });

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
