"use client";

import { useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { InsightCard } from "@/components/ui/InsightCard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { StarterTopics } from "@/components/ui/StarterTopics";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { Tour } from "@/components/tour/Tour";
import { ForYouCard, type FeedItemType } from "@/components/today/ForYouCard";
import { useOpportunityList } from "@/hooks/useOpportunity";
import { usePriorityWatch, usePatentStats } from "@/hooks/usePatents";
import { useSuppliers } from "@/hooks/useSuppliers";
import { useThemes } from "@/hooks/useThemes";
import { useWatchlist } from "@/hooks/useWatchlist";
import { todayApi, suppliersApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type {
  TodayState,
  TodayInsight,
  FilingTrendCard,
  ExpiringOpportunityCard,
  NotablePatentCard,
  CompanyMoveCard,
  Topic,
  WatchlistItemResponse,
} from "@/lib/types";
import type { OpportunityItem } from "@/lib/types";
import type { PatentListItem } from "@/lib/types";

// -- Insight builders (deterministic, evidence-backed) --

function buildInsights(
  state: TodayState | undefined,
  highlights: {
    filing_trend: FilingTrendCard | null;
    expiring_opportunity: ExpiringOpportunityCard | null;
    notable_patent: NotablePatentCard | null;
    company_move: CompanyMoveCard | null;
  } | undefined,
  stats: { total_patents: number; patents_this_week: number; summarized_count: number; top_assignees?: { assignee: string; count: number }[] } | undefined,
  watchlist: unknown[] | undefined,
  userTopics: Topic[] | undefined,
  followedCompanyNames: Set<string>,
  _topOpps: { items?: OpportunityItem[] } | undefined,
  _expiring: { items?: PatentListItem[] } | undefined,
  _companies: { items?: { name: string; patent_count: number; supplier_score: number }[] } | undefined,
): { personalized: TodayInsight[]; general: TodayInsight[] } {
  const personalized: TodayInsight[] = [];
  const general: TodayInsight[] = [];
  const now = new Date().toISOString();
  const _savedIds = new Set((watchlist as WatchlistItemResponse[] | undefined)?.map((w) => w?.patent?.id) || []);
  const _topicCPCs = new Set(userTopics?.flatMap((t) => t.cpc_prefixes || []) || []);

  function add(insight: TodayInsight) {
    const hasWatchlist = insight.evidence.some((e) => e.label === "From watchlist");
    const hasTopic = insight.evidence.some((e) => e.label === "Your topic");
    const hasCompany = insight.evidence.some((e) => e.label === "Company you follow");
    if (hasWatchlist || hasTopic || hasCompany) {
      personalized.push(insight);
    } else {
      general.push(insight);
    }
  }

  // Watchlist items (personalized)
  if (watchlist && watchlist.length > 0) {
    const wlItems = watchlist as WatchlistItemResponse[];
    personalized.push({
      id: "watchlist-count",
      type: "update",
      title: `${wlItems.length} patent${wlItems.length !== 1 ? "s" : ""} in your watchlist`,
      summary: wlItems.length > 3
        ? `Top watchlisted: ${wlItems.slice(0, 3).map((w) => w.patent.title || w.patent.doc_id).join(", ")}`
        : wlItems.map((w) => w.patent.title || w.patent.doc_id).join(" · "),
      why_it_matters: "Patents you've saved. Monitor them for updates, related citations, and expiry changes.",
      evidence: [
        { label: "Saved patents", value: wlItems.length },
        { label: "From watchlist", value: "Your personal watchlist" },
      ],
      confidence: "high",
      timestamp: now,
      primary_action: { label: "Open watchlist", href: "/watchlist" },
    });
  }

  // 1. New patents this week
  if (stats && stats.patents_this_week > 0) {
    general.push({
      id: "new-patents-week",
      type: "update",
      title: `${stats.patents_this_week.toLocaleString()} new patents this week`,
      summary: `The patent corpus grew by ${stats.patents_this_week.toLocaleString()} records since your last visit window.`,
      why_it_matters: "New filings may indicate competitor activity or emerging technology areas.",
      evidence: [
        { label: "New patents", value: stats.patents_this_week },
        { label: "Total corpus", value: stats.total_patents },
      ],
      confidence: "high",
      timestamp: now,
      primary_action: { label: "Browse new patents", href: "/patents?sort_by=publication_date&sort_order=desc" },
      secondary_action: { label: "Search by technology", href: "/search" },
    });
  }

  // 2. Filing trend
  if (highlights?.filing_trend) {
    const t = highlights.filing_trend;
    general.push({
      id: `trend-${t.trend_surface}-${t.trend_key}`,
      type: "signal",
      title: `${t.trend_label} filing activity trending up`,
      summary: `${t.count_4w} patents filed in the last 4 weeks with a z-score of ${t.z_score.toFixed(1)}, indicating above-average activity.`,
      why_it_matters: "Above-average filing momentum in this area may signal competitive R&D investment.",
      evidence: [
        { label: "4-week count", value: t.count_4w },
        { label: "Z-score", value: t.z_score.toFixed(1) },
        ...(t.top_assignees.length > 0 ? [{ label: "Top assignees", value: t.top_assignees.join(", ") }] : []),
      ],
      confidence: "medium",
      timestamp: now,
      primary_action: { label: "View trend detail", href: `/trends/${t.trend_surface}/${t.trend_key}` },
      secondary_action: { label: "Explore trends", href: "/trends" },
    });
  }

  // 3. Expiring opportunities
  if (highlights?.expiring_opportunity) {
    const e = highlights.expiring_opportunity;
    general.push({
      id: "expiring-opportunities",
      type: "opportunity",
      title: `${e.count} high-value patents expiring within 90 days`,
      summary: `${e.count} patents with strong opportunity scores are approaching estimated expiry.`,
      why_it_matters: "Expiring patents may create design freedom or licensing opportunities. Verify with official registers before acting.",
      evidence: [
        { label: "Count", value: e.count },
        { label: "Window", value: "90 days" },
      ],
      confidence: "medium",
      timestamp: now,
      primary_action: { label: "View Expiry Radar", href: "/expiry?expiry_status=expiring_soon&min_expiry_opportunity_score=70" },
      secondary_action: { label: "All expiry data", href: "/expiry" },
    });
  }

  // 4. Notable patent
  if (highlights?.notable_patent) {
    const n = highlights.notable_patent;
    general.push({
      id: `notable-${n.id}`,
      type: "signal",
      title: n.title || n.publication_number,
      summary: n.summary_first_sentence || `Patent from ${n.assignee || "unknown assignee"} with high opportunity score.`,
      why_it_matters: `Strong opportunity score (${n.opportunity_score.toFixed(1)}) suggests commercial relevance in its technology area.`,
      evidence: [
        { label: "Assignee", value: n.assignee || "Unknown" },
        { label: "Opportunity score", value: n.opportunity_score.toFixed(1) },
        { label: "Doc ID", value: n.doc_id },
      ],
      confidence: n.has_abstract && n.has_claims && !n.limited_source ? "high" : "medium",
      timestamp: now,
      primary_action: { label: "View patent", href: `/patents/${n.id}` },
    });
  }

  // 5. Company move
  if (highlights?.company_move) {
    const c = highlights.company_move;
    const isFollowed = followedCompanyNames.has(c.assignee.toLowerCase());
    const why = isFollowed
      ? `Shown because you follow ${c.assignee}. Their filing surge of +${c.delta} vs average may signal a new product cycle, strategic IP push, or competitive positioning relevant to your watch.`
      : "A filing surge may indicate a new product cycle, strategic IP push, or competitive positioning.";
    const evidence = [
      { label: "This week", value: c.count_this_week },
      { label: "4-week avg", value: c.count_4wk_avg.toFixed(1) },
      { label: "Delta", value: `+${c.delta}` },
    ];
    if (isFollowed) evidence.push({ label: "Company you follow", value: c.assignee });
    add({
      id: `company-${c.assignee}`,
      type: "update",
      title: `${c.assignee} filing surge: +${c.delta} vs 4-week average`,
      summary: `${c.count_this_week} filings this week compared to a ${c.count_4wk_avg.toFixed(1)} weekly average.`,
      why_it_matters: why,
      evidence,
      confidence: "medium",
      timestamp: now,
      primary_action: { label: "View company profile", href: `/companies/${encodeURIComponent(c.assignee)}` },
      secondary_action: { label: "All companies", href: "/companies" },
    });
  }

  // 6. Watchlist activity
  if (watchlist && watchlist.length > 0) {
    general.push({
      id: "watchlist-status",
      type: "update",
      title: `${watchlist.length} saved ${watchlist.length === 1 ? "patent" : "patents"} in your watchlist`,
      summary: "Review your saved patents for new enrichment data, expiry updates, or usage signals.",
      why_it_matters: "Saved patents are monitored for changes. Regular review keeps your intelligence current.",
      evidence: [{ label: "Saved patents", value: watchlist.length }],
      confidence: "high",
      timestamp: now,
      primary_action: { label: "Open watchlist", href: "/watchlist" },
      secondary_action: { label: "Save a search", href: "/search" },
    });
  }

  return { personalized, general };
}

// -- Component --

export default function TodayPage() {
  const searchParams = useSearchParams();
  const showTour =
    searchParams.get("tour") === "1" &&
    (typeof window !== "undefined" ? localStorage.getItem("tourCompleted") !== "true" : false);

  // Data
  const { data: state, error: stateError } = useSWR("today-state", () => todayApi.state(), {
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
  });
  const { data: highlights } = useSWR("today-highlights", () => todayApi.highlights(), {
    revalidateOnFocus: false,
    dedupingInterval: 300_000,
  });
  const { data: stats } = usePatentStats();
  const { data: themes, isLoading: themesLoading } = useThemes();
  const { data: watchlist, isLoading: watchlistLoading } = useWatchlist();
  const { data: topOpps } = useOpportunityList({
    tab: "top",
    sort: "opportunity_score",
    page_size: 5,
  });
  const { data: expiring, isLoading: expiringLoading } = usePriorityWatch("expiring_soon", 5);
  const { data: companies, isLoading: companiesLoading } = useSuppliers({
    sort_by: "patent_count",
    sort_order: "desc",
    min_patent_count: 2,
    page_size: 5,
  });

  const { data: follows } = useSWR("followed-companies", () => suppliersApi.follows(), {
    revalidateOnFocus: false,
    dedupingInterval: 300_000,
  });

  // Mark seen after data loads — only if not recently marked (prevents
  // rapid-refresh churn that would mislabel the comparison window).
  const markSeenRef = useRef(false);
  useEffect(() => {
    if (state && !stateError && !markSeenRef.current) {
      markSeenRef.current = true;
      todayApi.markSeen().catch(() => {
        // Silent — analytics failure must not block UX
      });
    }
  }, [state, stateError]);

  // Build insights from real data — split into personalized + general
  const followedCompanyNames = useMemo(
    () => new Set((follows || []).map((f: { company_name: string }) => f.company_name.toLowerCase())),
    [follows],
  );
  const { personalized, general } = useMemo(
    () =>
      buildInsights(
        state,
        highlights,
        stats,
        watchlist,
        themes,
        followedCompanyNames,
        topOpps,
        expiring,
        companies,
      ),
    [state, highlights, stats, watchlist, themes, followedCompanyNames, topOpps, expiring, companies],
  );

  const isLoading = themesLoading || watchlistLoading;
  const isFirstTime =
    !isLoading &&
    (!themes || themes.length === 0) &&
    (!watchlist || watchlist.length === 0) &&
    (!state?.last_seen_at);

  // -- States --

  if (isFirstTime) {
    return (
      <div>
        <PageHeader
          title="Today"
          description={
            state?.comparison_label || "Welcome — your first Today briefing"
          }
          freshnessSources={["patents"]}
        />
        <FirstTimeWelcome />
      </div>
    );
  }

  if (stateError) {
    return (
      <div>
        <PageHeader title="Today" freshnessSources={["patents"]} />
        <ErrorState
          title="Unable to load briefing"
          message="The Today briefing data could not be loaded. This may be temporary."
          detail={stateError.message}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div>
      {showTour && (
        <Tour
          onDismiss={() => {
            if (typeof window !== "undefined") window.location.search = "";
          }}
        />
      )}

      <PageHeader
        title="Today"
        description={
          state?.comparison_label ||
          "Your daily patent intelligence briefing"
        }
        freshnessSources={["patents"]}
      />

      {/* Generic platform stats (Total patents, This Week's Highlights, etc.)
          are rendered lower under "Platform Overview" so the user's own
          For You briefing leads the page. */}

      <div className="space-y-6">
        {/* For You — personalized insights */}
        {personalized.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-[var(--accent)] uppercase tracking-wider">
                For You
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {personalized.slice(0, 6).map((insight) => (
                <InsightCard
                  key={insight.id}
                  type={insight.type}
                  title={insight.title}
                  summary={insight.summary}
                  whyItMatters={insight.why_it_matters}
                  evidence={insight.evidence
                    .map((e) => `${e.label}: ${e.value}`)
                    .join(" · ")}
                  confidence={insight.confidence}
                  timestamp={insight.timestamp}
                  primaryAction={insight.primary_action}
                  secondaryAction={insight.secondary_action}
                />
              ))}
            </div>
          </section>
        )}

        {/* Empty personalized state */}
        {personalized.length === 0 && !isLoading && (
          <section className="bg-gradient-to-r from-[var(--bg-elevated)] to-[var(--bg-surface)] rounded-lg border border-[var(--accent)]/20 p-6">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              Personalize your briefing
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Follow companies, save patents, or create topics to get personalized
              intelligence on Today. Generic signals are shown below.
            </p>
            <div className="flex gap-3 mt-3">
              <Link href="/search" className="text-sm text-[var(--accent)] hover:underline">Search patents</Link>
              <Link href="/themes" className="text-sm text-[var(--accent)] hover:underline">Create topics</Link>
              <Link href="/companies" className="text-sm text-[var(--accent)] hover:underline">Browse companies</Link>
            </div>
          </section>
        )}

        {/* More Signals — general insights */}
        {general.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                More Signals
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {general.slice(0, 6).map((insight) => (
                <InsightCard
                  key={insight.id}
                  type={insight.type}
                  title={insight.title}
                  summary={insight.summary}
                  whyItMatters={insight.why_it_matters}
                  evidence={insight.evidence
                    .map((e) => `${e.label}: ${e.value}`)
                    .join(" · ")}
                  confidence={insight.confidence}
                  timestamp={insight.timestamp}
                  primaryAction={insight.primary_action}
                  secondaryAction={insight.secondary_action}
                />
              ))}
            </div>
          </section>
        )}

        {/* Your Topics */}
        {themes && themes.length > 0 ? (
          <section className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">Your Topics</h2>
              <Link href="/themes" className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)]">
                Manage topics →
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {themes.slice(0, 6).map((topic) => (
                <Link
                  key={topic.id}
                  href="/themes"
                  className="rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--accent)]/30 transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium text-sm text-[var(--text-primary)] truncate">
                      {topic.name}
                    </h3>
                    {!topic.is_active && (
                      <Badge variant="default" size="sm">inactive</Badge>
                    )}
                  </div>
                  <p className="text-xs text-[var(--text-muted)]">
                    {topic.patent_count} {topic.patent_count === 1 ? "patent" : "patents"} matched
                  </p>
                </Link>
              ))}
            </div>
          </section>
        ) : (
          <section className="bg-gradient-to-r from-[var(--bg-elevated)] to-[var(--bg-surface)] rounded-lg border border-[var(--accent)]/20 p-6">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              Personalize your briefing
            </h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              <Link href="/themes" className="text-[var(--accent)] hover:underline">
                Create topics
              </Link>{" "}
              to track technology areas that matter to you. Matched patents and
              trend signals will appear here automatically.
            </p>
          </section>
        )}

        {/* Expiring Opportunities */}
        <section className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Expiring Opportunities</h2>
            <Link href="/expiry" className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)]">
              View all →
            </Link>
          </div>
          {expiringLoading ? (
            <LoadingState variant="card" count={3} />
          ) : !expiring?.items?.length ? (
            <EmptyState
              icon="calendar"
              title="No expiring patents in window"
              message="No patents with estimated expiry dates were found in the 5-year window."
              detail="Expiry data is being computed as ingestion and enrichment jobs complete."
              actions={[
                { label: "View Expiry Radar", href: "/expiry", primary: true },
              ]}
            />
          ) : (
            <div className="space-y-2">
              {expiring.items.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-[var(--bg-base)] transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {item.title || "Untitled patent"}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {item.assignees?.[0] || "Unknown"} ·{" "}
                      {item.estimated_expiry_date
                        ? `Expires ${formatDate(item.estimated_expiry_date)}`
                        : "No expiry data"}
                    </p>
                  </div>
                  {item.opportunity_score != null && (
                    <OpportunityScoreBadge score={item.opportunity_score} size="sm" />
                  )}
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Companies Moving */}
        <section className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Companies Moving</h2>
            <Link href="/companies" className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)]">
              View all →
            </Link>
          </div>
          {companiesLoading ? (
            <LoadingState variant="table" count={5} />
          ) : !companies?.items?.length ? (
            <EmptyState
              icon="list"
              title="No company data yet"
              message="Company data is derived from patent assignee records."
              detail="Enrichment runs periodically. Check back after the next data refresh."
              actions={[{ label: "Browse all patents", href: "/patents", primary: true }]}
            />
          ) : (
            <div className="space-y-2">
              {companies.items.slice(0, 5).map((item) => (
                <Link
                  key={item.name}
                  href={`/companies/${encodeURIComponent(item.name)}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-[var(--bg-base)] transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {item.name}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {item.patent_count} patents
                    </p>
                  </div>
                  <span
                    className={`text-sm font-semibold ${
                      item.supplier_score >= 60
                        ? "text-[var(--score-high)]"
                        : item.supplier_score >= 35
                        ? "text-[var(--score-medium)]"
                        : "text-[var(--text-muted)]"
                    }`}
                  >
                    {item.supplier_score}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Platform Overview — generic, non-personalized corpus stats. Kept
            below the personalized sections so Today leads with For You. */}
        {(stats || highlights) && (
          <section>
            <h2 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-3">
              Platform Overview
            </h2>
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <MetricTile label="Total patents" value={stats.total_patents.toLocaleString()} />
                <MetricTile
                  label="New this week"
                  value={stats.patents_this_week.toLocaleString()}
                  highlight
                />
                <MetricTile
                  label="AI summarized"
                  value={stats.summarized_count.toLocaleString()}
                />
                <MetricTile
                  label="Top assignee"
                  value={stats.top_assignees?.[0]?.assignee || "—"}
                />
              </div>
            )}
            {highlights && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {highlights.filing_trend && (
                  <HighlightInsight
                    type="signal"
                    title={highlights.filing_trend.trend_label}
                    summary={`${highlights.filing_trend.count_4w} patents (4wk) · z-score ${highlights.filing_trend.z_score.toFixed(1)}`}
                    detail={
                      highlights.filing_trend.top_assignees.length > 0
                        ? `Top: ${highlights.filing_trend.top_assignees.join(", ")}`
                        : undefined
                    }
                    href={`/trends/${highlights.filing_trend.trend_surface}/${highlights.filing_trend.trend_key}`}
                  />
                )}
                {highlights.expiring_opportunity && (
                  <HighlightInsight
                    type="opportunity"
                    title={`${highlights.expiring_opportunity.count} high-value patents expiring soon`}
                    summary="Within 90-day window with strong opportunity scores."
                    href="/expiry?expiry_status=expiring_soon&min_expiry_opportunity_score=70"
                  />
                )}
                {highlights.notable_patent && (
                  <HighlightInsight
                    type="signal"
                    title={highlights.notable_patent.title || highlights.notable_patent.publication_number}
                    summary={`${highlights.notable_patent.assignee} · Opportunity score ${highlights.notable_patent.opportunity_score.toFixed(1)}`}
                    detail={highlights.notable_patent.summary_first_sentence}
                    href={`/patents/${highlights.notable_patent.id}`}
                  />
                )}
                {highlights.company_move && (
                  <HighlightInsight
                    type="update"
                    title={`${highlights.company_move.assignee}: +${highlights.company_move.delta} filing surge`}
                    summary={`${highlights.company_move.count_this_week} this week vs ${highlights.company_move.count_4wk_avg.toFixed(1)} avg`}
                    href={`/companies/${encodeURIComponent(highlights.company_move.assignee)}`}
                  />
                )}
              </div>
            )}
          </section>
        )}

        {/* Recommended Actions */}
        <section className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
            Recommended Actions
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <ActionSuggestion
              label="Save a search"
              description="Create a saved patent search for technology areas you track."
              href="/search"
            />
            <ActionSuggestion
              label="Review watchlist"
              description={
                watchlist && watchlist.length > 0
                  ? `You have ${watchlist.length} saved patents. Check for updates.`
                  : "Save patents to build your personal intelligence workspace."
              }
              href="/watchlist"
            />
            <ActionSuggestion
              label="Explore expiry opportunities"
              description="Find patents approaching expiration in your technology areas."
              href="/expiry"
            />
            <ActionSuggestion
              label="Browse companies"
              description="See which organizations are filing in your areas of interest."
              href="/companies"
            />
          </div>
        </section>
      </div>

      <div className="mt-8">
        <SourceAttribution />
        <FeedbackWidget screen="today" />
      </div>
    </div>
  );
}

// -- Sub-components --

function FirstTimeWelcome() {
  return (
    <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] p-8 text-center">
      <div className="max-w-lg mx-auto">
        <div className="text-4xl mb-4">📊</div>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
          Welcome to Invention Index 8
        </h2>
        <p className="text-sm text-[var(--text-secondary)] mb-6">
          Track patent filings, spot expiring opportunities, and discover
          commercial signals across any technology area. Today gets better as
          you save patents, searches, companies, and technology areas.
        </p>
        <StarterTopics showHeading={false} />
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
          <div className="rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] p-4">
            <div className="text-lg mb-1">🔍</div>
            <h3 className="font-medium text-sm text-[var(--text-primary)]">
              Search by technology
            </h3>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Find patents in semiconductor packaging, battery tech, AI/ML, and more
            </p>
            <Link
              href="/search"
              className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block"
            >
              Start searching →
            </Link>
          </div>
          <div className="rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] p-4">
            <div className="text-lg mb-1">📈</div>
            <h3 className="font-medium text-sm text-[var(--text-primary)]">
              Explore trends
            </h3>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Hot tech areas, growing assignees, and filing momentum
            </p>
            <Link
              href="/trends"
              className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block"
            >
              See trends →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function HighlightInsight({
  type,
  title,
  summary,
  detail,
  href,
}: {
  type: "signal" | "opportunity" | "update";
  title: string;
  summary: string;
  detail?: string;
  href: string;
}) {
  const colors = {
    signal: "bg-[var(--accent-muted)] text-[var(--accent)]",
    opportunity: "bg-[var(--score-high-bg)] text-[var(--score-high)]",
    update: "bg-[var(--text-muted)]/12 text-[var(--text-muted)]",
  };
  const labels = { signal: "Trend", opportunity: "Expiry", update: "Update" };

  return (
    <Link
      href={href}
      className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--accent)]/30 transition-colors"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${colors[type]}`}>
          {labels[type]}
        </span>
      </div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
        {title}
      </h3>
      <p className="text-xs text-[var(--text-muted)]">{summary}</p>
      {detail && (
        <p className="text-xs text-[var(--text-secondary)] mt-1 truncate">
          {detail}
        </p>
      )}
    </Link>
  );
}

function MetricTile({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-3 ${
        highlight
          ? "bg-[var(--bg-elevated)] border-[var(--accent)]/20"
          : "bg-[var(--bg-surface)] border-[var(--border-subtle)]"
      }`}
    >
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <p
        className={`text-lg font-bold truncate ${
          highlight ? "text-[var(--accent)]" : "text-[var(--text-primary)]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function ActionSuggestion({
  label,
  description,
  href,
}: {
  label: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--accent)]/30 transition-colors"
    >
      <h3 className="font-medium text-sm text-[var(--text-primary)]">{label}</h3>
      <p className="text-xs text-[var(--text-muted)] mt-1">{description}</p>
      <span className="text-xs text-[var(--accent)] mt-2 inline-block">
        Go →
      </span>
    </Link>
  );
}

// ── V3.2 For You Feed ──────────────────────────────────────────────────

function ForYouFeedSection() {
  const { data, error } = useSWR("today-feed", () =>
    fetch("/api/v1/today/feed", { credentials: "include" }).then((r) => r.json())
  );

  if (error) return null;
  if (!data) {
    return (
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-[var(--accent)] uppercase tracking-wider mb-3">For You</h2>
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 text-center">
          <div className="animate-pulse space-y-2">
            <div className="h-4 w-3/4 mx-auto bg-[var(--bg-glass)] rounded" />
            <div className="h-3 w-1/2 mx-auto bg-[var(--bg-glass)] rounded" />
          </div>
        </div>
      </section>
    );
  }

  const items: FeedItemType[] = data?.feed_items || [];
  if (items.length === 0) return null;

  return (
    <section className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-[var(--accent)] uppercase tracking-wider">For You</h2>
        <span className="text-[11px] text-[var(--text-muted)]">{items.length} signal{items.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map((item) => (
          <ForYouCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}
