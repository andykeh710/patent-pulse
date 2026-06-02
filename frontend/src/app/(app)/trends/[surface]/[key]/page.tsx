"use client";

import { Suspense, useState, useCallback, useEffect } from "react";
import { useParams, useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { AISourceFooter } from "@/components/patents/AISourceFooter";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { trendsApi, expiryApi } from "@/lib/api";
import type {
  TrendItem,
  PatentListItem,
  TrendNarrativeResponse,
  TrendAssigneeItem,
  ExpiryItem,
} from "@/lib/types";

// ── CPC label lookup (shared with /trends page) ──────────────────────

const CPC_LABELS: Record<string, string> = {
  A61B: "Medical Diagnostics", A61F: "Medical Implants", A61K: "Pharma",
  A61M: "Medical Devices", B01D: "Filtration", B32B: "Layered Materials",
  B60W: "Vehicle Control", C12N: "Biotech", G06F: "Computing",
  G06T: "Image Processing", G09G: "Display Control", H01M: "Batteries",
  H04L: "Networking", H04W: "Wireless", H10W: "Semiconductors",
  Y02E: "Clean Energy", Y10T: "Technical Subjects",
};

function cpcLabel(key: string): string {
  return CPC_LABELS[key] || key;
}

// ── main page ────────────────────────────────────────────────────────

export default function TrendDrilldownPage() {
  return (
    <Suspense fallback={<div className="p-8 text-[var(--text-muted)]">Loading...</div>}>
      <TrendDrilldownContent />
    </Suspense>
  );
}

function TrendDrilldownContent() {
  const routeParams = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const surface = routeParams.surface as string;
  const key = decodeURIComponent(routeParams.key as string);

  // ── trend detail ──
  const { data: trend, isLoading: trendLoading } = useSWR<TrendItem>(
    `trend-detail-${surface}-${key}`,
    () =>
      fetch(`/api/v1/trends/detail/${surface}/${key}`).then((r) => r.json()),
    { revalidateOnFocus: false }
  );

  // ── patents ──
  const [patentPage, setPatentPage] = useState(() =>
    searchParams.get("page") ? Number(searchParams.get("page")) : 1
  );
  useEffect(() => {
    const sp = new URLSearchParams();
    if (patentPage > 1) sp.set("page", String(patentPage));
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [patentPage, pathname, router]);
  const { data: patents, isLoading: patentsLoading } = useSWR(
    `trend-patents-${surface}-${key}-${patentPage}`,
    () => trendsApi.getDrilldownPatents(surface, key, patentPage),
    { revalidateOnFocus: false }
  );

  // ── assignees ──
  const { data: assignees, isLoading: assigneesLoading } = useSWR(
    `trend-assignees-${surface}-${key}`,
    () => trendsApi.getDrilldownAssignees(surface, key),
    { revalidateOnFocus: false }
  );

  // ── narrative ──
  const {
    data: narrative,
    isLoading: narrativeLoading,
    mutate: mutateNarrative,
  } = useSWR(
    `trend-narrative-${surface}-${key}`,
    () => trendsApi.getNarrative(surface, key),
    { revalidateOnFocus: false }
  );

  const handleGenerateNarrative = useCallback(async () => {
    const data = await trendsApi.generateNarrative(surface, key);
    mutateNarrative(data, false);
  }, [surface, key, mutateNarrative]);

  const [handleGenerate, isGenerating] = useAsyncAction(handleGenerateNarrative);

  // ── expiry ──
  const expiryKey = key.length <= 6 ? key : undefined;
  const { data: expiryData, isLoading: expiryLoading } = useSWR(
    expiryKey ? `trend-expiry-${expiryKey}` : null,
    () =>
      expiryApi.list({
        days_ahead: 365,
        page_size: 6,
        sort_by: "expiry_urgency",
        sort_order: "asc",
      }),
    { revalidateOnFocus: false }
  );

  // ── render ──────────────────────────────────────────────────────────

  if (trendLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-6 w-96" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
    );
  }

  if (!trend) {
    return (
      <div className="text-center py-12">
        <p className="text-[var(--text-muted)]">
          Trend not found for {surface}/{key}.
        </p>
        <Link href="/trends" className="text-[var(--accent)] mt-2 inline-block">
          Back to Trends
        </Link>
      </div>
    );
  }

  const label = surface === "cpc" ? `${key} — ${cpcLabel(key)}` : key;

  return (
    <div>
      {/* ── 1. Header ──────────────────────────────────────────── */}
      <div className="mb-6">
        <Link
          href="/trends"
          className="text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] mb-2 inline-flex items-center gap-1"
        >
          ← Back to Trends
        </Link>
        <div className="flex items-center gap-3 mt-2">
          <Badge
            variant="default"
            size="sm"
            className={
              surface === "cpc"
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : surface === "tag"
                ? "bg-[var(--accent-muted)] text-[var(--type-foryou)]"
                : "bg-[var(--score-medium-bg)] text-[var(--score-medium)]"
            }
          >
            {surface}
          </Badge>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{label}</h1>
        </div>
        <FreshnessBanner show={["trends"]} className="mt-2" />
        <div className="flex items-center gap-4 mt-3">
          <div>
            <span className="text-xs text-[var(--text-muted)]">z-score</span>
            <div
              className={`text-lg font-bold ${
                trend.z_score >= 5
                  ? "text-[var(--accent)]"
                  : trend.z_score >= 2
                  ? "text-[var(--score-medium)]"
                  : "text-[var(--text-secondary)]"
              }`}
            >
              {trend.z_score.toFixed(1)}
            </div>
          </div>
          <div>
            <span className="text-xs text-[var(--text-muted)]">growth</span>
            <div
              className={`text-lg font-bold ${
                trend.growth_pct > 0 ? "text-[var(--score-high)]" : "text-[var(--expiry-lapsed-confirmed)]"
              }`}
            >
              {trend.growth_pct > 0 ? "+" : ""}
              {trend.growth_pct.toFixed(1)}%
            </div>
          </div>
          <div>
            <span className="text-xs text-[var(--text-muted)]">patents (4wk)</span>
            <div className="text-lg font-bold text-[var(--text-primary)]">
              {trend.count_4w.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* ── 2. Why this matters ────────────────────────────── */}
          {narrative?.why_now && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
              <h2 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
                Why This Matters
              </h2>
              <p className="text-[var(--text-secondary)] leading-relaxed">
                {narrative.why_now}
              </p>
            </div>
          )}

          {/* ── 3. Narrative ───────────────────────────────────── */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-[var(--text-primary)]">
                Trend Analysis
              </h2>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="text-xs text-[var(--accent)] hover:text-text-[var(--accent-hover)] font-medium disabled:opacity-50"
              >
                {isGenerating
                  ? "Generating..."
                  : narrative
                  ? "Regenerate"
                  : "Analyze"}
              </button>
            </div>

            {isGenerating ? (
              <div className="flex items-center gap-3 text-[var(--text-muted)] py-4">
                <div className="animate-spin h-4 w-4 border-2 border-border-[var(--accent)]/30 border-t-bg-[var(--accent)] rounded-full" />
                <span className="text-sm">Generating trend analysis...</span>
              </div>
            ) : narrative?.summary ? (
              <div>
                <p className="text-[var(--text-secondary)] leading-relaxed">
                  {narrative.summary}
                </p>
                <AISourceFooter />
                {narrative.caveats.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
                    <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
                      Caveats
                    </h3>
                    <ul className="space-y-1">
                      {narrative.caveats.map((c, i) => (
                        <li
                          key={i}
                          className="text-xs text-[var(--text-muted)] flex items-start gap-2"
                        >
                          <span>&bull;</span>
                          {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)] py-4">
                No analysis generated yet. Click Analyze to generate an
                AI-powered trend summary (cached for reuse).
              </p>
            )}
          </div>

          {/* ── 4. Patents driving this trend ──────────────────── */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">
              Patents Driving This Trend
            </h2>
            {patentsLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-lg" />
                ))}
              </div>
            ) : !patents || patents.items.length === 0 ? (
              <div className="text-center py-8 text-[var(--text-muted)] text-sm">
                No patents driving this trend have been identified yet.
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Trend data depends on weekly computation of patent filing
                  activity. New filings may not appear until the next
                  scheduled refresh.
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  {patents.items.map((p: PatentListItem) => (
                    <PatentCardRow key={p.id} patent={p} />
                  ))}
                </div>
                {patents.total > 20 && (
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <span className="text-[var(--text-muted)]">
                      Page {patentPage} of{" "}
                      {Math.ceil(patents.total / 20)}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPatentPage((p) => Math.max(1, p - 1))}
                        disabled={patentPage === 1}
                        className="px-3 py-1 rounded border border-[var(--border-default)] disabled:opacity-50 hover:bg-[var(--bg-glass)]"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setPatentPage((p) => p + 1)}
                        disabled={patentPage * 20 >= patents.total}
                        className="px-3 py-1 rounded border border-[var(--border-default)] disabled:opacity-50 hover:bg-[var(--bg-glass)]"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── 6. Linked expiring patents ─────────────────────── */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">
              Expiring Patents in This Area
            </h2>
            {expiryLoading ? (
              <div className="space-y-3">
                {[...Array(2)].map((_, i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-lg" />
                ))}
              </div>
            ) : !expiryData || expiryData.items.length === 0 ? (
              <div className="text-center py-8 text-[var(--text-muted)] text-sm">
                No expiring patents tracked in this CPC area.
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Expiry tracking depends on estimated expiry dates and
                  legal status data. Verify with official registers.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {expiryData.items.slice(0, 4).map((item: ExpiryItem) => (
                  <Link
                    key={item.id}
                    href={`/patents/${item.id}`}
                    className="block p-3 bg-[var(--bg-base)] rounded hover:bg-[var(--bg-elevated)] transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                          {item.title || item.doc_id}
                        </p>
                        <p className="text-xs text-[var(--text-muted)]">
                          {item.doc_id} · {item.assignees?.[0] || "Unknown"}
                          {item.estimated_expiry_date &&
                            ` · Expiry: ${item.estimated_expiry_date}`}
                        </p>
                      </div>
                      {item.opportunity_score != null && (
                        <span className="text-xs font-bold text-[var(--accent)] ml-2">
                          {item.opportunity_score.toFixed(0)}
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* ── 7. Time-series (deferred — Sprint 4) ──────────── */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">
              Filing Activity Over Time
            </h2>
            <div className="text-center py-8 text-[var(--text-muted)] text-sm">
              Time-series view (coming soon). Historical trend data is
              available in the trend_snapshots table but requires a
              /history endpoint not yet built.
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Current snapshot shows {trend.count_4w} patents in the
                last 4 weeks and {trend.count_12w} in the last 12 weeks,
                compared to a 12-month baseline of{" "}
                {trend.baseline_12mo.toFixed(0)}.
              </p>
            </div>
          </div>
        </div>

        {/* ── Sidebar ────────────────────────────────────────── */}
        <div className="space-y-6">
          {/* ── 5. Top assignees ──────────────────────────────── */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">
              Top Assignees
            </h2>
            {assigneesLoading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-5 w-full" />
                ))}
              </div>
            ) : !assignees || assignees.items.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">
                No assignee data available for this trend.
              </p>
            ) : (
              <div className="space-y-2">
                {assignees.items.map((a: TrendAssigneeItem) => (
                  <div
                    key={a.assignee}
                    className="flex items-center justify-between text-sm"
                  >
                    <Link
                      href={`/companies/${encodeURIComponent(a.assignee)}`}
                      className="text-[var(--accent)] hover:underline truncate flex-1"
                    >
                      {a.assignee}
                    </Link>
                    <span className="text-[var(--text-muted)] ml-2">{a.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Trend stats ──────────────────────────────────── */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">
              Trend Stats
            </h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-[var(--text-muted)]">Patents (12wk)</dt>
                <dd className="font-medium">{trend.count_12w}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--text-muted)]">Baseline (12mo avg)</dt>
                <dd className="font-medium">{trend.baseline_12mo.toFixed(1)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--text-muted)]">Assignee Diversity</dt>
                <dd className="font-medium">
                  {(trend.assignee_diversity * 100).toFixed(0)}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--text-muted)]">CPC Diversity</dt>
                <dd className="font-medium">
                  {(trend.cpc_diversity * 100).toFixed(0)}%
                </dd>
              </div>
            </dl>
          </div>

          {/* ── Related trends ────────────────────────────────── */}
          {narrative?.related_trends && narrative.related_trends.length > 0 && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
              <h2 className="font-semibold text-[var(--text-primary)] mb-3">
                Related Trends
              </h2>
              <div className="flex flex-wrap gap-2">
                {narrative.related_trends.map((t, i) => (
                  <Badge key={i} variant="default" size="sm">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Legal caveat ─────────────────────────────────────── */}
      <div className="mt-8 p-4 bg-[var(--score-medium-bg)] border border-[var(--score-medium)]/30 rounded-lg">
        <p className="text-xs text-[var(--score-medium)]">
          <strong>Important:</strong> Trend data is based on patent filing
          activity and does not reflect market adoption. AI-generated
          narratives are heuristic analyses, not investment or legal
          advice. Verify patent data with official registers before any
          commercial decision.
        </p>
      </div>
    </div>
  );
}

// ── PatentCardRow (simplified inline) ─────────────────────────────────

function PatentCardRow({ patent }: { patent: PatentListItem }) {
  return (
    <Link
      href={`/patents/${patent.id}`}
      className="block p-3 bg-[var(--bg-base)] rounded hover:bg-[var(--bg-elevated)] transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)] truncate">
            {patent.title || patent.doc_id}
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            {patent.doc_id} · {patent.assignees?.[0] || "Unknown"}
          </p>
        </div>
        <div className="flex items-center gap-3 ml-2">
          {patent.opportunity_score != null && (
            <span className="text-xs font-bold text-[var(--accent)]">
              {patent.opportunity_score.toFixed(0)}
            </span>
          )}
          {patent.interesting_score != null && (
            <span className="text-xs text-[var(--text-muted)]">
              {patent.interesting_score.toFixed(0)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
