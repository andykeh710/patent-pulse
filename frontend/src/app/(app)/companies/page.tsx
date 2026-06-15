"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { PageHeader } from "@/components/ui/PageHeader";
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
      <PageHeader
        title="Companies / Assignees"
        description="Portfolio strength, opportunity exposure, geographic coverage, and risk from patent assignee data."
        freshnessSources={["patents"]}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <SummaryCard label="Total Companies" value={summary?.total_suppliers} isLoading={summaryLoading} />
        <SummaryCard label="Company Patents" value={summary?.total_supplier_patents} isLoading={summaryLoading} />
        <SummaryCard label="High-Score Companies" value={summary?.high_opportunity_suppliers} isLoading={summaryLoading} highlight />
        <SummaryCard label="Avg. Patents / Company" value={summary?.average_patents_per_supplier} isLoading={summaryLoading} decimals />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <SupplierDistribution items={mapData || []} isLoading={mapLoading} />

        <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-1">Data Coverage</h2>
          <p className="text-xs text-[var(--text-muted)] mb-4">Uses normalized assignee metadata when available, with patent assignee aggregation as fallback.</p>
          <div className="space-y-4">
            <CoverageBar label="Country Coverage" value={summary?.suppliers_with_country || 0} total={summary?.total_suppliers || 0} isLoading={summaryLoading} enrichmentNote="Country detection requires external data sources (not available from patent office feeds). Planned for a future data enrichment sprint." />
            <CoverageBar label="Entity Type Coverage" value={summary?.suppliers_with_entity_type || 0} total={summary?.total_suppliers || 0} isLoading={summaryLoading} enrichmentNote="Entity type classification is computed nightly from company name patterns. If zero, the backfill has not yet run on this dataset." />
          </div>
          {(summary?.entity_types?.length ?? 0) > 0 && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Entity Mix</h3>
              <div className="flex flex-wrap gap-2">
                {summary?.entity_types.map((item, i) => (
                  <Badge key={`entity-${item.entity_type}-${i}`} variant="default" size="sm">
                    {humanizeTag(item.entity_type)} · {item.count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 mb-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Company Rankings</h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              Composite score blends patent volume, active grants, technology breadth, signal score, and near-term expiry exposure.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={params.country || ""}
              onChange={(e) => handleFilterChange({ country: e.target.value || undefined })}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="">All Countries</option>
              {summary?.countries.map((item, i) => (
                <option key={`country-${item.country}-${i}`} value={item.country}>{item.country}</option>
              ))}
            </select>
            <select
              value={params.sort_by}
              onChange={(e) => handleFilterChange({ sort_by: e.target.value as SupplierListParams["sort_by"] })}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="supplier_score">Company Score</option>
              <option value="patent_count">Patent Count</option>
              <option value="active_patent_count">Active Patents</option>
              <option value="average_signal_score">Avg. Signal Score</option>
            </select>
            <select
              value={params.min_patent_count || 1}
              onChange={(e) => handleFilterChange({ min_patent_count: Number(e.target.value) })}
              className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
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
            className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-[var(--text-secondary)]">
            Page {params.page} of {suppliers.pages}
          </span>
          <button
            onClick={() => handlePageChange((params.page || 1) + 1)}
            disabled={params.page === suppliers.pages}
            className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
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
    <div className={`rounded-lg border p-4 ${highlight ? "bg-[var(--bg-elevated)] border-border-[var(--accent)]/20" : "bg-[var(--bg-surface)] border-[var(--border-subtle)]"}`}>
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
      {isLoading ? (
        <div className="h-8 w-20 bg-[var(--bg-surface)] animate-pulse rounded mt-1" />
      ) : (
        <p className={`text-2xl font-bold ${highlight ? "text-[var(--accent)]" : "text-[var(--text-primary)]"}`}>
          {value !== undefined ? decimals ? value.toFixed(2) : formatNumber(value) : "—"}
        </p>
      )}
    </div>
  );
}

function SupplierDistribution({ items, isLoading }: { items: SupplierMapCountry[]; isLoading: boolean }) {
  const max = Math.max(...items.map((item) => item.patent_count), 1);

  return (
    <div className="xl:col-span-2 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Company Geography</h2>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">Country-level company distribution from patent assignee metadata.</p>
        </div>
        <Badge variant="default" size="sm">Map-ready data</Badge>
      </div>
      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : items.length === 0 ? (
        <div className="h-64 rounded-lg bg-[var(--bg-base)] flex items-center justify-center text-sm text-[var(--text-muted)]">
          No country metadata available yet
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="h-64 rounded-lg bg-gradient-to-br from-bg-[var(--bg-elevated)] to-[var(--bg-surface)] border border-bg-[var(--accent-muted)] p-4 relative overflow-hidden">
            {items.slice(0, 8).map((item, idx) => {
              const size = 36 + Math.round((item.patent_count / max) * 54);
              return (
                <div
                  key={`country-bubble-${item.country}-${idx}`}
                  className="absolute rounded-full bg-[var(--bg-elevated)]0/80 text-white flex items-center justify-center text-xs font-semibold shadow-sm"
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
            {items.slice(0, 6).map((item, i) => (
              <div key={`country-bar-${item.country}-${i}`}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium text-[var(--text-secondary)]">{item.country}</span>
                  <span className="text-[var(--text-muted)]">{formatNumber(item.patent_count)} patents</span>
                </div>
                <div className="h-2 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                  <div className="h-2 bg-bg-[var(--accent)]/70 rounded-full" style={{ width: `${Math.max((item.patent_count / max) * 100, 3)}%` }} />
                </div>
                <p className="text-xs text-[var(--text-muted)] mt-1">
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

function CoverageBar({ label, value, total, isLoading, enrichmentNote }: { label: string; value: number; total: number; isLoading?: boolean; enrichmentNote?: string }) {
  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between text-sm mb-1">
          <Skeleton className="h-4 w-28 rounded" />
          <Skeleton className="h-4 w-8 rounded" />
        </div>
        <Skeleton className="h-2 w-full rounded-full" />
        <Skeleton className="h-3 w-40 rounded mt-1" />
      </div>
    );
  }

  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="text-[var(--text-secondary)]">{label}</span>
        <span className="text-[var(--text-muted)]">{pct}%</span>
      </div>
      <div className="h-2 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
        <div className="h-2 bg-bg-[var(--accent)]/70 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-[var(--text-muted)] mt-1">
        {formatNumber(value)} of {formatNumber(total)} companies
      </p>
      {enrichmentNote && value === 0 && total > 0 && (
        <p className="text-xs text-[var(--text-muted)] mt-1 italic">{enrichmentNote}</p>
      )}
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
    return (
      <div className="text-center py-12 bg-[var(--bg-base)] rounded-lg">
        <p className="text-[var(--text-muted)]">
          Companies are derived from patent assignees — each tracked
          organisation shows its R&amp;D activity across patent classes.
        </p>
        <p className="text-sm text-[var(--text-muted)] mt-2">
          No companies found for the selected filters.
        </p>
        <div className="mt-4 flex items-center justify-center gap-4">
          <Link
            href="/patents"
            className="text-sm text-[var(--accent)] hover:underline font-medium"
          >
            Browse all patents →
          </Link>
          <Link
            href="/search"
            className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Search for a company
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-[var(--bg-base)]">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Company</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Profile</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Score</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Patents</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Active</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Tech Breadth</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Expiry Risk</th>
            </tr>
          </thead>
          <tbody className="bg-[var(--bg-surface)] divide-y divide-gray-200">
            {items.map((item) => (
              <tr key={item.name} className="hover:bg-[var(--bg-glass)]">
                <td className="px-4 py-4">
                  <Link
                    href={`/companies/${encodeURIComponent(item.name)}`}
                    className="text-sm font-medium text-[var(--accent)] hover:text-text-[var(--accent)] hover:underline max-w-xs truncate block"
                  >
                    {item.name}
                  </Link>
                  <p className="text-xs text-[var(--text-muted)]">Avg signal {item.average_signal_score ?? "—"}</p>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1.5">
                    {item.country && <Badge variant="default" size="sm">{item.country}</Badge>}
                    {item.entity_type && <Badge variant="default" size="sm">{humanizeTag(item.entity_type)}</Badge>}
                    {!item.country && !item.entity_type && <span className="text-xs text-[var(--text-muted)]">Enrichment pending</span>}
                  </div>
                </td>
                <td className="px-4 py-4 text-right">
                  <span className={`text-sm font-semibold ${item.supplier_score >= 60 ? "text-[var(--score-high)]" : item.supplier_score >= 35 ? "text-[var(--score-medium)]" : "text-[var(--text-muted)]"}`}>
                    {item.supplier_score}
                  </span>
                </td>
                <td className="px-4 py-4 text-right text-sm text-[var(--text-secondary)]">{formatNumber(item.patent_count)}</td>
                <td className="px-4 py-4 text-right text-sm text-[var(--text-secondary)]">{formatNumber(item.active_patent_count)}</td>
                <td className="px-4 py-4 text-right text-sm text-[var(--text-secondary)]">{formatNumber(item.technology_area_count)}</td>
                <td className="px-4 py-4 text-right text-sm text-[var(--text-secondary)]">{formatNumber(item.expiring_soon_count)}</td>
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
