"use client";

import Link from "next/link";
import useSWR from "swr";
import { BRAND } from "@/lib/brand";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { StarterTopics } from "@/components/ui/StarterTopics";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { useOpportunityList } from "@/hooks/useOpportunity";
import { useHotTrends } from "@/hooks/useTrends";
import { usePriorityWatch, usePatentStats } from "@/hooks/usePatents";
import { useSuppliers } from "@/hooks/useSuppliers";
import { useThemes } from "@/hooks/useThemes";
import { useWatchlist } from "@/hooks/useWatchlist";
import { todayApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type {
  FilingTrendCard,
  ExpiringOpportunityCard,
  NotablePatentCard,
  CompanyMoveCard,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Highlight card components (Step 9)
// ---------------------------------------------------------------------------

function FilingTrendHighlight({ data }: { data: FilingTrendCard | null }) {
  if (!data) return null;
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">Trend</span>
        <span className="text-xs text-gray-400">Filing momentum</span>
      </div>
      <Link
        href={`/trends/${data.trend_surface}/${data.trend_key}`}
        className="text-sm font-semibold text-gray-900 hover:text-primary-700"
      >
        {data.trend_label}
      </Link>
      <p className="text-xs text-gray-500 mt-1">
        {data.count_4w} patents (4wk) · z-score {data.z_score}
      </p>
      {data.top_assignees.length > 0 && (
        <p className="text-xs text-gray-500 mt-1 truncate">
          Top: {data.top_assignees.join(", ")}
        </p>
      )}
    </div>
  );
}

function ExpiringOppHighlight({ data }: { data: ExpiringOpportunityCard | null }) {
  if (!data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">Expiry</span>
          <span className="text-xs text-gray-400">High-opportunity window</span>
        </div>
        <p className="text-sm text-gray-500">
          No high-value patents expiring within 90 days yet.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          As v3 scoring reaches more patents, this card will populate.{" "}
          <Link href="/expiry" className="text-primary-600 hover:underline">
            Browse all expiry data →
          </Link>
        </p>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">Expiry</span>
        <span className="text-xs text-gray-400">High-opportunity window</span>
      </div>
      <Link
        href="/expiry?expiry_status=expiring_soon&min_expiry_opportunity_score=70"
        className="text-sm font-semibold text-gray-900 hover:text-primary-700"
      >
        {data.count} high-value patents expiring within 90 days
      </Link>
      <p className="text-xs text-gray-400 mt-1">{data.caveat}</p>
    </div>
  );
}

function NotablePatentHighlight({ data }: { data: NotablePatentCard | null }) {
  if (!data) return null;
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-green-100 text-green-700">Notable</span>
        <span className="text-xs text-gray-400">Recent high-scorer</span>
      </div>
      <Link
        href={`/patents/${data.id}`}
        className="text-sm font-semibold text-gray-900 hover:text-primary-700 line-clamp-1"
      >
        {data.title || data.publication_number}
      </Link>
      <p className="text-xs text-gray-500 mt-1">
        {data.assignee} · {data.publication_number}
      </p>
      {data.summary_first_sentence && (
        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
          {data.summary_first_sentence}
        </p>
      )}
      <div className="flex items-center gap-2 mt-2">
        {data.limited_source && (
          <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
            Limited source text available
          </span>
        )}
      </div>
    </div>
  );
}

function CompanyMoveHighlight({ data }: { data: CompanyMoveCard | null }) {
  if (!data) return null;
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">Company</span>
        <span className="text-xs text-gray-400">Filing surge</span>
      </div>
      <Link
        href={`/companies/${encodeURIComponent(data.assignee)}`}
        className="text-sm font-semibold text-gray-900 hover:text-primary-700"
      >
        {data.assignee}
      </Link>
      <p className="text-xs text-gray-500 mt-1">
        {data.count_this_week} filings this week · +{data.delta} vs 4wk avg
      </p>
    </div>
  );
}

function AtAGlanceCard({
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
          ? "bg-primary-50 border-primary-200"
          : "bg-white border-gray-200"
      }`}
    >
      <p className="text-xs text-gray-500">{label}</p>
      <p
        className={`text-lg font-bold truncate ${
          highlight ? "text-primary-700" : "text-gray-900"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function FirstTimeOnboarding() {
  return (
    <div className="rounded-lg bg-white border border-gray-200 p-8 text-center">
      <div className="max-w-lg mx-auto">
        <div className="text-4xl mb-4">📊</div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          Welcome to {BRAND.name}
        </h2>
        <p className="text-sm text-gray-600 mb-6">
          Track patent filings, spot expiring opportunities, and discover
          commercial signals across any technology area. Start by creating
          a topic below — your personalized command center will appear here.
        </p>
        <StarterTopics showHeading={false} />
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-4">
            <div className="text-lg mb-1">🔍</div>
            <h3 className="font-medium text-sm text-gray-900">Browse all patents</h3>
            <p className="text-xs text-gray-500 mt-1">
              63,000+ patents from USPTO, EPO, and WIPO
            </p>
            <Link
              href="/patents"
              className="text-xs text-primary-600 hover:underline mt-2 inline-block"
            >
              Start browsing →
            </Link>
          </div>
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-4">
            <div className="text-lg mb-1">📈</div>
            <h3 className="font-medium text-sm text-gray-900">Explore trends</h3>
            <p className="text-xs text-gray-500 mt-1">
              Hot tech areas, growing assignees, and cliff analysis
            </p>
            <Link
              href="/trends"
              className="text-xs text-primary-600 hover:underline mt-2 inline-block"
            >
              See trends →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function TodayPage() {
  // Data hooks — all existing, all SWR-cached
  const { data: topOpps, isLoading: topOppsLoading } = useOpportunityList({
    tab: "top",
    sort: "opportunity_score",
    page_size: 5,
  });
  const { data: hotTrends, isLoading: trendsLoading } = useHotTrends(undefined, 5);
  const { data: expiring, isLoading: expiringLoading } = usePriorityWatch("expiring_soon", 5);
  const { data: companies, isLoading: companiesLoading } = useSuppliers({
    sort_by: "patent_count",
    sort_order: "desc",
    min_patent_count: 2,
    page_size: 5,
  });
  // First-time user detection
  const { data: themes, isLoading: themesLoading } = useThemes();
  const { data: watchlist, isLoading: watchlistLoading } = useWatchlist();
  const { data: stats } = usePatentStats();
  const { data: highlights } = useSWR(
    "today-highlights",
    () => todayApi.highlights(),
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );

  const isLoading = themesLoading || watchlistLoading;
  const isFirstTime =
    !isLoading &&
    (!themes || themes.length === 0) &&
    (!watchlist || watchlist.length === 0);

  if (isFirstTime) {
    return (
      <div>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Today</h1>
          <FreshnessBanner className="mt-2" />
        </div>
        <FirstTimeOnboarding />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Today</h1>
        <FreshnessBanner className="mt-2" />
        <p className="text-gray-600 mt-1">
          Your daily patent intelligence briefing
        </p>
      </div>

      {/* Patent Index */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <AtAGlanceCard label="Total patents" value={stats.total_patents.toLocaleString()} />
          <AtAGlanceCard label="New this week" value={stats.patents_this_week.toLocaleString()} highlight />
          <AtAGlanceCard label="AI summarized" value={stats.summarized_count.toLocaleString()} />
          <AtAGlanceCard
            label="Top assignee"
            value={stats.top_assignees?.[0]?.assignee || "—"}
          />
        </div>
      )}

      {/* Data freshness note */}
      <div className="mb-6 text-xs text-gray-400 flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400"></span>
        Patent intelligence updates continuously as enrichment, scoring, and
        summarization jobs complete. Forward citation coverage is affected by
        USPTO availability.{" "}
        <Link href="/admin/data-health" className="text-primary-600 hover:underline">
          View pipeline status →
        </Link>
      </div>

      {/* What's New This Week */}
      {highlights && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            What&apos;s New This Week
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FilingTrendHighlight data={highlights.filing_trend} />
            <ExpiringOppHighlight data={highlights.expiring_opportunity} />
            <NotablePatentHighlight data={highlights.notable_patent} />
            <CompanyMoveHighlight data={highlights.company_move} />
          </div>
        </div>
      )}

      <div className="space-y-6">
        {/* Your Topics — or prompt to create them */}
        {themes && themes.length > 0 ? (
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Your Topics</h2>
              <Link href="/themes" className="text-sm text-primary-600 hover:text-primary-800">
                Manage topics →
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {themes.slice(0, 6).map((topic) => (
                <Link
                  key={topic.id}
                  href={`/themes`}
                  className="rounded-lg border border-gray-200 p-4 hover:border-primary-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium text-sm text-gray-900 truncate">{topic.name}</h3>
                    {!topic.is_active && (
                      <Badge variant="default" size="sm" className="text-gray-400">inactive</Badge>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {topic.cpc_prefixes.slice(0, 3).map((cpc) => (
                      <span key={cpc} className="text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5">
                        {cpc}
                      </span>
                    ))}
                    {topic.cpc_prefixes.length > 3 && (
                      <span className="text-xs text-gray-400">+{topic.cpc_prefixes.length - 3}</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    {topic.patent_count} {topic.patent_count === 1 ? "patent" : "patents"} matched
                  </p>
                </Link>
              ))}
            </div>
          </section>
        ) : (
          <section className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-lg border border-primary-200 p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Your {BRAND.name}</h2>
                <p className="text-sm text-gray-600 mt-1">
                  <Link href="/themes" className="text-primary-600 hover:underline">
                    Create topics
                  </Link>{" "}
                  to track technology areas that matter to you. Matched patents and
                  trend signals will appear here automatically.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Your saved patents — discoverability for watchlist */}
        {watchlist && watchlist.length > 0 && (
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Your Saved Patents</h2>
              <Link href="/watchlist" className="text-sm text-primary-600 hover:text-primary-800">
                View all ({watchlist.length}) →
              </Link>
            </div>
            <div className="space-y-2">
              {watchlist.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.patent.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.patent.title || "Untitled patent"}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.patent.assignees?.[0] || "Unknown"} · {item.patent.doc_id}
                    </p>
                  </div>
                  {item.patent.opportunity_score != null && (
                    <OpportunityScoreBadge score={item.patent.opportunity_score} size="sm" />
                  )}
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Top Opportunities */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Top Opportunities</h2>
            <Link href="/opportunity" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {topOppsLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded" />
              ))}
            </div>
          ) : !topOpps?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No opportunity data yet. Run opportunity scoring via Admin → AI Runs.
            </p>
          ) : (
            <div className="space-y-2">
              {topOpps.items.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.title || "Untitled patent"}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.assignees?.[0] || "Unknown"} · {item.doc_id}
                    </p>
                  </div>
                  <OpportunityScoreBadge score={item.opportunity_score} size="sm" />
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Emerging Trends */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Emerging Trends</h2>
            <Link href="/trends" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {trendsLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded" />
              ))}
            </div>
          ) : !hotTrends?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No trend data yet. Run weekly trend computation first.
            </p>
          ) : (
            <div className="space-y-2">
              {hotTrends.items.slice(0, 5).map((item) => (
                <div
                  key={`${item.surface}-${item.key}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="default" size="sm">{item.surface}</Badge>
                      <p className="text-sm font-medium text-gray-900 truncate">{item.key}</p>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.count_4w} patents (4wk) · z-score {item.z_score.toFixed(1)}
                    </p>
                  </div>
                  <div className={`text-sm font-semibold ${item.growth_pct > 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {item.growth_pct > 0 ? "+" : ""}{item.growth_pct.toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Expiring Opportunities */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Expiring Opportunities</h2>
            <Link href="/expiry" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {expiringLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded" />
              ))}
            </div>
          ) : !expiring?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No expiring patents found in the 5-year window.
            </p>
          ) : (
            <div className="space-y-2">
              {expiring.items.slice(0, 5).map((item) => (
                <Link
                  key={item.id}
                  href={`/patents/${item.id}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {item.title || "Untitled patent"}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
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
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Companies Moving</h2>
            <Link href="/companies" className="text-sm text-primary-600 hover:text-primary-800">
              View all →
            </Link>
          </div>

          {companiesLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded" />
              ))}
            </div>
          ) : !companies?.items?.length ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No company data available yet.
            </p>
          ) : (
            <div className="space-y-2">
              {companies.items.slice(0, 5).map((item) => (
                <Link
                  key={item.name}
                  href={`/companies/${encodeURIComponent(item.name)}`}
                  className="flex items-center justify-between gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {item.active_patent_count} active · {item.technology_area_count} tech areas
                      {item.country ? ` · ${item.country}` : ""}
                    </p>
                  </div>
                  <span className={`text-sm font-semibold ${item.supplier_score >= 60 ? "text-green-600" : item.supplier_score >= 35 ? "text-yellow-600" : "text-gray-500"}`}>
                    {item.supplier_score}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="mt-8">
        <SourceAttribution />
      </div>
    </div>
  );
}
