"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { LegalConfidenceBadge } from "@/components/patents/LegalConfidenceBadge";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { RiskFlagsBadge } from "@/components/patents/RiskFlagsBadge";
import { ScoreBadge } from "@/components/patents/ScoreBadge";
import { TagsPanel } from "@/components/patents/TagsPanel";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useOpportunityList,
  useOpportunityTabCounts,
} from "@/hooks/useOpportunity";
import {
  OPPORTUNITY_TAG_VALUES,
  RISK_FLAG_VALUES,
  type OpportunityListParams,
  type OpportunitySort,
  type OpportunityTab,
} from "@/lib/types";
import { formatDate, humanizeTag, pluralize } from "@/lib/utils";

import { FilterNumber, FilterSelect, FilterText } from "./_filters";

const TABS: { id: OpportunityTab; label: string; helper: string }[] = [
  { id: "top", label: "Top", helper: "Highest opportunity_score across all patents" },
  { id: "expired", label: "Expired", helper: "Already expired — public-domain reuse" },
  { id: "revival", label: "Revival", helper: "Public-domain or AI revival candidates" },
  { id: "cross_industry", label: "Cross-industry", helper: "Patents flagged as transferable across industries" },
  { id: "startup", label: "Startup", helper: "Startup or low-competition opportunities" },
  { id: "enterprise", label: "Enterprise", helper: "Enterprise automation / manufacturing reuse" },
  { id: "sustainability", label: "Sustainability", helper: "Sustainability-angle patents" },
  { id: "legal_review", label: "Legal review", helper: "Needs legal-review flagged" },
];

const SORTS: { id: OpportunitySort; label: string }[] = [
  { id: "opportunity_score", label: "Opportunity score (high → low)" },
  { id: "expiring_soon", label: "Expiring soonest" },
  { id: "newly_published", label: "Newly published" },
  { id: "interesting_score", label: "Interesting score" },
  { id: "lowest_legal_risk", label: "Lowest legal risk" },
  { id: "strongest_cross_industry", label: "Strongest cross-industry" },
];

interface FiltersState {
  opportunity_tag?: string;
  risk_flag?: string;
  legal_confidence?: "" | "estimated" | "confirmed";
  industry?: string;
  cpc_prefix?: string;
  min_score?: number | "";
}

export default function OpportunityPage() {
  const [tab, setTab] = useState<OpportunityTab>("top");
  const [sort, setSort] = useState<OpportunitySort>("opportunity_score");
  const [filters, setFilters] = useState<FiltersState>({});
  const [page, setPage] = useState(1);

  const params: OpportunityListParams = useMemo(
    () => ({
      tab,
      sort,
      opportunity_tag: filters.opportunity_tag || undefined,
      risk_flag: filters.risk_flag || undefined,
      legal_confidence:
        !filters.legal_confidence ? undefined : filters.legal_confidence,
      industry: filters.industry || undefined,
      cpc_prefix: filters.cpc_prefix || undefined,
      min_score:
        filters.min_score === "" || filters.min_score === undefined
          ? undefined
          : Number(filters.min_score),
      page,
      page_size: 20,
    }),
    [tab, sort, filters, page]
  );

  const { data, isLoading } = useOpportunityList(params);
  const { data: tabCounts } = useOpportunityTabCounts();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Opportunity</h1>
        <p className="text-gray-600 mt-1">
          Patents ranked by rules-based opportunity_score. Tabs drill into specific
          opportunity types; combine with filters to narrow further.
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-4 border-b border-gray-200">
        <nav className="flex flex-wrap gap-1" aria-label="Opportunity tabs">
          {TABS.map((t) => {
            const count = tabCounts
              ? (tabCounts as unknown as Record<string, number>)[t.id]
              : undefined;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setTab(t.id);
                  setPage(1);
                }}
                title={t.helper}
                className={
                  "border-b-2 px-3 py-2 text-sm font-medium transition-colors " +
                  (active
                    ? "border-primary-500 text-primary-700"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-800")
                }
              >
                {t.label}
                {count !== undefined && (
                  <span className="ml-1.5 inline-flex items-center rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-3">
        <FilterSelect
          label="Opportunity tag"
          value={filters.opportunity_tag || ""}
          onChange={(v) =>
            setFilters((f) => ({ ...f, opportunity_tag: v || undefined }))
          }
          options={[{ value: "", label: "Any" }, ...OPPORTUNITY_TAG_VALUES.map((v) => ({ value: v, label: humanizeTag(v) }))]}
        />
        <FilterSelect
          label="Risk flag"
          value={filters.risk_flag || ""}
          onChange={(v) =>
            setFilters((f) => ({ ...f, risk_flag: v || undefined }))
          }
          options={[{ value: "", label: "Any" }, ...RISK_FLAG_VALUES.map((v) => ({ value: v, label: humanizeTag(v) }))]}
        />
        <FilterSelect
          label="Legal confidence"
          value={filters.legal_confidence || ""}
          onChange={(v) =>
            setFilters((f) => ({
              ...f,
              legal_confidence: v as "" | "estimated" | "confirmed",
            }))
          }
          options={[
            { value: "", label: "Any" },
            { value: "confirmed", label: "Confirmed" },
            { value: "estimated", label: "Estimated" },
          ]}
        />
        <FilterText
          label="Industry"
          placeholder="e.g. healthcare"
          value={filters.industry || ""}
          onChange={(v) => setFilters((f) => ({ ...f, industry: v || undefined }))}
        />
        <FilterText
          label="CPC prefix"
          placeholder="e.g. G06N"
          value={filters.cpc_prefix || ""}
          onChange={(v) => setFilters((f) => ({ ...f, cpc_prefix: v || undefined }))}
        />
        <FilterNumber
          label="Min score"
          placeholder="0–100"
          value={filters.min_score === undefined ? "" : String(filters.min_score)}
          onChange={(v) =>
            setFilters((f) => ({ ...f, min_score: v === "" ? "" : Number(v) }))
          }
        />

        <div className="ml-auto flex items-center gap-2">
          <label className="text-xs font-medium text-gray-500">Sort</label>
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as OpportunitySort);
              setPage(1);
            }}
            className="rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {SORTS.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      {isLoading && !data ? (
        <div className="grid gap-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-44 w-full rounded-lg" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="mb-3 text-sm text-gray-500">
            {data.total} {pluralize(data.total, "opportunity", "opportunities")} ·
            page {data.page} of {data.pages || 1}
          </div>
          <div className="grid gap-3">
            {data.items.map((item) => (
              <Link
                key={item.id}
                href={`/patents/${item.id}`}
                className="block rounded-lg border border-gray-200 bg-white p-4 transition hover:border-primary-300 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span className="font-mono">{item.doc_id}</span>
                      <span>•</span>
                      <span>{formatDate(item.grant_date || item.publication_date)}</span>
                      <LegalConfidenceBadge
                        confidence={item.legal_status_confidence}
                        legalStatus={item.legal_status}
                      />
                    </div>
                    <h3 className="mt-1 font-medium text-gray-900">
                      {item.title || "Untitled patent"}
                    </h3>
                    {item.summary_what_it_is && (
                      <p className="mt-1 line-clamp-2 text-sm text-gray-600">
                        {item.summary_what_it_is}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <OpportunityScoreBadge score={item.opportunity_score} size="md" />
                    <ScoreBadge score={item.interesting_score} showLabel={false} />
                  </div>
                </div>

                <div className="mt-3">
                  <TagsPanel tags={item.tags} variant="compact" />
                </div>

                {item.tags?.risk_flags?.length ? (
                  <div className="mt-2">
                    <RiskFlagsBadge flags={item.tags.risk_flags} />
                  </div>
                ) : null}

                <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                  <span>
                    {item.assignees[0] || "Unknown assignee"}
                    {item.assignees.length > 1 ? ` +${item.assignees.length - 1}` : ""}
                  </span>
                  {item.estimated_expiry_date && (
                    <span>
                      Expires {formatDate(item.estimated_expiry_date)}
                      {item.days_until_expiry !== null && (
                        <> · {item.days_until_expiry} {pluralize(item.days_until_expiry, "day")}</>
                      )}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                type="button"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {data.page} / {data.pages}
              </span>
              <button
                type="button"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="rounded-lg bg-gray-50 py-12 text-center text-gray-500">
          No opportunities match these filters yet. Try widening the cohort or
          recompute opportunity scores via{" "}
          <Link href="/admin/ai-runs" className="text-primary-600 hover:underline">
            Admin → AI Runs
          </Link>
          .
        </div>
      )}
    </div>
  );
}
