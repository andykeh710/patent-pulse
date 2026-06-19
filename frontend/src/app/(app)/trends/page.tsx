"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  useHotTrends,
  useGrowingTrends,
  useConvergence,
  useCliffs,
  useTrendsSummary,
} from "@/hooks/useTrends";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import type { TrendItem, ConvergenceItem, CliffClusterItem } from "@/lib/types";

type SurfaceFilter = "all" | "cpc" | "tag" | "assignee";
type TrendView = "hot" | "growing" | "convergence" | "cliffs";

const CPC_LABELS: Record<string, string> = {
  A61B: "Medical Diagnostics",
  A61F: "Medical Implants",
  A61K: "Pharma / Drug Delivery",
  A61M: "Medical Devices",
  B01D: "Separation / Filtration",
  B29K: "Plastics / Polymers",
  B29L: "Layered Products",
  B32B: "Layered Materials",
  B60W: "Vehicle Control",
  C07K: "Peptides / Proteins",
  C12N: "Biotech / Genetics",
  G01N: "Testing / Analysis",
  G06F: "Computing / Processing",
  G06T: "Image Processing",
  G06V: "Computer Vision",
  G09G: "Display Control",
  H01M: "Batteries / Fuel Cells",
  H04L: "Network Protocols",
  H04W: "Wireless Communication",
  H05K: "Printed Circuits",
  H10W: "Semiconductor Devices",
  Y02E: "Clean Energy",
  Y10T: "Technical Subjects",
};

function cpcLabel(key: string): string {
  return CPC_LABELS[key] || key;
}

export default function TrendsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-[var(--text-muted)]">Loading...</div>}>
      <TrendsContent />
    </Suspense>
  );
}

function TrendsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [view, setView] = useState<TrendView>(
    (searchParams.get("view") as TrendView) || "hot"
  );
  const [surface, setSurface] = useState<SurfaceFilter>(
    (searchParams.get("surface") as SurfaceFilter) || "all"
  );
  const [cliffWindow, setCliffWindow] = useState<number | undefined>(
    searchParams.get("cliff_window") ? Number(searchParams.get("cliff_window")) : 12
  );

  useEffect(() => {
    const sp = new URLSearchParams();
    if (view !== "hot") sp.set("view", view);
    if (surface !== "all") sp.set("surface", surface);
    if (cliffWindow !== undefined && cliffWindow !== 12) sp.set("cliff_window", String(cliffWindow));
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [view, surface, cliffWindow, pathname, router]);

  const surfaceParam = surface === "all" ? undefined : surface;
  const { data: summary } = useTrendsSummary();
  const { data: hotData, isLoading: hotLoading } = useHotTrends(surfaceParam, 20);
  const { data: growingData, isLoading: growingLoading } = useGrowingTrends(surfaceParam, 20);
  const { data: convergence, isLoading: convLoading } = useConvergence(30);
  const { data: cliffs, isLoading: cliffsLoading } = useCliffs(cliffWindow, 3, 30);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Trends</h1>
        <FreshnessBanner show={["trends", "patents"]} className="mt-2" />
        <p className="text-[var(--text-secondary)] mt-1">
          Technology momentum, convergence signals, and patent cliff opportunities
        </p>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <SummaryCard label="Trending Topics" value={summary.total_trend_rows} />
          <SummaryCard label="CPC Trends" value={summary.surfaces.cpc || 0} />
          <SummaryCard label="Convergence Signals" value={summary.convergence_signals} highlight />
          <SummaryCard label="Patent Cliffs" value={summary.cliff_clusters} highlight />
        </div>
      )}

      {/* View tabs */}
      <div className="mb-4 border-b border-[var(--border-subtle)]">
        <nav className="flex gap-1">
          {([
            { id: "hot" as const, label: "Hot Right Now" },
            { id: "growing" as const, label: "Fastest Growing" },
            { id: "convergence" as const, label: "Convergence" },
            { id: "cliffs" as const, label: "Patent Cliffs" },
          ]).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setView(tab.id)}
              className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                view === tab.id
                  ? "border-[var(--accent)] text-[var(--accent)]"
                  : "border-transparent text-[var(--text-muted)] hover:border-[var(--border-default)] hover:text-[var(--text-primary)]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Surface filter (for hot/growing views) */}
      {(view === "hot" || view === "growing") && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm text-[var(--text-muted)]">Filter:</span>
          {(["all", "cpc", "tag", "assignee"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSurface(s)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                surface === s
                  ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {s === "all" ? "All" : s === "cpc" ? "Technology (CPC)" : s === "tag" ? "Tags" : "Assignees"}
            </button>
          ))}
        </div>
      )}

      {/* Cliff window filter */}
      {view === "cliffs" && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-sm text-[var(--text-muted)]">Expiry window:</span>
          {([6, 12, 24, 60] as const).map((m) => (
            <button
              key={m}
              onClick={() => setCliffWindow(m)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                cliffWindow === m
                  ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {m < 12 ? `${m}mo` : `${m / 12}yr`}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {view === "hot" && (
        <TrendList
          items={hotData?.items || []}
          isLoading={hotLoading}
          total={hotData?.total || 0}
        />
      )}

      {view === "growing" && (
        <TrendList
          items={growingData?.items || []}
          isLoading={growingLoading}
          total={growingData?.total || 0}
        />
      )}

      {view === "convergence" && (
        <ConvergenceList items={convergence || []} isLoading={convLoading} />
      )}

      {view === "cliffs" && (
        <CliffList items={cliffs?.items || []} isLoading={cliffsLoading} />
      )}

      <div className="mt-8">
        <SourceAttribution />
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        highlight ? "bg-[var(--bg-elevated)] border-border-[var(--accent)]/20" : "bg-[var(--bg-surface)] border-[var(--border-subtle)]"
      }`}
    >
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? "text-[var(--accent)]" : "text-[var(--text-primary)]"}`}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function TrendList({
  items,
  isLoading,
  total,
}: {
  items: TrendItem[];
  isLoading: boolean;
  total: number;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 bg-[var(--bg-base)] rounded-lg">
        <p className="text-[var(--text-muted)]">
          Trend signals from the past 7 days, computed weekly from CPC
          filing data.
        </p>
        <p className="text-sm text-[var(--text-muted)] mt-2">
          No trend data available yet — the weekly computation hasn&apos;t
          completed its first run.
        </p>
        <div className="mt-4">
          <Link
            href="/patents"
            className="text-sm text-[var(--accent)] hover:underline font-medium"
          >
            Browse recent patents →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-[var(--text-muted)] mb-3">{total.toLocaleString()} trends tracked</p>
      {items.map((item, idx) => (
        <Link
          key={`${item.surface}-${item.key}-${idx}`}
          href={`/trends/${item.surface}/${item.key}`}
          className="flex items-center gap-4 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--accent)]/30 transition-colors cursor-pointer block"
        >
          <div className="text-lg font-bold text-[var(--text-muted)] w-8 text-right">{idx + 1}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Badge
                variant="default"
                size="sm"
                className={
                  item.surface === "cpc"
                    ? "bg-[var(--accent-muted)] text-[var(--accent)] border-[var(--accent)]/30"
                    : item.surface === "tag"
                    ? "bg-[var(--accent-muted)] text-[var(--type-foryou)] border-[var(--type-foryou)]/30"
                    : "bg-[var(--score-medium-bg)] text-[var(--score-medium)] border-[var(--score-medium)]/30"
                }
              >
                {item.surface}
              </Badge>
              <span className="font-semibold text-[var(--text-primary)] truncate">
                {item.surface === "cpc" ? `${item.key} — ${cpcLabel(item.key)}` : item.key}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1 text-xs text-[var(--text-muted)]">
              <span>{item.count_4w} patents (4wk)</span>
              <span>{item.count_12w} patents (12wk)</span>
              {item.assignee_diversity > 0 && (
                <span>Diversity: {(item.assignee_diversity * 100).toFixed(0)}%</span>
              )}
            </div>
            {item.top_patent_ids && item.top_patent_ids.length > 0 && (
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-xs text-[var(--text-muted)]">Top patents:</span>
                {item.top_patent_ids.slice(0, 3).map((pid) => (
                  <Link
                    key={pid}
                    href={`/patents/${pid}`}
                    className="text-xs text-[var(--accent)] hover:underline"
                  >
                    View
                  </Link>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 text-right">
            <div>
              <div className="text-xs text-[var(--text-muted)]">z-score</div>
              <div className={`text-lg font-bold ${item.z_score >= 5 ? "text-[var(--accent)]" : item.z_score >= 2 ? "text-[var(--score-medium)]" : "text-[var(--text-secondary)]"}`}>
                {item.z_score.toFixed(1)}
              </div>
            </div>
            <div>
              <div className="text-xs text-[var(--text-muted)]">growth</div>
              <div className={`text-sm font-semibold ${item.growth_pct > 0 ? "text-[var(--score-high)]" : item.growth_pct < 0 ? "text-[var(--expiry-lapsed-confirmed)]" : "text-[var(--text-muted)]"}`}>
                {item.growth_pct > 0 ? "+" : ""}{item.growth_pct.toFixed(1)}%
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

function ConvergenceList({
  items,
  isLoading,
}: {
  items: ConvergenceItem[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 bg-[var(--bg-base)] rounded-lg text-[var(--text-muted)]">
        No convergence signals detected yet.
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-[var(--text-muted)] mb-3">
        Technology areas with accelerating co-occurrence on patents
      </p>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div
            key={`${item.cpc_a}-${item.cpc_b}-${idx}`}
            className="flex items-center gap-4 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4"
          >
            <div className="text-lg font-bold text-[var(--text-muted)] w-8 text-right">{idx + 1}</div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono font-semibold text-[var(--accent)]">{item.cpc_a}</span>
                <span className="text-xs text-[var(--text-muted)]">{cpcLabel(item.cpc_a)}</span>
                <svg className="w-4 h-4 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                <span className="font-mono font-semibold text-[var(--accent)]">{item.cpc_b}</span>
                <span className="text-xs text-[var(--text-muted)]">{cpcLabel(item.cpc_b)}</span>
              </div>
              <div className="text-xs text-[var(--text-muted)] mt-1">
                {item.joint_count} patents co-filed
                {item.baseline_count > 0 && ` (baseline: ${item.baseline_count})`}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-[var(--text-muted)]">growth ratio</div>
              <div className="text-lg font-bold text-[var(--accent)]">
                {item.growth_ratio.toFixed(1)}x
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CliffList({
  items,
  isLoading,
}: {
  items: CliffClusterItem[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 bg-[var(--bg-base)] rounded-lg text-[var(--text-muted)]">
        No patent cliff clusters found for this window.
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-[var(--text-muted)] mb-3">
        Technology areas where multiple patents are expiring together, creating opportunity openings
      </p>
      <div className="space-y-2">
        {items.map((item) => (
          <Link
            key={item.id}
            href={`/trends/${item.key_type}/${item.key_value}`}
            className="flex items-center gap-4 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--accent)]/30 transition-colors cursor-pointer"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-mono font-semibold text-[var(--text-primary)]">{item.key_value}</span>
                <span className="text-sm text-[var(--text-muted)]">{cpcLabel(item.key_value)}</span>
                <Badge variant="default" size="sm">
                  {item.window_months < 12 ? `${item.window_months}mo` : `${item.window_months / 12}yr`} window
                </Badge>
              </div>
              <div className="flex items-center gap-2 mt-1">
                {item.representative_patent_ids.slice(0, 3).map((pid) => (
                  <Link
                    key={pid}
                    href={`/patents/${pid}`}
                    className="text-xs text-[var(--accent)] hover:underline"
                  >
                    View patent
                  </Link>
                ))}
                {item.representative_patent_ids.length > 3 && (
                  <span className="text-xs text-[var(--text-muted)]">
                    +{item.representative_patent_ids.length - 3} more
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-[var(--accent)]">{item.patent_count}</div>
              <div className="text-xs text-[var(--text-muted)]">patents expiring</div>
            </div>
          </Link>
        ))}
      </div>
      <SourceAttribution />
    </div>
  );
}
