"use client";

import { use } from "react";
import Link from "next/link";
import { usePatent, usePatentSummary } from "@/hooks/usePatents";
import { AISummaryPanel } from "@/components/patents/AISummaryPanel";
import { ScoreBadge } from "@/components/patents/ScoreBadge";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { OpportunityBreakdown } from "@/components/patents/OpportunityBreakdown";
import { TagsPanel } from "@/components/patents/TagsPanel";
import { LegalConfidenceBadge } from "@/components/patents/LegalConfidenceBadge";
import { RiskFlagsBadge } from "@/components/patents/RiskFlagsBadge";
import { WhyNowPanel } from "@/components/patents/WhyNowPanel";
import { OpportunityNarrativePanel } from "@/components/patents/OpportunityNarrativePanel";
import { TrendSnapshotPanel } from "@/components/patents/TrendSnapshotPanel";
import { AssigneeIntelligencePanel } from "@/components/patents/AssigneeIntelligencePanel";
import { ClaimsPanel } from "@/components/patents/ClaimsPanel";
import { ExternalPatentLinks } from "@/components/patents/ExternalPatentLinks";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import { patentsApi } from "@/lib/api";
import { useWatchlistCheck, addToWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import { useState } from "react";

export default function PatentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: patent, isLoading } = usePatent(id);
  const { data: summary, isLoading: summaryLoading } = usePatentSummary(
    patent?.summarized_at ? null : id
  );

  const displaySummary = (patent?.summary || summary) ?? null;

  // Why Now state: load from why_now_text or generate on demand
  const [whyNowArtifact, setWhyNowArtifact] = useState<{
    headline: string;
    summary: string;
    signals: { type: string; explanation: string }[];
    confidence: string;
    limitations: string[];
  } | null>(null);

  const whyNowFromPatent = patent?.why_now_text
    ? {
        headline: patent.why_now_text,
        summary: "",
        signals: [],
        confidence: "medium",
        limitations: [],
      }
    : null;

  const effectiveWhyNow = whyNowArtifact ?? whyNowFromPatent;
  const [whyNowLoading, setWhyNowLoading] = useState(false);

  const handleGenerateWhyNow = async () => {
    setWhyNowLoading(true);
    try {
      const data = await patentsApi.generateWhyNow(id);
      setWhyNowArtifact(data);
    } finally {
      setWhyNowLoading(false);
    }
  };

  // Opportunity Narrative state
  const [oppNarrativeArtifact, setOppNarrativeArtifact] = useState<{
    opportunity_type: string;
    plain_english_opportunity: string;
    possible_products: string[];
    target_customers: string[];
    implementation_difficulty: string;
    commercial_timing: string;
    risks: string[];
  } | null>(null);
  const [oppNarrativeLoading, setOppNarrativeLoading] = useState(false);

  const handleGenerateOppNarrative = async () => {
    setOppNarrativeLoading(true);
    try {
      const data = await patentsApi.generateOpportunityNarrative(id);
      setOppNarrativeArtifact(data);
    } finally {
      setOppNarrativeLoading(false);
    }
  };

  // Trend Snapshot state
  const [trendArtifact, setTrendArtifact] = useState<{
    trend_score: number;
    components: Record<string, { sub_score: number; weight: number; contribution: number }>;
  } | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);

  const handleGenerateTrend = async () => {
    setTrendLoading(true);
    try {
      const data = await patentsApi.generateTrendSnapshot(id);
      setTrendArtifact(data);
    } finally {
      setTrendLoading(false);
    }
  };

  // Assignee Intelligence state
  const [assigneeArtifact, setAssigneeArtifact] = useState<{
    assignee_intelligence_score: number;
    components: Record<string, { sub_score: number; weight: number; contribution: number }>;
  } | null>(null);
  const [assigneeLoading, setAssigneeLoading] = useState(false);

  const handleGenerateAssignee = async () => {
    setAssigneeLoading(true);
    try {
      const data = await patentsApi.generateAssigneeIntelligence(id);
      setAssigneeArtifact(data);
    } finally {
      setAssigneeLoading(false);
    }
  };

  const { data: watchlistStatus, mutate: mutateWatchlist } = useWatchlistCheck(patent ? id : null);
  const [watchlistLoading, setWatchlistLoading] = useState(false);

  const handleToggleWatchlist = async () => {
    if (!patent) return;
    setWatchlistLoading(true);
    try {
      if (watchlistStatus?.in_watchlist && watchlistStatus.watchlist_item_id) {
        await removeFromWatchlist(watchlistStatus.watchlist_item_id, id);
      } else {
        await addToWatchlist(id);
      }
      mutateWatchlist();
    } finally {
      setWatchlistLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-64 mb-4" />
        <Skeleton className="h-6 w-96 mb-8" />
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
          <div>
            <Skeleton className="h-48 w-full rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (!patent) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Patent not found</p>
        <Link href="/patents" className="text-primary-600 mt-2 inline-block">
          Back to patents
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          href="/patents"
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-flex items-center gap-1"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to patents
        </Link>

        <div className="flex items-start justify-between gap-4 mt-2">
          <h1 className="text-2xl font-bold text-gray-900">
            {patent.title || "Untitled Patent"}
          </h1>
          <div className="flex items-start gap-3">
            <button
              onClick={handleToggleWatchlist}
              disabled={watchlistLoading}
              className={`p-2 rounded-lg border transition-colors ${
                watchlistStatus?.in_watchlist
                  ? "bg-primary-50 border-primary-300 text-primary-700"
                  : "border-gray-300 text-gray-400 hover:text-primary-600 hover:border-primary-300"
              } disabled:opacity-50`}
              title={watchlistStatus?.in_watchlist ? "Remove from watchlist" : "Save to watchlist"}
            >
              <svg className="w-5 h-5" fill={watchlistStatus?.in_watchlist ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </button>
            <div className="flex flex-col items-end gap-1.5">
              <OpportunityScoreBadge score={patent.opportunity_score} size="md" />
              <ScoreBadge score={patent.interesting_score} />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500">
          <span>{patent.publication_number}</span>
          <span>•</span>
          <span>{patent.office}</span>
          <span>•</span>
          <Badge
            variant={patent.legal_status === "GRANTED" ? "success" : "default"}
          >
            {patent.legal_status}
          </Badge>
          <LegalConfidenceBadge
            confidence={patent.legal_status_confidence}
            legalStatus={patent.legal_status}
          />
        </div>
        {patent.tags?.risk_flags && patent.tags.risk_flags.length > 0 && (
          <div className="mt-2">
            <RiskFlagsBadge flags={patent.tags.risk_flags} />
          </div>
        )}
        <div className="mt-3">
          <ExternalPatentLinks
            publicationNumber={patent.publication_number}
            office={patent.office}
            docId={patent.doc_id}
          />
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <AISummaryPanel
            summary={displaySummary}
            isLoading={summaryLoading && !patent.summarized_at}
          />

          <WhyNowPanel
            patent={patent}
            artifact={effectiveWhyNow}
            isLoading={whyNowLoading}
            onGenerate={handleGenerateWhyNow}
          />

          <OpportunityNarrativePanel
            patent={patent}
            artifact={oppNarrativeArtifact}
            isLoading={oppNarrativeLoading}
            onGenerate={handleGenerateOppNarrative}
          />

          <TrendSnapshotPanel
            patent={patent}
            artifact={trendArtifact}
            isLoading={trendLoading}
            onGenerate={handleGenerateTrend}
          />

          <AssigneeIntelligencePanel
            patent={patent}
            artifact={assigneeArtifact}
            isLoading={assigneeLoading}
            onGenerate={handleGenerateAssignee}
          />

          {patent.tags && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Tags</h2>
              <TagsPanel tags={patent.tags} variant="full" />
            </div>
          )}

          {patent.abstract && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Abstract</h2>
              <p className="text-gray-700 leading-relaxed">{patent.abstract}</p>
            </div>
          )}

          <ClaimsPanel claimsText={patent.claims_text} />
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Details</h2>

            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Application Number</dt>
                <dd className="font-medium">
                  {patent.application_number || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Filing Date</dt>
                <dd className="font-medium">{formatDate(patent.filing_date)}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Publication Date</dt>
                <dd className="font-medium">
                  {formatDate(patent.publication_date)}
                </dd>
              </div>
              {patent.grant_date && (
                <div>
                  <dt className="text-gray-500">Grant Date</dt>
                  <dd className="font-medium">
                    {formatDate(patent.grant_date)}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-gray-500">Estimated Expiry</dt>
                <dd className="font-medium">
                  {formatDate(patent.estimated_expiry_date)}
                </dd>
              </div>
            </dl>
          </div>

          {patent.assignees.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Assignees</h2>
              <ul className="space-y-1">
                {patent.assignees.map((assignee, i) => (
                  <li key={i} className="text-sm text-gray-700">
                    {assignee}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {patent.inventors.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Inventors</h2>
              <ul className="space-y-1">
                {patent.inventors.map((inventor, i) => (
                  <li key={i} className="text-sm text-gray-700">
                    {inventor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {patent.cpc.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">
                Classifications (CPC)
              </h2>
              <div className="flex flex-wrap gap-2">
                {patent.cpc.map((code, i) => (
                  <Badge key={i} variant="default" size="sm">
                    {code}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {patent.opportunity_breakdown && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <OpportunityBreakdown breakdown={patent.opportunity_breakdown} />
            </div>
          )}

          {patent.score_breakdown && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">
                Interesting Score Breakdown
              </h2>
              <dl className="space-y-2 text-sm">
                {Object.entries(patent.score_breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <dt className="text-gray-500 capitalize">
                      {key.replace(/_/g, " ")}
                    </dt>
                    <dd className="font-medium">
                      {Math.round(value * 100)}%
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
