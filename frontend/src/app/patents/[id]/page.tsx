"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
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
import { PatentDetailTabs } from "@/components/patents/PatentDetailTabs";
import { Badge } from "@/components/ui/Badge";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";
import { patentsApi, semanticApi } from "@/lib/api";
import { useWatchlistCheck, addToWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import type { PatentDetail, Summary, SimilarPatentsResponse } from "@/lib/types";

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

  const [activeTab, setActiveTab] = useState("overview");

  // --- AI generation state ---
  const [whyNowArtifact, setWhyNowArtifact] = useState<{
    headline: string;
    summary: string;
    signals: { type: string; explanation: string }[];
    confidence: string;
    limitations: string[];
  } | null>(null);
  const whyNowFromPatent = patent?.why_now_text
    ? { headline: patent.why_now_text, summary: "", signals: [], confidence: "medium", limitations: [] }
    : null;
  const effectiveWhyNow = whyNowArtifact ?? whyNowFromPatent;
  const [whyNowLoading, setWhyNowLoading] = useState(false);
  const handleGenerateWhyNow = async () => {
    setWhyNowLoading(true);
    try { const data = await patentsApi.generateWhyNow(id); setWhyNowArtifact(data); }
    finally { setWhyNowLoading(false); }
  };

  const [oppNarrativeArtifact, setOppNarrativeArtifact] = useState<{
    opportunity_type: string; plain_english_opportunity: string;
    possible_products: string[]; target_customers: string[];
    implementation_difficulty: string; commercial_timing: string; risks: string[];
  } | null>(null);
  const [oppNarrativeLoading, setOppNarrativeLoading] = useState(false);
  const handleGenerateOppNarrative = async () => {
    setOppNarrativeLoading(true);
    try { const data = await patentsApi.generateOpportunityNarrative(id); setOppNarrativeArtifact(data); }
    finally { setOppNarrativeLoading(false); }
  };

  const [trendArtifact, setTrendArtifact] = useState<{
    trend_score: number;
    components: Record<string, { sub_score: number; weight: number; contribution: number }>;
  } | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const handleGenerateTrend = async () => {
    setTrendLoading(true);
    try { const data = await patentsApi.generateTrendSnapshot(id); setTrendArtifact(data); }
    finally { setTrendLoading(false); }
  };

  const [assigneeArtifact, setAssigneeArtifact] = useState<{
    assignee_intelligence_score: number;
    components: Record<string, { sub_score: number; weight: number; contribution: number }>;
  } | null>(null);
  const [assigneeLoading, setAssigneeLoading] = useState(false);
  const handleGenerateAssignee = async () => {
    setAssigneeLoading(true);
    try { const data = await patentsApi.generateAssigneeIntelligence(id); setAssigneeArtifact(data); }
    finally { setAssigneeLoading(false); }
  };

  // --- Watchlist ---
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

  // --- Loading / Not Found ---
  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-64 mb-4" />
        <Skeleton className="h-6 w-96 mb-8" />
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2"><Skeleton className="h-64 w-full rounded-lg" /></div>
          <div><Skeleton className="h-48 w-full rounded-lg" /></div>
        </div>
      </div>
    );
  }

  if (!patent) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Patent not found</p>
        <Link href="/patents" className="text-primary-600 mt-2 inline-block">Back to patents</Link>
      </div>
    );
  }

  // --- Tab config ---
  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "claims", label: "Claims", count: patent.claims_text ? 1 : 0 },
    { id: "opportunity", label: "Opportunity" },
    { id: "similar", label: "Similar" },
    { id: "family", label: "Family", count: patent.family_members?.length || 0 },
    { id: "citations", label: "Citations", count: patent.citations_backward?.length || 0 },
    { id: "legal", label: "Legal / Expiry" },
  ];

  return (
    <div>
      {/* --- Header (always visible) --- */}
      <div className="mb-6">
        <Link href="/patents" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to patents
        </Link>

        <div className="flex items-start justify-between gap-4 mt-2">
          <h1 className="text-2xl font-bold text-gray-900">{patent.title || "Untitled Patent"}</h1>
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
          <Badge variant={patent.legal_status === "GRANTED" ? "success" : "default"}>{patent.legal_status}</Badge>
          <LegalConfidenceBadge confidence={patent.legal_status_confidence} legalStatus={patent.legal_status} />
        </div>
        {patent.tags?.risk_flags && patent.tags.risk_flags.length > 0 && (
          <div className="mt-2"><RiskFlagsBadge flags={patent.tags.risk_flags} /></div>
        )}
        <div className="mt-3">
          <ExternalPatentLinks publicationNumber={patent.publication_number} office={patent.office} docId={patent.doc_id} />
        </div>
      </div>

      <FreshnessBanner show={["patents", "summaries", "trends", "ai_runs"]} className="mb-4" />

      {/* --- Tabs --- */}
      <PatentDetailTabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* --- Tab content --- */}
      {activeTab === "overview" && (
        <OverviewTab
          patent={patent}
          displaySummary={displaySummary}
          summaryLoading={summaryLoading}
        />
      )}

      {activeTab === "claims" && (
        <ClaimsPanel claimsText={patent.claims_text} />
      )}

      {activeTab === "opportunity" && (
        <OpportunityTab
          patent={patent}
          effectiveWhyNow={effectiveWhyNow}
          whyNowLoading={whyNowLoading}
          handleGenerateWhyNow={handleGenerateWhyNow}
          oppNarrativeArtifact={oppNarrativeArtifact}
          oppNarrativeLoading={oppNarrativeLoading}
          handleGenerateOppNarrative={handleGenerateOppNarrative}
          trendArtifact={trendArtifact}
          trendLoading={trendLoading}
          handleGenerateTrend={handleGenerateTrend}
          assigneeArtifact={assigneeArtifact}
          assigneeLoading={assigneeLoading}
          handleGenerateAssignee={handleGenerateAssignee}
        />
      )}

      {activeTab === "similar" && (
        <SimilarTab patentId={id} />
      )}

      {activeTab === "family" && (
        <FamilyTab patent={patent} />
      )}

      {activeTab === "citations" && (
        <CitationsTab patent={patent} />
      )}

      {activeTab === "legal" && (
        <LegalExpiryTab patent={patent} />
      )}
    </div>
  );
}

// =============================================================================
// TAB COMPONENTS
// =============================================================================

function OverviewTab({
  patent,
  displaySummary,
  summaryLoading,
}: {
  patent: PatentDetail;
  displaySummary: Summary | null;
  summaryLoading: boolean;
}) {
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <AISummaryPanel summary={displaySummary} isLoading={summaryLoading && !patent.summarized_at} />

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
      </div>

      <div className="space-y-6">
        <DetailsPanel patent={patent} />

        {patent.assignees.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Assignees</h2>
            <ul className="space-y-1">
              {patent.assignees.map((assignee, i) => (
                <li key={i}>
                  <Link
                    href={`/companies/${encodeURIComponent(assignee)}`}
                    className="text-sm text-primary-600 hover:text-primary-800 hover:underline"
                  >
                    {assignee}
                  </Link>
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
                <li key={i} className="text-sm text-gray-700">{inventor}</li>
              ))}
            </ul>
          </div>
        )}

        {patent.cpc.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Classifications (CPC)</h2>
            <div className="flex flex-wrap gap-2">
              {patent.cpc.map((code, i) => (
                <Badge key={i} variant="default" size="sm">{code}</Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function OpportunityTab({
  patent,
  effectiveWhyNow,
  whyNowLoading,
  handleGenerateWhyNow,
  oppNarrativeArtifact,
  oppNarrativeLoading,
  handleGenerateOppNarrative,
  trendArtifact,
  trendLoading,
  handleGenerateTrend,
  assigneeArtifact,
  assigneeLoading,
  handleGenerateAssignee,
}: {
  patent: PatentDetail;
  effectiveWhyNow: { headline: string; summary: string; signals: { type: string; explanation: string }[]; confidence: string; limitations: string[] } | null;
  whyNowLoading: boolean;
  handleGenerateWhyNow: () => Promise<void>;
  oppNarrativeArtifact: { opportunity_type: string; plain_english_opportunity: string; possible_products: string[]; target_customers: string[]; implementation_difficulty: string; commercial_timing: string; risks: string[] } | null;
  oppNarrativeLoading: boolean;
  handleGenerateOppNarrative: () => Promise<void>;
  trendArtifact: { trend_score: number; components: Record<string, { sub_score: number; weight: number; contribution: number }> } | null;
  trendLoading: boolean;
  handleGenerateTrend: () => Promise<void>;
  assigneeArtifact: { assignee_intelligence_score: number; components: Record<string, { sub_score: number; weight: number; contribution: number }> } | null;
  assigneeLoading: boolean;
  handleGenerateAssignee: () => Promise<void>;
}) {
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <WhyNowPanel patent={patent} artifact={effectiveWhyNow} isLoading={whyNowLoading} onGenerate={handleGenerateWhyNow} />
        <OpportunityNarrativePanel patent={patent} artifact={oppNarrativeArtifact} isLoading={oppNarrativeLoading} onGenerate={handleGenerateOppNarrative} />
        <TrendSnapshotPanel patent={patent} artifact={trendArtifact} isLoading={trendLoading} onGenerate={handleGenerateTrend} />
        <AssigneeIntelligencePanel patent={patent} artifact={assigneeArtifact} isLoading={assigneeLoading} onGenerate={handleGenerateAssignee} />
      </div>

      <div className="space-y-6">
        {patent.opportunity_breakdown && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <OpportunityBreakdown breakdown={patent.opportunity_breakdown} />
          </div>
        )}

        {patent.score_breakdown && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Interest Score Breakdown</h2>
            <dl className="space-y-2 text-sm">
              {Object.entries(patent.score_breakdown).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <dt className="text-gray-500 capitalize">{key.replace(/_/g, " ")}</dt>
                  <dd className="font-medium">{Math.round(value * 100)}%</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}

function FamilyTab({ patent }: { patent: PatentDetail }) {
  if (!patent.family_members || patent.family_members.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
        <p className="text-gray-500">No family members found for this patent.</p>
        <p className="text-xs text-gray-400 mt-1">Family data depends on INPADOC resolution, which may not cover all patents.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="font-semibold text-gray-900 mb-4">
        Patent Family ({patent.family_members.length} members)
      </h2>
      <div className="space-y-2">
        {patent.family_members.map((member, i) => (
          <div key={i} className="flex items-center gap-3 py-2 px-3 bg-gray-50 rounded text-sm">
            <span className="text-gray-700 font-medium">{member}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-4">
        Family members may include active patents in other jurisdictions. An expired patent with active
        family members may still restrict freedom to operate.
      </p>
    </div>
  );
}

function CitationsTab({ patent }: { patent: PatentDetail }) {
  if (!patent.citations_backward || patent.citations_backward.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
        <p className="text-gray-500">No citation data available for this patent.</p>
        <p className="text-xs text-gray-400 mt-1">Citation data is sourced from patent filings and may be incomplete.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="font-semibold text-gray-900 mb-4">
        Backward Citations ({patent.citations_backward.length})
      </h2>
      <p className="text-sm text-gray-600 mb-4">
        Patents cited by this application. These represent prior art the applicant disclosed.
      </p>
      <div className="space-y-2">
        {patent.citations_backward.map((citation, i) => (
          <div key={i} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded text-sm">
            <span className="text-gray-700 font-medium">{citation}</span>
            <a
              href={`https://patents.google.com/patent/${citation.replace(/[^A-Za-z0-9]/g, "")}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary-600 hover:text-primary-800"
            >
              View →
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

function LegalExpiryTab({ patent }: { patent: PatentDetail }) {
  return (
    <div className="max-w-2xl space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Legal Status</h2>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Status</dt>
            <dd><Badge variant={patent.legal_status === "GRANTED" ? "success" : "default"}>{patent.legal_status || "Unknown"}</Badge></dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Confidence</dt>
            <dd><LegalConfidenceBadge confidence={patent.legal_status_confidence} legalStatus={patent.legal_status} /></dd>
          </div>
          {patent.maintenance_status && (
            <div className="flex justify-between">
              <dt className="text-gray-500">Maintenance Status</dt>
              <dd className="font-medium">{patent.maintenance_status}</dd>
            </div>
          )}
        </dl>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Expiry Information</h2>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Estimated Expiry Date</dt>
            <dd className="font-medium">{formatDate(patent.estimated_expiry_date)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Filing Date</dt>
            <dd className="font-medium">{formatDate(patent.filing_date)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Grant Date</dt>
            <dd className="font-medium">{formatDate(patent.grant_date)}</dd>
          </div>
        </dl>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p className="text-xs text-amber-800">
          <strong>Important:</strong> Expiry dates are estimates based on filing date + 20 years and
          do not account for maintenance fee status, patent term adjustment (PTA), patent term
          extension (PTE), or terminal disclaimers. Verify with official registers before making
          decisions based on patent expiry.
        </p>
      </div>
    </div>
  );
}

function DetailsPanel({ patent }: { patent: PatentDetail }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="font-semibold text-gray-900 mb-4">Details</h2>
      <dl className="space-y-3 text-sm">
        <div>
          <dt className="text-gray-500">Application Number</dt>
          <dd className="font-medium">{patent.application_number || "—"}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Filing Date</dt>
          <dd className="font-medium">{formatDate(patent.filing_date)}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Publication Date</dt>
          <dd className="font-medium">{formatDate(patent.publication_date)}</dd>
        </div>
        {patent.grant_date && (
          <div>
            <dt className="text-gray-500">Grant Date</dt>
            <dd className="font-medium">{formatDate(patent.grant_date)}</dd>
          </div>
        )}
        <div>
          <dt className="text-gray-500">Estimated Expiry</dt>
          <dd className="font-medium">{formatDate(patent.estimated_expiry_date)}</dd>
        </div>
      </dl>
    </div>
  );
}

function SimilarTab({ patentId }: { patentId: string }) {
  const { data, isLoading, error } = useSWR<SimilarPatentsResponse>(
    ["similar", patentId],
    () => semanticApi.similar(patentId),
    { revalidateOnFocus: false }
  );

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    const isNoEmbedding = String(error?.message || "").includes("no embedding");
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
        <p className="text-gray-500">
          {isNoEmbedding
            ? "This patent does not have an embedding yet. Similar patents require embeddings to be generated."
            : "Could not load similar patents."}
        </p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
        <p className="text-gray-500">No similar patents found above the similarity threshold.</p>
        <p className="text-xs text-gray-400 mt-1">Similarity is computed using semantic embeddings of patent abstracts and claims.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="font-semibold text-gray-900 mb-4">
        Similar Patents ({data.results.length})
      </h2>
      <div className="space-y-3">
        {data.results.map((result) => (
          <Link
            key={result.patent.id}
            href={`/patents/${result.patent.id}`}
            className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {result.patent.title || result.patent.doc_id}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {result.patent.doc_id} · {result.patent.assignees?.[0] || "Unknown assignee"}
                </p>
              </div>
              <span className="flex-shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-primary-100 text-primary-700">
                {Math.round(result.similarity * 100)}% similar
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
