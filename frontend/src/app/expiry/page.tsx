"use client";

import { useState } from "react";
import Link from "next/link";
import { useExpiry } from "@/hooks/useExpiry";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate, pluralize } from "@/lib/utils";
import type { ExpiryItem, ExpiryParams } from "@/lib/types";

export default function ExpiryPage() {
  const [params, setParams] = useState<ExpiryParams>({
    days_ahead: 365,
    sort_by: "expiry_urgency",
    sort_order: "asc",
    page: 1,
    page_size: 20,
  });

  const { data, isLoading } = useExpiry(params);

  const handleDaysChange = (days: number) => {
    setParams((prev) => ({ ...prev, days_ahead: days, page: 1 }));
  };

  const handleFilterChange = (key: keyof ExpiryParams, value: string | undefined) => {
    setParams((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handleSortChange = (sort_by: string, sort_order: string) => {
    setParams((prev) => ({ ...prev, sort_by, sort_order, page: 1 }));
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Expiry Watch</h1>
          <p className="text-gray-600 mt-1">
            {data?.total
              ? `${data.total} patents expiring soon`
              : "Track patents approaching expiration"}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-gray-500">Show patents expiring in:</span>
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
            <option value="AI & Data">AI & Data</option>
            <option value="Biotech & Healthcare">Biotech & Healthcare</option>
            <option value="Energy & Environment">Energy & Environment</option>
            <option value="Manufacturing & Materials">Manufacturing & Materials</option>
            <option value="Semiconductors">Semiconductors</option>
            <option value="Telecom & Networking">Telecom & Networking</option>
          </select>

          <select
            value={params.time_horizon || ""}
            onChange={(e) => handleFilterChange("time_horizon", e.target.value || undefined)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All time horizons</option>
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
            <option value="expiry_urgency|asc">Expiring soonest first</option>
            <option value="opportunity_score|desc">Highest opportunity</option>
            <option value="expiry_date|asc">Expiry date (asc)</option>
            <option value="expiry_date|desc">Expiry date (desc)</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Patent
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Assignee
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Expiry Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Time Remaining
                </th>
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-t border-gray-200">
                  <td className="px-4 py-4">
                    <Skeleton className="h-5 w-48" />
                  </td>
                  <td className="px-4 py-4">
                    <Skeleton className="h-5 w-32" />
                  </td>
                  <td className="px-4 py-4">
                    <Skeleton className="h-5 w-12" />
                  </td>
                  <td className="px-4 py-4">
                    <Skeleton className="h-5 w-24" />
                  </td>
                  <td className="px-4 py-4">
                    <Skeleton className="h-6 w-20 rounded-full" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No patents expiring in this timeframe</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Patent
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Assignee
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Expiry Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Time Remaining
                </th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((item) => (
                <tr
                  key={item.id}
                  className="border-t border-gray-200 hover:bg-gray-50"
                >
                  <td className="px-4 py-4">
                    <Link
                      href={`/patents/${item.id}`}
                      className="text-primary-600 hover:text-primary-700 font-medium"
                    >
                      {item.doc_id}
                    </Link>
                    {item.title && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-1">
                        {item.title}
                      </p>
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
      )}
    </div>
  );
}

function ExpiryBadge({ days }: { days: number | null }) {
  if (days === null) return <Badge variant="default">Unknown</Badge>;

  let variant: "danger" | "warning" | "default" = "default";
  if (days <= 90) variant = "danger";
  else if (days <= 180) variant = "warning";

  return (
    <Badge variant={variant}>
      {days} {pluralize(days, "day")}
    </Badge>
  );
}

function OpportunityScore({ item }: { item: ExpiryItem }) {
  if (item.opportunity_score === null || item.opportunity_score === undefined) {
    return <span className="text-sm text-gray-400">—</span>;
  }
  const color =
    item.opportunity_score >= 70
      ? "text-emerald-700"
      : item.opportunity_score >= 50
      ? "text-amber-700"
      : "text-gray-600";
  return (
    <span className={`text-sm font-semibold ${color}`}>
      {item.opportunity_score.toFixed(0)}
    </span>
  );
}

function ExpiryTags({ item }: { item: ExpiryItem }) {
  const tags = [];
  if (
    item.opportunity_score !== null &&
    item.opportunity_score !== undefined &&
    item.opportunity_score >= 60 &&
    (!item.tags?.risk_flags || item.tags.risk_flags.length === 0)
  ) {
    tags.push(
      <Badge key="revival" variant="default" size="sm" className="bg-emerald-100 text-emerald-800 border-emerald-200">
        Revival
      </Badge>
    );
  }
  if (item.tags?.industries && item.tags.industries.length > 0) {
    item.tags.industries.slice(0, 2).forEach((ind: string) => {
      tags.push(
        <Badge key={ind} variant="default" size="sm">
          {ind}
        </Badge>
      );
    });
  }
  if (item.tags?.time_horizon) {
    tags.push(
      <Badge key="horizon" variant="default" size="sm">
        {item.tags.time_horizon.replace("_", " ")}
      </Badge>
    );
  }
  return <>{tags}</>;
}
