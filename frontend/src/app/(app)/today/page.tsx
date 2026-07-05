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
import { Score } from "@/components/ui/Score";
import { StarterTopics } from "@/components/ui/StarterTopics";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { FeedbackWidget } from "@/components/ui/FeedbackWidget";
import { Tour } from "@/components/tour/Tour";
import { useDiversifiedFeed } from "@/hooks/useDiversifiedFeed";
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

// ── Types ────────────────────────────────────────────────────────────────

interface FeedItem {
  id: string;
  feedType: string; // for diversification: expiry_opportunity, filing_trend, notable_patent, company_move, watchlist, topic_activity, platform
  card: React.ReactNode;
}

// ── Insight builders ─────────────────────────────────────────────────────

function buildFeed(
  state: TodayState | undefined,
  highlights: {
    filing_trend: FilingTrendCard | null;
    expiring_opportunity: ExpiringOpportunityCard | null;
    notable_patent: NotablePatentCard | null;
    company_move: CompanyMoveCard | null;
  } | undefined,
  stats:
    | {
        total_patents: number;
        patents_this_week: number;
        summarized_count: number;
        top_assignees?: { assignee: string; count: number }[];
      }
    | undefined,
  watchlist: unknown[] | undefined,
  userTopics: Topic[] | undefined,
  followedCompanyNames: Set<string>,
): FeedItem[] {
  const items: FeedItem[] = [];
  const now = new Date().toISOString();
  const wlItems = (watchlist as WatchlistItemResponse[] | undefined) || [];

  // Watchlist activity (personalized)
  if (wlItems.length > 0) {
    items.push({
      id: "watchlist-count",
      feedType: "watchlist",
      card: (
        <InsightCard
          key="watchlist-count"
          type="update"
          title={`${wlItems.length} patent${
            wlItems.length !== 1 ? "s" : ""
          } in your watchlist`}
          summary={
            wlItems.length > 3
              ? `Top: ${wlItems
                  .slice(0, 3)
                  .map((w) => w.patent.title || w.patent.doc_id)
                  .join(", ")}`
              : wlItems
                  .map((w) => w.patent.title || w.patent.doc_id)
                  .join(" · ")
          }
          whyItMatters="Patents you've saved. Monitor them for updates, related citations, and expiry changes."
          evidence={`Saved patents: ${wlItems.length} · From watchlist · Your personal watchlist`}
          confidence="high"
          timestamp={now}
          primaryAction={{ label: "Open watchlist", href: "/watchlist" }}
          personalization={{
            whyShown: "Shown because these are your saved patents.",
          }}
        />
      ),
    });
  }

  // Filing trend
  if (highlights?.filing_trend) {
    const t = highlights.filing_trend;
    items.push({
      id: `trend-${t.trend_surface}-${t.trend_key}`,
      feedType: "filing_trend",
      card: (
        <InsightCard
          key={`trend-${t.trend_surface}-${t.trend_key}`}
          type="signal"
          title={`${t.trend_label} filing activity trending up`}
          summary={`${t.count_4w} patents filed in the last 4 weeks with a z-score of ${t.z_score.toFixed(
            1
          )}, indicating above-average activity.`}
          whyItMatters="Above-average filing momentum may signal competitive R&D investment."
          evidence={`4-week count: ${t.count_4w} · Z-score: ${t.z_score.toFixed(
            1
          )}${t.top_assignees.length > 0 ? ` · Top assignees: ${t.top_assignees.join(", ")}` : ""}`}
          confidence="medium"
          timestamp={now}
          primaryAction={{
            label: "View trend detail",
            href: `/trends/${t.trend_surface}/${t.trend_key}`,
          }}
          secondaryAction={{ label: "Explore trends", href: "/trends" }}
        />
      ),
    });
  }

  // Expiring opportunities
  if (highlights?.expiring_opportunity) {
    const e = highlights.expiring_opportunity;
    items.push({
      id: "expiring-opportunities",
      feedType: "expiry_opportunity",
      card: (
        <InsightCard
          key="expiring-opportunities"
          type="opportunity"
          title={`${e.count} high-value patents expiring within 90 days`}
          summary={`${e.count} patents with strong opportunity scores are approaching estimated expiry.`}
          whyItMatters="Expiring patents may create design freedom or licensing opportunities. Verify with official registers before acting."
          evidence={`Count: ${e.count} · Window: 90 days`}
          confidence="medium"
          timestamp={now}
          primaryAction={{
            label: "View Expiry Radar",
            href: "/expiry?expiry_status=expiring_soon&min_expiry_opportunity_score=70",
          }}
          secondaryAction={{ label: "All expiry data", href: "/expiry" }}
        />
      ),
    });
  }

  // Notable patent
  if (highlights?.notable_patent) {
    const n = highlights.notable_patent;
    items.push({
      id: `notable-${n.id}`,
      feedType: "notable_patent",
      card: (
        <InsightCard
          key={`notable-${n.id}`}
          type="signal"
          title={n.title || n.publication_number}
          summary={
            n.summary_first_sentence ||
            `Patent from ${n.assignee || "unknown assignee"} with high opportunity score.`
          }
          whyItMatters={`Strong opportunity score (${Math.round(
            n.opportunity_score
          )}) suggests commercial relevance in its technology area.`}
          evidence={`Assignee: ${n.assignee || "Unknown"} · Opportunity score: ${Math.round(n.opportunity_score)} · Doc ID: ${n.doc_id}`}
          confidence={
            n.has_abstract && n.has_claims && !n.limited_source
              ? "high"
              : "medium"
          }
          timestamp={now}
          primaryAction={{
            label: "View patent",
            href: `/patents/${n.id}`,
          }}
        />
      ),
    });
  }

  // Company move
  if (highlights?.company_move) {
    const c = highlights.company_move;
    const isFollowed = followedCompanyNames.has(c.assignee.toLowerCase());
    const why = isFollowed
      ? `Shown because you follow ${c.assignee}. Their filing surge of +${c.delta} vs average may signal a new product cycle, strategic IP push, or competitive positioning relevant to your watch.`
      : "A filing surge may indicate a new product cycle, strategic IP push, or competitive positioning.";
    items.push({
      id: `company-${c.assignee}`,
      feedType: "company_move",
      card: (
        <InsightCard
          key={`company-${c.assignee}`}
          type="update"
          title={`${c.assignee} filing surge: +${c.delta} vs 4-week average`}
          summary={`${c.count_this_week} filings this week compared to a ${c.count_4wk_avg.toFixed(
            1
          )} weekly average.`}
          whyItMatters={why}
          evidence={`This week: ${c.count_this_week} · 4-week avg: ${c.count_4wk_avg.toFixed(1)} · Delta: +${c.delta}`}
          confidence="medium"
          timestamp={now}
          primaryAction={{
            label: "View company profile",
            href: `/companies/${encodeURIComponent(c.assignee)}`,
          }}
          secondaryAction={{ label: "All companies", href: "/companies" }}
          personalization={
            isFollowed ? { whyShown: `You follow ${c.assignee}.` } : undefined
          }
        />
      ),
    });
  }

  // New patents this week (platform signal)
  if (stats && stats.patents_this_week > 0) {
    items.push({
      id: "new-patents-week",
      feedType: "platform",
      card: (
        <InsightCard
          key="new-patents-week"
          type="update"
          title={`${stats.patents_this_week.toLocaleString()} new patents this week`}
          summary={`The patent corpus grew by ${stats.patents_this_week.toLocaleString()} records since your last visit window.`}
          whyItMatters="New filings may indicate competitor activity or emerging technology areas."
          evidence={`New patents: ${stats.patents_this_week} · Total corpus: ${stats.total_patents}`}
          confidence="high"
          timestamp={now}
          primaryAction={{
            label: "Browse new patents",
            href: "/patents?sort_by=publication_date&sort_order=desc",
          }}
          secondaryAction={{
            label: "Search by technology",
            href: "/search",
          }}
        />
      ),
    });
  }

  return items;
}

// ── Page Component ────────────────────────────────────────────────────────

export default function TodayPage() {
  const searchParams = useSearchParams();
  const showTour =
    searchParams.get("tour") === "1" &&
    (typeof window !== "undefined"
      ? localStorage.getItem("tourCompleted") !== "true"
      : false);

  // Data fetches
  const { data: state, error: stateError } = useSWR(
    "today-state",
    () => todayApi.state(),
    { revalidateOnFocus: false, dedupingInterval: 60_000 }
  );
  const { data: highlights } = useSWR(
    "today-highlights",
    () => todayApi.highlights(),
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );
  const { data: stats } = usePatentStats();
  const { data: themes, isLoading: themesLoading } = useThemes();
  const { data: watchlist, isLoading: watchlistLoading } = useWatchlist();
  const { data: expiring, isLoading: expiringLoading } = usePriorityWatch(
    "expiring_soon",
    5
  );
  const { data: companies, isLoading: companiesLoading } = useSuppliers({
    sort_by: "patent_count",
    sort_order: "desc",
    min_patent_count: 2,
    page_size: 5,
  });
  const { data: follows } = useSWR(
    "followed-companies",
    () => suppliersApi.follows(),
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );

  // Mark seen
  const markSeenRef = useRef(false);
  useEffect(() => {
    if (state && !stateError && !markSeenRef.current) {
      markSeenRef.current = true;
      todayApi.markSeen().catch(() => {});
    }
  }, [state, stateError]);

  // Derived state
  const followedCompanyNames = useMemo(
    () =>
      new Set(
        (follows || []).map((f: { company_name: string }) =>
          f.company_name.toLowerCase()
        )
      ),
    [follows]
  );

  const feedItems = useMemo(
    () =>
      buildFeed(
        state,
        highlights,
        stats,
        watchlist,
        themes,
        followedCompanyNames
      ),
    [state, highlights, stats, watchlist, themes, followedCompanyNames]
  );

  // Diversify the feed
  const diversifiedItems = useDiversifiedFeed(feedItems, {
    typeOf: (item) => item.feedType,
    maxConsecutive: 2,
    maxShareOfType: 0.4,
  });

  const isLoading = themesLoading || watchlistLoading;
  const isFirstTime =
    !isLoading &&
    (!themes || themes.length === 0) &&
    (!watchlist || watchlist.length === 0) &&
    !state?.last_seen_at;

  // Comparison label for return-trigger
  const comparisonLabel = state?.comparison_label;

  // ── States ──────────────────────────────────────────────────────────

  if (isFirstTime) {
    return (
      <div>
        <PageHeader
          title="Today"
          description="Welcome — your first Today briefing"
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

  // Show platform overview + stats even for first-time visitors.
  // The first-time wrapper is shown as a banner, not a page replacement.
  if (isFirstTime) {
    return (
      <div>
        <PageHeader
          title="Today"
          description="Welcome — your first Today briefing"
          freshnessSources={["patents"]}
        />
        <FirstTimeWelcome />
        {/* Render platform overview below onboarding for first-time users */}
        {stats && (
          <PlatformOverview stats={stats} highlights={highlights} watchlist={watchlist} />
        )}
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────

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
          comparisonLabel
            ? `Since your last visit (${comparisonLabel})`
            : "Your daily patent intelligence briefing"
        }
        freshnessSources={["patents"]}
      />

      <div className="space-y-6">
        {/* ── For You — unified, diversified feed ── */}
        {diversifiedItems.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-[var(--text)] uppercase tracking-wider">
                For You
              </h2>
              <span className="text-[11px] text-[var(--text-muted)]">
                {diversifiedItems.length} signal
                {diversifiedItems.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {diversifiedItems.map((item) => item.card)}
            </div>
          </section>
        )}

        {/* Empty personalized state */}

        {/* ── Your Topics ── */}
        {themes && themes.length > 0 && (
          <section className="bg-[var(--surface)] rounded-[var(--radius-lg)] border border-[var(--border)] p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-[var(--text)]">
                Your Topics
              </h2>
              <Link
                href="/themes"
                className="text-xs text-[var(--accent)] hover:underline"
              >
                Manage →
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {themes.slice(0, 6).map((topic) => (
                <Link
                  key={topic.id}
                  href="/themes"
                  className="rounded-[var(--radius-md)] border border-[var(--border)] p-3 hover:border-[var(--accent)]/30 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium text-sm text-[var(--text)] truncate">
                      {topic.name}
                    </h3>
                    {!topic.is_active && (
                      <Badge variant="default" size="sm">
                        inactive
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-[var(--text-muted)]">
                    {topic.patent_count}{" "}
                    {topic.patent_count === 1 ? "patent" : "patents"} matched
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* ── Expiring Opportunities ── */}
        <section className="bg-[var(--surface)] rounded-[var(--radius-lg)] border border-[var(--border)] p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--text)]">
              Expiring Opportunities
            </h2>
            <Link
              href="/expiry"
              className="text-xs text-[var(--accent)] hover:underline"
            >
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
                {
                  label: "View Expiry Radar",
                  href: "/expiry",
                  primary: true,
                },
              ]}
            />
          ) : (
            <div className="space-y-2">
              {expiring.items.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-[var(--radius-sm)] hover:bg-[var(--bg-glass)] transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--text)] truncate">
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
                    <Score
                      value={item.opportunity_score}
                      kind="opportunity"
                      size="sm"
                    />
                  )}
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* ── Companies Moving ── */}
        <section className="bg-[var(--surface)] rounded-[var(--radius-lg)] border border-[var(--border)] p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--text)]">
              Companies Moving
            </h2>
            <Link
              href="/companies"
              className="text-xs text-[var(--accent)] hover:underline"
            >
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
              actions={[
                {
                  label: "Browse all patents",
                  href: "/patents",
                  primary: true,
                },
              ]}
            />
          ) : (
            <div className="space-y-2">
              {companies.items.slice(0, 5).map((item) => (
                <Link
                  key={item.name}
                  href={`/companies/${encodeURIComponent(item.name)}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-[var(--radius-sm)] hover:bg-[var(--bg-glass)] transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--text)] truncate">
                      {item.name}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {item.patent_count} patents
                    </p>
                  </div>
                  <Score
                    value={item.supplier_score}
                    kind="composite"
                    size="sm"
                  />
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* ── Platform Overview (collapsed accordion) ── */}
        <PlatformOverview
          stats={stats}
          highlights={highlights}
          watchlist={watchlist}
        />
      </div>

      <div className="mt-8">
        <SourceAttribution />
        <FeedbackWidget screen="today" />
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function FirstTimeWelcome() {
  return (
    <div className="rounded-[var(--radius-lg)] bg-[var(--surface)] border border-[var(--border)] p-8 text-center">
      <div className="max-w-lg mx-auto">
        <div className="text-4xl mb-4">📊</div>
        <h2 className="text-xl font-bold text-[var(--text)] mb-2">
          Welcome to Invention Index 8
        </h2>
        <p className="text-sm text-[var(--text-2)] mb-6">
          Track patent filings, spot expiring opportunities, and discover
          commercial signals across any technology area. Today gets better as
          you save patents, searches, companies, and technology areas.
        </p>
        <StarterTopics showHeading={false} />
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
          <div className="rounded-[var(--radius-md)] bg-[var(--bg)] border border-[var(--border)] p-4">
            <div className="text-lg mb-1">🔍</div>
            <h3 className="font-medium text-sm text-[var(--text)]">
              Search by technology
            </h3>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Find patents in semiconductor packaging, battery tech, AI/ML, and
              more
            </p>
            <Link
              href="/search"
              className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block"
            >
              Start searching →
            </Link>
          </div>
          <div className="rounded-[var(--radius-md)] bg-[var(--bg)] border border-[var(--border)] p-4">
            <div className="text-lg mb-1">📈</div>
            <h3 className="font-medium text-sm text-[var(--text)]">
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

function PlatformOverview({
  stats,
  highlights,
  watchlist,
}: {
  stats:
    | {
        total_patents: number;
        patents_this_week: number;
        summarized_count: number;
        top_assignees?: { assignee: string; count: number }[];
      }
    | undefined;
  highlights:
    | {
        filing_trend: FilingTrendCard | null;
        expiring_opportunity: ExpiringOpportunityCard | null;
        notable_patent: NotablePatentCard | null;
        company_move: CompanyMoveCard | null;
      }
    | undefined;
  watchlist: WatchlistItemResponse[] | undefined;
}) {
  return (
    <details className="group">
      <summary className="cursor-pointer text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider py-2 hover:text-[var(--text-2)] transition-colors select-none">
        Platform Overview
      </summary>
      <div className="pt-3 space-y-4">
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricTile
              label="Total patents"
              value={stats.total_patents.toLocaleString()}
            />
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
                title={
                  highlights.notable_patent.title ||
                  highlights.notable_patent.publication_number
                }
                summary={`${highlights.notable_patent.assignee} · Opportunity score ${Math.round(highlights.notable_patent.opportunity_score)}`}
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
      </div>
    </details>
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
    signal: "bg-[var(--accent-muted)] text-[var(--type-trend)]",
    opportunity: "bg-[var(--ok-bg)] text-[var(--ok)]",
    update: "bg-[var(--text-muted)]/12 text-[var(--text-muted)]",
  };
  const labels = { signal: "Trend", opportunity: "Expiry", update: "Update" };

  return (
    <div className="bg-[var(--surface)] rounded-[var(--radius-md)] border border-[var(--border)] p-4">
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`text-xs font-medium px-1.5 py-0.5 rounded ${colors[type]}`}
        >
          {labels[type]}
        </span>
      </div>
      <h3 className="text-sm font-semibold text-[var(--text)] mb-1">
        {title}
      </h3>
      <p className="text-xs text-[var(--text-muted)]">{summary}</p>
      {detail && (
        <p className="text-xs text-[var(--text-2)] mt-1 truncate">{detail}</p>
      )}
      {href && (
        <Link
          href={href}
          className="text-xs text-[var(--accent)] hover:underline mt-1 inline-block"
        >
          View →
        </Link>
      )}
    </div>
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
      className={`rounded-[var(--radius-md)] border p-3 ${
        highlight
          ? "bg-[var(--elevated)] border-[var(--border)]"
          : "bg-[var(--surface)] border-[var(--border)]"
      }`}
    >
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <p
        className={`text-lg font-bold truncate ${
          highlight ? "text-[var(--text)] font-bold" : "text-[var(--text)]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
