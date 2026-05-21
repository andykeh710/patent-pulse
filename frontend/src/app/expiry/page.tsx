"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useExpiry } from "@/hooks/useExpiry";
import { useCliffs } from "@/hooks/useTrends";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { formatDate, pluralize } from "@/lib/utils";
import type { ExpiryItem, ExpiryParams, CliffClusterItem } from "@/lib/types";

const CPC_LABELS: Record<string, string> = {
  A61B: "Medical Diagnostics", A61F: "Medical Implants", A61K: "Pharma",
  A61M: "Medical Devices", B01D: "Filtration", B32B: "Layered Materials",
  B60W: "Vehicle Control", C12N: "Biotech", G06F: "Computing",
  G06T: "Image Processing", G09G: "Display Control", H01M: "Batteries",
  H04L: "Networking", H04W: "Wireless", H10W: "Semiconductors",
  Y02E: "Clean Energy", Y10T: "Technical Subjects",
};

export default function ExpiryPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-400">Loading...</div>}>
      <ExpiryContent />
    </Suspense>
  );
}

function ExpiryContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [params, setParams] = useState<ExpiryParams>({
    days_ahead: searchParams.get("days_ahead") ? Number(searchParams.get("days_ahead")) : 1825,
    industry: searchParams.get("industry") || undefined,
    time_horizon: searchParams.get("time_horizon") || undefined,
    sort_by: searchParams.get("sort_by") || "expiry_urgency",
    sort_order: searchParams.get("sort_order") || "asc",
    page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
    page_size: 20,
  });

  const syncURL = useCallback(
    (p: ExpiryParams) => {
      const sp = new URLSearchParams();
      if (p.days_ahead !== 1825) sp.set("days_ahead", String(p.days_ahead));
      if (p.industry) sp.set("industry", p.industry);
      if (p.time_horizon) sp.set("time_horizon", p.time_horizon);
      if (p.sort_by !== "expiry_urgency") sp.set("sort_by", p.sort_by!);
      if (p.sort_order !== "asc") sp.set("sort_order", p.sort_order!);
      if ((p.page ?? 1) > 1) sp.set("page", String(p.page));
      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router]
  );

  useEffect(() => {
    syncURL(params);
  }, [params, syncURL]);

  const { data, isLoading } = useExpiry(params);
  const { data: cliffs12 } = useCliffs(12, 5, 6);
  const { data: cliffs24 } = useCliffs(24, 5, 6);

  const handleDaysChange = (days: number) =>
    setParams((prev) => ({ ...prev, days_ahead: days, page: 1 }));
  const handleFilterChange = (key: keyof ExpiryParams, value: string | undefined) =>
    setParams((prev) => ({ ...prev, [key]: value, page: 1 }));
  const handleSortChange = (sort_by: string, sort_order: string) =>
    setParams((prev) => ({ ...prev, sort_by, sort_order, page: 1 }));
  const handlePageChange = (page: number) =>
    setParams((prev) => ({ ...prev, page }));

  const topCliffs = [...(cliffs12?.items || []), ...(cliffs24?.items || [])]
    .sort((a, b) => b.patent_count - a.patent_count)
    .slice(0, 4);

  return (
    <div>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Expiry Watch</h1>
          <FreshnessBanner show={["patents"]} className="mt-2" />
          <p className="text-gray-600 mt-1">
            {data?.total
              ? `${data.total.toLocaleString()} patents expiring in this window`
              : "Track patents approaching expiration"}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          <select
            value={params.days_ahead}
            onChange={(e) => handleDaysChange(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value={90}>90 days</option>
            <option value={180}>180 days</option>
            <option value={365}>1 year</option>
            <option value={730}>2 years</option>
            <option value={1825}>5 years</option>
            <option value={3650}>10 years</option>
            <option value={7300}>All</option>
          </select>

          <select
            value={params.industry || ""}
            onChange={(e) => handleFilterChange("industry", e.target.value || undefined)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All industries</option>
            <option value="healthcare">Healthcare</option>
            <option value="pharma">Pharma</option>
            <option value="biotech">Biotech</option>
            <option value="energy">Energy</option>
            <option value="semiconductors">Semiconductors</option>
            <option value="ai_ml">AI / ML</option>
            <option value="automotive">Automotive</option>
            <option value="telecom">Telecom</option>
            <option value="manufacturing">Manufacturing</option>
          </select>

          <select
            value={params.time_horizon || ""}
            onChange={(e) => handleFilterChange("time_horizon", e.target.value || undefined)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All horizons</option>
            <option value="now">Now</option>
            <option value="near_term">Near-term</option>
            <option value="long_term">Long-term</option>
          </select>

          <select
            value={`${params.sort_by || "expiry_urgency"}|${params.sort_order || "asc"}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split("|");
              handleSortChange(sb, so);
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="expiry_urgency|asc">Expiring soonest</option>
            <option value="opportunity_score|desc">Highest opportunity</option>
            <option value="expiry_date|asc">Expiry date (asc)</option>
            <option value="expiry_date|desc">Expiry date (desc)</option>
          </select>
        </div>
      </div>

      {/* Patent Cliff Highlights */}
      {topCliffs.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Technology Openings — Patent Cliff Clusters
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {topCliffs.map((cliff) => (
              <CliffCard key={cliff.id} cliff={cliff} />
            ))}
          </div>
        </div>
      )}

      {/* Expiry table */}
      {isLoading ? (
        <TableSkeleton />
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No patents expiring in this timeframe</p>
          <p className="text-sm text-gray-400 mt-1">Try expanding the time window</p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patent</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expiry Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time Remaining</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((item) => (
                  <tr key={item.id} className="border-t border-gray-200 hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <Link
                        href={`/patents/${item.id}`}
                        className="text-primary-600 hover:text-primary-700 font-medium"
                      >
                        {item.doc_id}
                      </Link>
                      {item.title && (
                        <p className="text-sm text-gray-500 mt-1 line-clamp-1">{item.title}</p>
                      )}
                      <div className="flex flex-wrap gap-1 mt-1">
                        <ExpiryTags item={item} />
                      </div>
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-700">
                      {item.assignees[0] || "—"}
                    </td>
                    <td className="px-4 py-4">
                      <OpportunityScore item={item} />
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-700">
                      {formatDate(item.estimated_expiry_date)}
                    </td>
                    <td className="px-4 py-4">
                      <ExpiryBadge days={item.days_until_expiry} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {data.page} of {data.pages} ({data.total.toLocaleString()} total)
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => handlePageChange(params.page! - 1)}
                  disabled={params.page === 1}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => handlePageChange(params.page! + 1)}
                  disabled={params.page === data.pages}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CliffCard({ cliff }: { cliff: CliffClusterItem }) {
  const label = CPC_LABELS[cliff.key_value] || cliff.key_value;
  const windowLabel = cliff.window_months < 12
    ? `${cliff.window_months}mo`
    : `${cliff.window_months / 12}yr`;

  return (
    <Link
      href={`/trends`}
      className="block rounded-lg border border-primary-200 bg-primary-50 p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="font-mono text-sm font-bold text-primary-700">{cliff.key_value}</span>
          <p className="text-xs text-gray-600 mt-0.5">{label}</p>
        </div>
        <Badge variant="default" size="sm">{windowLabel}</Badge>
      </div>
      <div className="mt-2">
        <span className="text-2xl font-bold text-primary-700">{cliff.patent_count}</span>
        <span className="text-xs text-gray-500 ml-1">patents expiring</span>
      </div>
    </Link>
  );
}

function TableSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patent</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expiry Date</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time Remaining</th>
          </tr>
        </thead>
        <tbody>
          {[...Array(5)].map((_, i) => (
            <tr key={i} className="border-t border-gray-200">
              <td className="px-4 py-4"><Skeleton className="h-5 w-48" /></td>
              <td className="px-4 py-4"><Skeleton className="h-5 w-32" /></td>
              <td className="px-4 py-4"><Skeleton className="h-5 w-12" /></td>
              <td className="px-4 py-4"><Skeleton className="h-5 w-24" /></td>
              <td className="px-4 py-4"><Skeleton className="h-6 w-20 rounded-full" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExpiryBadge({ days }: { days: number | null }) {
  if (days === null) return <Badge variant="default">Unknown</Badge>;
  let variant: "danger" | "warning" | "default" = "default";
  if (days <= 90) variant = "danger";
  else if (days <= 365) variant = "warning";
  return (
    <Badge variant={variant}>
      {days > 365
        ? `${(days / 365).toFixed(1)} yr`
        : `${days} ${pluralize(days, "day")}`}
    </Badge>
  );
}

function OpportunityScore({ item }: { item: ExpiryItem }) {
  if (item.opportunity_score === null || item.opportunity_score === undefined) {
    return <span className="text-sm text-gray-400">—</span>;
  }
  const color =
    item.opportunity_score >= 70 ? "text-emerald-700"
    : item.opportunity_score >= 50 ? "text-amber-700"
    : "text-gray-600";
  return (
    <span className={`text-sm font-semibold ${color}`}>
      {item.opportunity_score.toFixed(0)}
    </span>
  );
}

function ExpiryTags({ item }: { item: ExpiryItem }) {
  const badges = [];
  if (
    item.opportunity_score != null &&
    item.opportunity_score >= 50 &&
    (!item.tags?.risk_flags || item.tags.risk_flags.length === 0)
  ) {
    badges.push(
      <Badge key="revival" variant="default" size="sm" className="bg-emerald-100 text-emerald-800 border-emerald-200">
        Revival candidate
      </Badge>
    );
  }
  if (item.tags?.industries) {
    item.tags.industries.slice(0, 2).forEach((ind: string) => {
      badges.push(
        <Badge key={ind} variant="default" size="sm">{ind}</Badge>
      );
    });
  }
  if (item.tags?.time_horizon) {
    badges.push(
      <Badge key="horizon" variant="default" size="sm">
        {item.tags.time_horizon.replace("_", " ")}
      </Badge>
    );
  }
  return <>{badges}</>;
}
