"use client";

import Link from "next/link";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { useOpportunityList } from "@/hooks/useOpportunity";
import { useHotTrends } from "@/hooks/useTrends";
import { usePriorityWatch } from "@/hooks/usePatents";
import { useSuppliers } from "@/hooks/useSuppliers";
import { formatDate } from "@/lib/utils";

export default function TodayPage() {
  // Data hooks — all existing, all SWR-cached
  const { data: topOpps, isLoading: topOppsLoading } = useOpportunityList({
    tab: "top",
    sort: "opportunity_score",
    page_size: 5,
  });
  const { data: hotTrends, isLoading: trendsLoading } = useHotTrends(undefined, 5);
  const { data: expiring, isLoading: expiringLoading } = usePriorityWatch("expiring_soon", 5);
  const { data: companies, isLoading: companiesLoading } = useSuppliers({
    sort_by: "patent_count",
    sort_order: "desc",
    min_patent_count: 2,
    page_size: 5,
  });

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Today</h1>
        <FreshnessBanner className="mt-2" />
        <p className="text-gray-600 mt-1">
          Your daily patent intelligence briefing
        </p>
      </div>

      <div className="space-y-6">
        {/* Your Patent Pulse — placeholder for Phase 3 topics */}
        <section className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg border border-primary-200 p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white rounded-lg shadow-sm">
              <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Your Patent Pulse</h2>
              <p className="text-sm text-gray-600 mt-1">
                <Link href="/themes" className="text-primary-600 hover:underline">
                  Create topics
                </Link>{" "}
                to track technology areas that matter to you. Matched patents and
                trend signals will appear here automatically.
              </p>
            </div>
          </div>
        </section>

        {/* Top Opportunities */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Top Opportunities</h2>
            <Link href="/opportunity" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {topOppsLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded" />
              ))}
            </div>
          ) : !topOpps?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No opportunity data yet. Run opportunity scoring via Admin → AI Runs.
            </p>
          ) : (
            <div className="space-y-2">
              {topOpps.items.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.title || "Untitled patent"}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.assignees?.[0] || "Unknown"} · {item.doc_id}
                    </p>
                  </div>
                  <OpportunityScoreBadge score={item.opportunity_score} size="sm" />
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Emerging Trends */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Emerging Trends</h2>
            <Link href="/trends" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {trendsLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded" />
              ))}
            </div>
          ) : !hotTrends?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No trend data yet. Run weekly trend computation first.
            </p>
          ) : (
            <div className="space-y-2">
              {hotTrends.items.slice(0, 5).map((item) => (
                <div
                  key={`${item.surface}-${item.key}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="default" size="sm">{item.surface}</Badge>
                      <p className="text-sm font-medium text-gray-900 truncate">{item.key}</p>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.count_4w} patents (4wk) · z-score {item.z_score.toFixed(1)}
                    </p>
                  </div>
                  <div className={`text-sm font-semibold ${item.growth_pct > 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {item.growth_pct > 0 ? "+" : ""}{item.growth_pct.toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Expiring Opportunities */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Expiring Opportunities</h2>
            <Link href="/expiry" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {expiringLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded" />
              ))}
            </div>
          ) : !expiring?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No expiring patents found in the 5-year window.
            </p>
          ) : (
            <div className="space-y-2">
              {expiring.items.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.title || "Untitled patent"}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.assignees?.[0] || "Unknown"} ·{" "}
                      {item.estimated_expiry_date
                        ? `Expires ${formatDate(item.estimated_expiry_date)}`
                        : "No expiry data"}
                    </p>
                  </div>
                  {item.opportunity_score != null && (
                    <OpportunityScoreBadge score={item.opportunity_score} size="sm" />
                  )}
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Companies Moving */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Companies Moving</h2>
            <Link href="/companies" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {companiesLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded" />
              ))}
            </div>
          ) : !companies?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No company data available yet.
            </p>
          ) : (
            <div className="space-y-2">
              {companies.items.slice(0, 5).map((item) => (
                <Link
                  key={item.name}
                  href={`/companies/${encodeURIComponent(item.name)}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.active_patent_count} active · {item.technology_area_count} tech areas
                      {item.country ? ` · ${item.country}` : ""}
                    </p>
                  </div>
                  <span className={`text-sm font-semibold ${item.supplier_score >= 60 ? "text-green-600" : item.supplier_score >= 35 ? "text-yellow-600" : "text-gray-500"}`}>
                    {item.supplier_score}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
