"use client";

import { useState } from "react";
import Link from "next/link";
import { useExpiry } from "@/hooks/useExpiry";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate, pluralize } from "@/lib/utils";
import type { ExpiryParams } from "@/lib/types";

export default function ExpiryPage() {
  const [params, setParams] = useState<ExpiryParams>({
    days_ahead: 365,
    page: 1,
    page_size: 20,
  });

  const { data, isLoading } = useExpiry(params);

  const handleDaysChange = (days: number) => {
    setParams((prev) => ({ ...prev, days_ahead: days, page: 1 }));
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

        <div className="flex items-center gap-2">
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
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-700">
                    {item.assignees[0] || "—"}
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
