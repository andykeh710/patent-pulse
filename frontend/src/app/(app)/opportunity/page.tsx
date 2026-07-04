"use client";

import Link from "next/link";
import { Suspense, useMemo, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

import { LegalConfidenceBadge } from "@/components/patents/LegalConfidenceBadge";

import { RiskFlagsBadge } from "@/components/patents/RiskFlagsBadge";
import { Score } from "@/components/ui/Score";
import { TagsPanel } from "@/components/patents/TagsPanel";
import { Skeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
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
  { id: "expired", label: "Expired", helper: "Already expired. Public-domain reuse." },
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
  return (
    <Suspense fallback={<div className="p-8 text-[var(--text-muted)]">Loading...</div>}>
      <OpportunityContent />
    </Suspense>
  );
}

function OpportunityContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Initialize state from URL params
  const [tab, setTab] = useState<OpportunityTab>(
    (searchParams.get("tab") as OpportunityTab) || "top"
  );
  const [sort, setSort] = useState<OpportunitySort>(
    (searchParams.get("sort") as OpportunitySort) || "opportunity_score"
  );
  const [filters, setFilters] = useState<FiltersState>({
    opportunity_tag: searchParams.get("opportunity_tag") || undefined,
    risk_flag: searchParams.get("risk_flag") || undefined,
    legal_confidence: (searchParams.get("legal_confidence") as FiltersState["legal_confidence"]) || undefined,
    industry: searchParams.get("industry") || undefined,
    cpc_prefix: searchParams.get("cpc_prefix") || undefined,
    min_score: searchParams.get("min_score") ? Number(searchParams.get("min_score")) : undefined,
  });
  const [page, setPage] = useState(
    searchParams.get("page") ? Number(searchParams.get("page")) : 1
  );

  // Sync state changes to URL
  const syncURL = useCallback(
    (t: string, s: string, f: FiltersState, p: number) => {
      const params = new URLSearchParams();
      if (t !== "top") params.set("tab", t);
      if (s !== "opportunity_score") params.set("sort", s);
      if (f.opportunity_tag) params.set("opportunity_tag", f.opportunity_tag);
      if (f.risk_flag) params.set("risk_flag", f.risk_flag);
      if (f.legal_confidence) params.set("legal_confidence", f.legal_confidence);
      if (f.industry) params.set("industry", f.industry);
      if (f.cpc_prefix) params.set("cpc_prefix", f.cpc_prefix);
      if (f.min_score !== undefined && f.min_score !== "") params.set("min_score", String(f.min_score));
      if (p > 1) params.set("page", String(p));
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router]
  );

  useEffect(() => {
    syncURL(tab, sort, filters, page);
  }, [tab, sort, filters, page, syncURL]);

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
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Opportunity</h1>
        <FreshnessBanner show={["patents", "summaries"]} className="mt-2" />
        <p className="text-[var(--text-secondary)] mt-1">
          Patents ranked by rules-based opportunity_score. Tabs drill into specific
          opportunity types; combine with filters to narrow further.
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-4 border-b border-[var(--border-subtle)]">
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
                    ? "border-[var(--accent)] text-[var(--accent)]"
                    : "border-transparent text-[var(--text-muted)] hover:border-[var(--border-default)] hover:text-[var(--text-primary)]")
                }
              >
                {t.label}
                {count !== undefined && (
                  <span className="ml-1.5 inline-flex items-center rounded-full bg-[var(--bg-elevated)] px-1.5 py-0.5 text-xs text-[var(--text-secondary)]">
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
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
          <label className="text-xs font-medium text-[var(--text-muted)]">Sort</label>
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as OpportunitySort);
              setPage(1);
            }}
            className="rounded-lg border border-[var(--border-default)] px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
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
          <div className="mb-3 text-sm text-[var(--text-muted)]">
            {data.total} {pluralize(data.total, "opportunity", "opportunities")} ·
            page {data.page} of {data.pages || 1}
          </div>
          <div className="grid gap-3">
            {data.items.map((item) => (
              <Link
                key={item.id}
                href={`/patents/${item.id}`}
                className="block rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 transition hover:border-[var(--accent)]/30"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                      <span className="font-mono">{item.doc_id}</span>
                      <span>•</span>
                      <span>{formatDate(item.grant_date || item.publication_date)}</span>
                      <LegalConfidenceBadge
                        confidence={item.legal_status_confidence}
                        legalStatus={item.legal_status}
                      />
                    </div>
                    <h3 className="mt-1 font-medium text-[var(--text-primary)]">
                      {item.title || "Untitled patent"}
                    </h3>
                    {item.summary_what_it_is && (
                      <p className="mt-1 line-clamp-2 text-sm text-[var(--text-secondary)]">
                        {item.summary_what_it_is}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <Score value={item.opportunity_score} kind="opportunity" size="md" />
                    <Score value={item.interesting_score} kind="interesting" size="sm" showLabel={false} />
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

                <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-muted)]">
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
                <SourceAttribution docId={item.doc_id} />
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
                className="rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-base)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {data.page} / {data.pages}
              </span>
              <button
                type="button"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-base)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="rounded-lg bg-[var(--bg-base)] py-12 text-center">
          <p className="text-[var(--text-muted)]">
            High-value patents ranked by opportunity score — factoring
            expiry proximity, claim breadth, and cross-industry potential.
          </p>
          <p className="text-sm text-[var(--text-muted)] mt-2">
            No opportunities match these filters yet.
          </p>
          <div className="mt-4">
            <Link
              href="/patents"
              className="text-sm text-[var(--accent)] hover:underline font-medium"
            >
              Browse all patents →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
