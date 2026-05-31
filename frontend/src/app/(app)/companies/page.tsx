"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { useSupplierMap, useSupplierSummary, useSuppliers } from "@/hooks/useSuppliers";
import { formatNumber, humanizeTag } from "@/lib/utils";
import type { SupplierItem, SupplierListParams, SupplierMapCountry } from "@/lib/types";

export default function CompaniesPage() {
  const [params, setParams] = useState<SupplierListParams>({
    sort_by: "supplier_score",
    sort_order: "desc",
    page: 1,
    page_size: 20,
  });

  const { data: summary, isLoading: summaryLoading } = useSupplierSummary();
  const { data: suppliers, isLoading: suppliersLoading } = useSuppliers(params);
  const { data: mapData, isLoading: mapLoading } = useSupplierMap();

  const handleFilterChange = (next: Partial<SupplierListParams>) => {
    setParams((prev) => ({ ...prev, ...next, page: 1 }));
  };

  const handlePageChange = (page: number) => {
    setParams((prev) => ({ ...prev, page }));
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Companies / Assignees</h1>
        <FreshnessBanner show={["patents"]} className="mt-2" />
        <p className="text-gray-600 mt-1">
          Portfolio strength, opportunity exposure, geographic coverage, and risk from patent assignee data
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <SummaryCard label="Total Companies" value={summary?.total_suppliers} isLoading={summaryLoading} />
        <SummaryCard label="Company Patents" value={summary?.total_supplier_patents} isLoading={summaryLoading} />
        <SummaryCard label="High-Score Companies" value={summary?.high_opportunity_suppliers} isLoading={summaryLoading} highlight />
        <SummaryCard label="Avg. Patents / Company" value={summary?.average_patents_per_supplier} isLoading={summaryLoading} decimals />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <SupplierDistribution items={mapData || []} isLoading={mapLoading} />

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Data Coverage</h2>
          <p className="text-xs text-gray-500 mb-4">Uses normalized assignee metadata when available, with patent assignee aggregation as fallback.</p>
          <div className="space-y-4">
            <CoverageBar label="Country Coverage" value={summary?.suppliers_with_country || 0} total={summary?.total_suppliers || 0} />
            <CoverageBar label="Entity Type Coverage" value={summary?.suppliers_with_entity_type || 0} total={summary?.total_suppliers || 0} />
          </div>
          {(summary?.entity_types?.length ?? 0) > 0 && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Entity Mix</h3>
              <div className="flex flex-wrap gap-2">
                {summary?.entity_types.map((item) => (
                  <Badge key={item.entity_type} variant="default" size="sm">
                    {humanizeTag(item.entity_type)} · {item.count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Company Rankings</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Composite score blends patent volume, active grants, technology breadth, signal score, and near-term expiry exposure.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={params.country || ""}
              onChange={(e) => handleFilterChange({ country: e.target.value || undefined })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Countries</option>
              {summary?.countries.map((item) => (
                <option key={item.country} value={item.country}>{item.country}</option>
              ))}
            </select>
            <select
              value={params.sort_by}
              onChange={(e) => handleFilterChange({ sort_by: e.target.value as SupplierListParams["sort_by"] })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="supplier_score">Company Score</option>
              <option value="patent_count">Patent Count</option>
              <option value="active_patent_count">Active Patents</option>
              <option value="average_signal_score">Avg. Signal Score</option>
            </select>
            <select
              value={params.min_patent_count || 1}
              onChange={(e) => handleFilterChange({ min_patent_count: Number(e.target.value) })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value={1}>1+ Patents</option>
              <option value={2}>2+ Patents</option>
              <option value={5}>5+ Patents</option>
              <option value={10}>10+ Patents</option>
            </select>
          </div>
        </div>
      </div>

      <SupplierTable items={suppliers?.items || []} isLoading={suppliersLoading} />

      {suppliers && suppliers.pages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => handlePageChange((params.page || 1) - 1)}
            disabled={params.page === 1}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Page {params.page} of {suppliers.pages}
          </span>
          <button
            onClick={() => handlePageChange((params.page || 1) + 1)}
            disabled={params.page === suppliers.pages}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, isLoading, highlight, decimals }: { label: string; value?: number; isLoading: boolean; highlight?: boolean; decimals?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${highlight ? "bg-primary-50 border-primary-200" : "bg-white border-gray-200"}`}>
      <p className="text-sm text-gray-500">{label}</p>
      {isLoading ? (
        <div className="h-8 w-20 bg-gray-200 animate-pulse rounded mt-1" />
      ) : (
        <p className={`text-2xl font-bold ${highlight ? "text-primary-700" : "text-gray-900"}`}>
          {value !== undefined ? decimals ? value.toFixed(2) : formatNumber(value) : "—"}
        </p>
      )}
    </div>
  );
}

function SupplierDistribution({ items, isLoading }: { items: SupplierMapCountry[]; isLoading: boolean }) {
  const max = Math.max(...items.map((item) => item.patent_count), 1);

  return (
    <div className="xl:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Company Geography</h2>
          <p className="text-xs text-gray-500 mt-0.5">Country-level company distribution from patent assignee metadata.</p>
        </div>
        <Badge variant="default" size="sm">Map-ready data</Badge>
      </div>
      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : items.length === 0 ? (
        <div className="h-64 rounded-lg bg-gray-50 flex items-center justify-center text-sm text-gray-400">
          No country metadata available yet
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="h-64 rounded-lg bg-gradient-to-br from-primary-50 to-blue-50 border border-primary-100 p-4 relative overflow-hidden">
            {items.slice(0, 8).map((item, idx) => {
              const size = 36 + Math.round((item.patent_count / max) * 54);
              return (
                <div
                  key={item.country}
                  className="absolute rounded-full bg-primary-500/80 text-white flex items-center justify-center text-xs font-semibold shadow-sm"
                  style={{
                    width: size,
                    height: size,
                    left: `${8 + (idx % 4) * 23}%`,
                    top: `${12 + Math.floor(idx / 4) * 42}%`,
                  }}
                  title={`${item.country}: ${item.patent_count} patents`}
                >
                  {item.country.slice(0, 3).toUpperCase()}
                </div>
              );
            })}
          </div>
          <div className="space-y-3">
            {items.slice(0, 6).map((item) => (
              <div key={item.country}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700">{item.country}</span>
                  <span className="text-gray-500">{formatNumber(item.patent_count)} patents</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-2 bg-primary-400 rounded-full" style={{ width: `${Math.max((item.patent_count / max) * 100, 3)}%` }} />
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {item.supplier_count} companies · avg score {item.average_supplier_score}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CoverageBar({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-gray-700">{label}</span>
        <span className="text-gray-500">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-2 bg-primary-400 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-400 mt-1">{formatNumber(value)} of {formatNumber(total)} companies</p>
    </div>
  );
}

function SupplierTable({ items, isLoading }: { items: SupplierItem[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-lg" />)}
      </div>
    );
  }

  if (items.length === 0) {
    return <div className="text-center py-12 bg-gray-50 rounded-lg text-gray-500">No companies found for the selected filters.</div>;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Profile</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Patents</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Active</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Tech Breadth</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Expiry Risk</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((item) => (
              <tr key={item.name} className="hover:bg-gray-50">
                <td className="px-4 py-4">
                  <Link
                    href={`/companies/${encodeURIComponent(item.name)}`}
                    className="text-sm font-medium text-primary-700 hover:text-primary-900 hover:underline max-w-xs truncate block"
                  >
                    {item.name}
                  </Link>
                  <p className="text-xs text-gray-500">Avg signal {item.average_signal_score ?? "—"}</p>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1.5">
                    {item.country && <Badge variant="default" size="sm">{item.country}</Badge>}
                    {item.entity_type && <Badge variant="default" size="sm">{humanizeTag(item.entity_type)}</Badge>}
                    {!item.country && !item.entity_type && <span className="text-xs text-gray-400">Metadata pending</span>}
                  </div>
                </td>
                <td className="px-4 py-4 text-right">
                  <span className={`text-sm font-semibold ${item.supplier_score >= 60 ? "text-green-600" : item.supplier_score >= 35 ? "text-yellow-600" : "text-gray-500"}`}>
                    {item.supplier_score}
                  </span>
                </td>
                <td className="px-4 py-4 text-right text-sm text-gray-700">{formatNumber(item.patent_count)}</td>
                <td className="px-4 py-4 text-right text-sm text-gray-700">{formatNumber(item.active_patent_count)}</td>
                <td className="px-4 py-4 text-right text-sm text-gray-700">{formatNumber(item.technology_area_count)}</td>
                <td className="px-4 py-4 text-right text-sm text-gray-700">{formatNumber(item.expiring_soon_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <SourceAttribution />
      </div>
    </div>
  );
}
