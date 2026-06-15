"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import useSWR from "swr";
import { useCliffs } from "@/hooks/useTrends";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { FilterChips } from "@/components/ui/FilterChips";
import { ExpirySummaryCards } from "@/components/expiry/ExpirySummaryCards";
import { ExpiryRadarSection } from "@/components/expiry/ExpiryRadarSection";
import { useWatchlist, addToWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import type { ExpiryRadarCardProps } from "@/components/expiry/ExpiryRadarCard";
import { expiryApi } from "@/lib/api";
import type {
  ExpiryItem,
  ExpiryParams,
  CliffClusterItem,
  ExpiryOpportunityItem,
} from "@/lib/types";

// ── helpers ──────────────────────────────────────────────────────────

function expiryItemToCardProps(item: ExpiryItem): ExpiryRadarCardProps {
  return {
    id: item.id,
    docId: item.doc_id,
    title: item.title,
    assignee: item.assignees?.[0] || "",
    estimatedExpiryDate: item.estimated_expiry_date,
    daysUntilExpiry: item.days_until_expiry,
    expiryStatus: item.expiry_status || "unknown",
    expiryConfidence: item.expiry_status_confidence || "low",
    activeFamilyRisk: item.active_family_risk ?? false,
    opportunityScore: item.opportunity_score,
    expiryOpportunityScore: item.expiry_opportunity_score,
    legalStatus: item.legal_status,
    legalStatusConfidence: item.legal_status_confidence,
    usageSignalCount: item.usage_signal_evidence_count ?? null,
    usageHasSelfCitationRisk: item.usage_has_self_citation_risk ?? null,
  };
}

function oppItemToCardProps(item: ExpiryOpportunityItem): ExpiryRadarCardProps {
  return {
    id: item.id,
    docId: item.doc_id,
    title: item.title,
    assignee: item.assignees?.[0] || "",
    estimatedExpiryDate: item.estimated_expiry_date,
    daysUntilExpiry: item.days_until_expiry,
    expiryStatus: item.expiry_status,
    expiryConfidence: item.expiry_status_confidence,
    activeFamilyRisk: item.active_family_risk,
    opportunityScore: item.opportunity_score,
    expiryOpportunityScore: item.expiry_opportunity_score,
    legalStatus: null,
    legalStatusConfidence: "estimated",
    usageSignalCount: item.usage_signal_evidence_count ?? null,
    usageHasSelfCitationRisk: item.usage_has_self_citation_risk ?? null,
  };
}

function useExpirySection(params: ExpiryParams | null) {
  const key = params ? ["expiry-section", JSON.stringify(params)] : null;
  return useSWR(key, () => (params ? expiryApi.list(params) : null), {
    revalidateOnFocus: false,
  });
}

// ── main page ────────────────────────────────────────────────────────

export default function ExpiryPage() {
  return (
    <Suspense fallback={<div className="p-8 text-[var(--text-muted)]">Loading...</div>}>
      <ExpiryContent />
    </Suspense>
  );
}

function ExpiryContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [params, setParams] = useState<ExpiryParams>(() => ({
    days_ahead: searchParams.get("days_ahead") ? Number(searchParams.get("days_ahead")) : 1825,
    expiry_status: searchParams.get("expiry_status") || undefined,
    confidence: searchParams.get("confidence") || undefined,
    maintenance_status: searchParams.get("maintenance_status") || undefined,
    active_family_risk: searchParams.get("active_family_risk") === "true" ? true : undefined,
    expiry_window_start: searchParams.get("expiry_window_start") || undefined,
    min_expiry_opportunity_score: searchParams.get("min_expiry_opportunity_score")
      ? Number(searchParams.get("min_expiry_opportunity_score"))
      : undefined,
    sort_by: searchParams.get("sort_by") || "expiry_urgency",
    sort_order: searchParams.get("sort_order") || "asc",
    page: 1,
    page_size: 12,
  }));

  const syncURL = useCallback(
    (p: ExpiryParams) => {
      const sp = new URLSearchParams();
      if (p.days_ahead !== 1825) sp.set("days_ahead", String(p.days_ahead));
      if (p.expiry_status) sp.set("expiry_status", p.expiry_status);
      if (p.confidence) sp.set("confidence", p.confidence);
      if (p.maintenance_status) sp.set("maintenance_status", p.maintenance_status);
      if (p.active_family_risk) sp.set("active_family_risk", "true");
      if (p.expiry_window_start) sp.set("expiry_window_start", p.expiry_window_start);
      if (p.min_expiry_opportunity_score)
        sp.set("min_expiry_opportunity_score", String(p.min_expiry_opportunity_score));
      if (p.sort_by && p.sort_by !== "expiry_urgency") sp.set("sort_by", p.sort_by);
      if (p.sort_order && p.sort_order !== "asc") sp.set("sort_order", p.sort_order);
      const qs = sp.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router]
  );

  useEffect(() => {
    syncURL(params);
  }, [params, syncURL]);

  // ── summary cards ──
  const { data: summaryData, isLoading: summaryLoading } = useSWR(
    "expiry-summary",
    () => expiryApi.getSummary(),
    { revalidateOnFocus: false }
  );

  // ── 7 sections ──
  const ninetyDaysAgo = new Date(Date.now() - 90 * 86400000).toISOString().split("T")[0];
  const fiveYearsAgo = new Date(Date.now() - 5 * 365 * 86400000).toISOString().split("T")[0];

  const expiringSoonParams: ExpiryParams = {
    ...params,
    expiry_status: "expiring_soon",
    expiry_window_start: undefined,
  };

  const recentlyExpiredParams: ExpiryParams = {
    ...params,
    expiry_status: undefined, // handled by window
    expiry_window_start: ninetyDaysAgo,
    days_ahead: 0,
    active_family_risk: undefined,
    min_expiry_opportunity_score: undefined,
  };

  const likelyLapsedParams: ExpiryParams = {
    ...params,
    expiry_status: "lapsed_possible",
    expiry_window_start: fiveYearsAgo,
    days_ahead: 0,
    active_family_risk: undefined,
    min_expiry_opportunity_score: undefined,
  };

  const revivalParams: ExpiryParams = {
    ...params,
    expiry_status: undefined,
    expiry_window_start: ninetyDaysAgo,
    days_ahead: 0,
    min_expiry_opportunity_score: 50,
    active_family_risk: undefined,
    sort_by: "expiry_opportunity_score",
    sort_order: "desc",
  };

  const familyRiskParams: ExpiryParams = {
    ...params,
    active_family_risk: true,
    expiry_status: undefined,
    expiry_window_start: undefined,
    sort_by: "expiry_opportunity_score",
    sort_order: "desc",
  };

  const lowConfidenceParams: ExpiryParams = {
    ...params,
    confidence: "low",
    expiry_status: undefined,
    expiry_window_start: undefined,
    active_family_risk: undefined,
  };

  const expSoon = useExpirySection(expiringSoonParams);
  const recentExp = useExpirySection(recentlyExpiredParams);
  const likelyLapsed = useExpirySection(likelyLapsedParams);
  const revival = useExpirySection(revivalParams);
  const familyRisk = useExpirySection(familyRiskParams);
  const lowConf = useExpirySection(lowConfidenceParams);

  const { data: oppData, isLoading: oppLoading } = useSWR(
    "expiry-opportunities",
    () => expiryApi.getOpportunities(50),
    { revalidateOnFocus: false }
  );

  const { data: cliffs12 } = useCliffs(12, 5, 6);
  const { data: cliffs24 } = useCliffs(24, 5, 6);

  // Watchlist for save/unsave on expiry cards
  const { data: watchlist, mutate: mutateWatchlist } = useWatchlist();
  const savedIds = new Set(watchlist?.map((item) => item.patent.id) || []);
  const handleToggleSave = async (patentId: string) => {
    const item = watchlist?.find((w) => w.patent.id === patentId);
    if (item) {
      await removeFromWatchlist(item.id, patentId);
    } else {
      await addToWatchlist(patentId);
    }
    mutateWatchlist();
  };

  // FilterChips
  const chips: { key: string; label: string; onRemove: () => void }[] = [];
  if (params.expiry_status) {
    chips.push({ key: "status", label: `Status: ${params.expiry_status}`, onRemove: () => setParams((p) => ({ ...p, expiry_status: undefined })) });
  }
  if (params.confidence) {
    chips.push({ key: "conf", label: `Confidence: ${params.confidence}`, onRemove: () => setParams((p) => ({ ...p, confidence: undefined })) });
  }
  if (params.active_family_risk) {
    chips.push({ key: "family", label: "Family risk only", onRemove: () => setParams((p) => ({ ...p, active_family_risk: undefined })) });
  }
  if (params.min_expiry_opportunity_score) {
    chips.push({ key: "score", label: `Score ≥ ${params.min_expiry_opportunity_score}`, onRemove: () => setParams((p) => ({ ...p, min_expiry_opportunity_score: undefined })) });
  }

  // ── render ──────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Expiry Radar"
        description="Track patents approaching or past expiration — with confidence labels and active family risk awareness."
        freshnessSources={["patents"]}
      />

      {/* Summary cards */}
      <ExpirySummaryCards data={summaryData ?? null} isLoading={summaryLoading} />

      {/* Legal caveat banner */}
      <div className="mb-4 p-3 bg-[var(--score-medium-bg)] border border-[var(--score-medium)]/30 rounded-lg">
        <p className="text-xs text-[var(--score-medium)]">
          <strong>Important:</strong> Expiry dates are estimates based on available patent data.
          Maintenance events, term adjustments, continuations, jurisdiction rules, and legal
          status changes may affect actual enforceability. Verify with official registers.
        </p>
      </div>

      {/* Horizon tabs */}
      <div className="flex flex-wrap items-center gap-1 mb-4">
        {[
          { label: "Expired", days: 0 },
          { label: "0–6 mo", days: 180 },
          { label: "6–12 mo", days: 365 },
          { label: "12–24 mo", days: 730 },
          { label: "24–36 mo", days: 1095 },
          { label: "All", days: 7300 },
        ].map((h) => {
          const active = (params.days_ahead ?? 1825) === h.days;
          return (
            <button
              key={h.days}
              onClick={() => setParams((p) => ({ ...p, days_ahead: h.days }))}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                active
                  ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {h.label}
            </button>
          );
        })}
      </div>

      {/* FilterBar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <select
          value={params.days_ahead ?? 1825}
          onChange={(e) =>
            setParams((p) => ({ ...p, days_ahead: Number(e.target.value) }))
          }
          className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm"
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
          value={params.expiry_status || ""}
          onChange={(e) =>
            setParams((p) => ({ ...p, expiry_status: e.target.value || undefined }))
          }
          className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="expiring_soon">Expiring Soon</option>
          <option value="expired_estimated">Expired (est.)</option>
          <option value="expired_confirmed">Expired (confirmed)</option>
          <option value="lapsed_possible">Lapsed (possible)</option>
          <option value="lapsed_confirmed">Lapsed (confirmed)</option>
          <option value="active_estimated">Active (est.)</option>
          <option value="unknown">Unknown</option>
        </select>

        <select
          value={params.confidence || ""}
          onChange={(e) =>
            setParams((p) => ({ ...p, confidence: e.target.value || undefined }))
          }
          className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm"
        >
          <option value="">All confidence</option>
          <option value="confirmed">Confirmed</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <label className="flex items-center gap-1.5 text-sm text-[var(--text-secondary)]">
          <input
            type="checkbox"
            checked={params.active_family_risk === true}
            onChange={(e) =>
              setParams((p) => ({
                ...p,
                active_family_risk: e.target.checked ? true : undefined,
              }))
            }
            className="rounded"
          />
          Family risk
        </label>

        <select
          value={`${params.sort_by || "expiry_urgency"}|${params.sort_order || "asc"}`}
          onChange={(e) => {
            const [sb, so] = e.target.value.split("|");
            setParams((p) => ({ ...p, sort_by: sb, sort_order: so }));
          }}
          className="rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm"
        >
          <option value="expiry_urgency|asc">Expiring soonest</option>
          <option value="expiry_opportunity_score|desc">Highest expiry opp.</option>
          <option value="opportunity_score|desc">Highest opportunity</option>
          <option value="confidence|desc">Highest confidence</option>
          <option value="recently_assessed|desc">Recently assessed</option>
          <option value="expiry_date|asc">Expiry date (asc)</option>
          <option value="expiry_date|desc">Expiry date (desc)</option>
        </select>
      </div>

      {/* Active filter chips */}
      {chips.length > 0 && (
        <div className="mb-4 mt-2">
          <FilterChips chips={chips} onClearAll={() => setParams((p) => ({ ...p, expiry_status: undefined, confidence: undefined, active_family_risk: undefined, min_expiry_opportunity_score: undefined }))} />
        </div>
      )}

      {/* CSV Export */}
      <div className="flex justify-end mb-4">
        <CSVExportButton params={params} />
      </div>

      <div className="space-y-8">
        {/* 1. Expiring Soon */}
        <ExpiryRadarSection
          title="Expiring Soon"
          description="Patents with estimated expiry within the selected window."
          items={(expSoon.data?.items || []).map(expiryItemToCardProps)}
          isLoading={expSoon.isLoading}
          emptyMessage="No patents currently flagged as expiring within your filter window."
          emptyDetail="Expiry estimates are based on filing date + standard term. Actual expiry may differ due to maintenance fees, patent term adjustments, or terminal disclaimers. Verify with official registers before any commercial decision."
          savedIds={savedIds}
          onToggleSave={handleToggleSave}
        />

        {/* 2. Recently Expired */}
        <ExpiryRadarSection
          title="Recently Expired"
          description="Patents that recently passed their estimated expiry date (last 90 days)."
          items={(recentExp.data?.items || []).map(expiryItemToCardProps)}
          isLoading={recentExp.isLoading}
          emptyMessage="No patents with estimated expiry in the last 90 days."
          emptyDetail="Estimated expiry does not account for maintenance fees, family status, or jurisdictional variations. All expiry statuses are heuristic estimates — verify with the issuing patent office before relying on this data."
          savedIds={savedIds}
          onToggleSave={handleToggleSave}
        />

        {/* 3. Likely Lapsed */}
        <ExpiryRadarSection
          title="Likely Lapsed"
          description="Patents with a lapsed maintenance status (possible abandonment)."
          items={(likelyLapsed.data?.items || []).map(expiryItemToCardProps)}
          isLoading={likelyLapsed.isLoading}
          emptyMessage="No lapsed-possible candidates identified."
          emptyDetail="Lapse status requires maintenance-fee evidence; absence of lapse data here does not mean a patent is fee-paid or in force. The USPTO does not publish real-time maintenance fee status in bulk."
        />

        {/* 4. Revival Candidates */}
        <ExpiryRadarSection
          title="Revival Candidates"
          description="Recently expired patents with high opportunity scores — may be worth investigating."
          items={(revival.data?.items || []).map(expiryItemToCardProps)}
          isLoading={revival.isLoading}
          emptyMessage="No high-opportunity revival candidates in this window."
          emptyDetail="A revival candidate is an estimated-expired patent with an above-threshold opportunity score. This is not a legal determination — active family members may still be enforceable in other jurisdictions."
        />

        {/* 5. Patent Cliffs */}
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">
            Patent Cliffs — Technology Openings
          </h2>
          {(!cliffs12 && !cliffs24) ? (
            <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-8 text-center">
              <p className="text-[var(--text-muted)] text-sm">No patent cliff data available for this window.</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Patent cliffs are detected from CPC clustering of patents with
                estimated expiry dates. Absence of cliff data does not indicate
                the absence of expiring patents — verify individual patents with
                official registers.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                ...(cliffs12?.items || []),
                ...(cliffs24?.items || []),
              ]
                .sort((a, b) => b.patent_count - a.patent_count)
                .slice(0, 4)
                .map((cliff) => (
                  <CliffCard key={cliff.id} cliff={cliff} />
                ))}
            </div>
          )}
        </div>

        {/* 6. High-Opportunity Expirations */}
        <ExpiryRadarSection
          title="High-Opportunity Expirations"
          description="Expired or expiring patents with strong expiry opportunity scores."
          items={(oppData?.items || []).map(oppItemToCardProps)}
          isLoading={oppLoading}
          emptyMessage="No high-scoring expiry opportunities in this dataset."
          emptyDetail="Expiry opportunity scores are deterministic heuristics, not legal advice. Scores reflect data completeness, commercial relevance indicators, and legal clarity — not a determination of freedom to operate."
        />

        {/* 7. Needs Legal Verification */}
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">
            Needs Legal Verification
          </h2>
          <p className="text-sm text-[var(--text-muted)] mb-3">
            Patents with active family risk or low-confidence expiry status — treat with caution.
          </p>

          {/* 7a: Active family risk */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">
              Active Family Risk
            </h3>
            <ExpiryRadarSection
              title=""
              items={(familyRisk.data?.items || []).map(expiryItemToCardProps)}
              isLoading={familyRisk.isLoading}
              emptyMessage="No patents with active family risk in this dataset."
              emptyDetail="Family risk assessment depends on available patent family data. An empty result does not guarantee the absence of active family members — always verify with official patent office records."
            />
          </div>

          {/* 7b: Low confidence */}
          <div>
            <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">
              Low Confidence Expiry Status
            </h3>
            <ExpiryRadarSection
              title=""
              items={(lowConf.data?.items || []).map(expiryItemToCardProps)}
              isLoading={lowConf.isLoading}
              emptyMessage="No low-confidence expiry assessments in this dataset."
              emptyDetail="Low confidence means key data — maintenance fees, grant date, or confirmed legal status — is missing. These patents may still be enforceable. Verify before any commercial action."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── CSV Export ────────────────────────────────────────────────────────

const CSV_HEADERS = [
  "doc_id",
  "title",
  "assignee_primary",
  "expiry_status",
  "expiry_status_confidence",
  "estimated_expiry_date",
  "days_until_expiry",
  "opportunity_score",
  "expiry_opportunity_score",
  "active_family_risk",
  "maintenance_status",
  "publication_number",
  "office",
];

function itemsToCSV(items: ExpiryItem[]): string {
  const escape = (v: unknown): string => {
    const s = v == null ? "" : String(v);
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const rows = [CSV_HEADERS.join(",")];
  for (const item of items) {
    rows.push(
      [
        item.doc_id,
        item.title || "",
        item.assignees?.[0] || "",
        item.expiry_status || "",
        item.expiry_status_confidence || "",
        item.estimated_expiry_date || "",
        item.days_until_expiry ?? "",
        item.opportunity_score ?? "",
        item.expiry_opportunity_score ?? "",
        item.active_family_risk ? "true" : "false",
        item.maintenance_status || "",
        item.publication_number || "",
        item.office || "",
      ].map(escape).join(",")
    );
  }
  return rows.join("\n");
}

function CSVExportButton({ params }: { params: ExpiryParams }) {
  const [isExporting, setIsExporting] = useState(false);
  const [rowCount, setRowCount] = useState<number | null>(null);

  // Check total available rows for the current filter state.
  const exportParams = { ...params, page: 1, page_size: 1 };
  const { data: countCheck, isLoading: countLoading } = useSWR(
    ["expiry-export-count", JSON.stringify(exportParams)],
    () => expiryApi.list(exportParams),
    { revalidateOnFocus: false }
  );

  const total = countCheck?.total ?? null;
  const isEmpty = total !== null && total === 0;
  const isDisabled = countLoading || isExporting || isEmpty;
  const isOverCap = total !== null && total > 1000;

  let tooltip = "";
  if (countLoading) tooltip = "Checking available rows...";
  else if (isEmpty) tooltip = "No data to export with current filters.";
  else if (isExporting) tooltip = "Generating CSV...";
  else if (isOverCap) tooltip = `Exporting first 1000 of ${total.toLocaleString()} rows. Refine filters for smaller exports.`;
  else if (total != null) tooltip = `Export ${total.toLocaleString()} rows as CSV.`;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const data = await expiryApi.list({
        ...params,
        page: 1,
        page_size: Math.min(total ?? 1000, 1000),
      });
      setRowCount(data?.items?.length ?? 0);
      if (data?.items?.length) {
        const csv = itemsToCSV(data.items);
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const today = new Date().toISOString().split("T")[0];
        a.download = `expiry-radar-${today}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleExport}
        disabled={isDisabled}
        title={tooltip}
        className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm font-medium
          bg-[var(--bg-surface)] hover:bg-[var(--bg-base)] disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors"
      >
        {isExporting ? "Exporting..." : "Download CSV"}
      </button>
      {rowCount !== null && !isExporting && (
        <span className="text-xs text-[var(--text-muted)]">
          Exported {rowCount.toLocaleString()} rows
        </span>
      )}
    </div>
  );
}

// ── CliffCard (reused from original) ──────────────────────────────────

const CPC_LABELS: Record<string, string> = {
  A61B: "Medical Diagnostics", A61F: "Medical Implants", A61K: "Pharma",
  A61M: "Medical Devices", B01D: "Filtration", B32B: "Layered Materials",
  B60W: "Vehicle Control", C12N: "Biotech", G06F: "Computing",
  G06T: "Image Processing", G09G: "Display Control", H01M: "Batteries",
  H04L: "Networking", H04W: "Wireless", H10W: "Semiconductors",
  Y02E: "Clean Energy", Y10T: "Technical Subjects",
};

function CliffCard({ cliff }: { cliff: CliffClusterItem }) {
  const label = CPC_LABELS[cliff.key_value] || cliff.key_value;
  const windowLabel =
    cliff.window_months < 12
      ? `${cliff.window_months}mo`
      : `${cliff.window_months / 12}yr`;

  return (
    <div className="block rounded-lg border border-border-[var(--accent)]/20 bg-[var(--bg-elevated)] p-4">
      <div className="flex items-start justify-between">
        <div>
          <span className="font-mono text-sm font-bold text-[var(--accent)]">
            {cliff.key_value}
          </span>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">{label}</p>
        </div>
        <Badge variant="default" size="sm">{windowLabel}</Badge>
      </div>
      <div className="mt-2">
        <span className="text-2xl font-bold text-[var(--accent)]">
          {cliff.patent_count}
        </span>
        <span className="text-xs text-[var(--text-muted)] ml-1">patents expiring</span>
      </div>
    </div>
  );
}
