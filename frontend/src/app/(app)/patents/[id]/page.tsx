"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { BRAND } from "@/lib/brand";
import { usePatent, usePatentSummary } from "@/hooks/usePatents";
import { AISummaryPanel } from "@/components/patents/AISummaryPanel";
import { ScoreBadge } from "@/components/patents/ScoreBadge";
import { OpportunityScoreBadge } from "@/components/patents/OpportunityScoreBadge";
import { OpportunityBreakdown } from "@/components/patents/OpportunityBreakdown";
import { TagsPanel } from "@/components/patents/TagsPanel";
import { LegalConfidenceBadge } from "@/components/patents/LegalConfidenceBadge";
import { RiskFlagsBadge } from "@/components/patents/RiskFlagsBadge";
import { WhyNowPanel } from "@/components/patents/WhyNowPanel";
import { LinkedInPostPanel } from "@/components/patents/LinkedInPostPanel";
import { UsageSignalsPanel } from "@/components/patents/UsageSignalsPanel";
import { OpportunityNarrativePanel } from "@/components/patents/OpportunityNarrativePanel";
import { TrendSnapshotPanel } from "@/components/patents/TrendSnapshotPanel";
import { AssigneeIntelligencePanel } from "@/components/patents/AssigneeIntelligencePanel";
import { ClaimsPanel } from "@/components/patents/ClaimsPanel";
import { ExternalPatentLinks } from "@/components/patents/ExternalPatentLinks";
import { PatentFiguresPanel } from "@/components/patents/PatentFiguresPanel";
import { PatentDetailTabs } from "@/components/patents/PatentDetailTabs";
import { Badge } from "@/components/ui/Badge";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { Skeleton } from "@/components/ui/Skeleton";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { formatDate } from "@/lib/utils";
import { patentsApi, semanticApi } from "@/lib/api";
import { useWatchlistCheck, addToWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import type { PatentDetail, Summary, SimilarPatentsResponse } from "@/lib/types";

// ---------------------------------------------------------------------------
// Data Completeness Panel — shows which fields are available for this patent
// ---------------------------------------------------------------------------
type FieldStatus = "available" | "unavailable";

interface DataField {
  label: string;
  category: string;
  status: FieldStatus;
}

function DataCompletenessPanel({ patent }: { patent: PatentDetail }) {
  const [expanded, setExpanded] = useState(false);

  const fields: DataField[] = [
    { label: "Title", category: "Core", status: patent.title ? "available" : "unavailable" },
    { label: "Inventors", category: "Core", status: patent.inventors?.length > 0 ? "available" : "unavailable" },
    { label: "Full abstract", category: "Content", status: patent.abstract ? "available" : "unavailable" },
    { label: "Claims text", category: "Content", status: patent.claims_text ? "available" : "unavailable" },
    { label: "AI summary", category: "Intelligence", status: patent.summary ? "available" : "unavailable" },
    { label: "AI tags", category: "Intelligence", status: patent.tags ? "available" : "unavailable" },
    { label: "Opportunity score", category: "Intelligence", status: patent.opportunity_score != null ? "available" : "unavailable" },
    { label: "Why-now narrative", category: "Intelligence", status: patent.why_now_text ? "available" : "unavailable" },
    { label: "Expiry estimate", category: "Legal", status: patent.estimated_expiry_date ? "available" : "unavailable" },
    { label: "Family members", category: "Legal", status: patent.family_members?.length > 0 ? "available" : "unavailable" },
    { label: "Backward citations", category: "Legal", status: patent.citations_backward?.length > 0 ? "available" : "unavailable" },
    { label: "Forward citations", category: "Legal", status: patent.citations_forward?.length > 0 ? "available" : "unavailable" },
    { label: "Patent figures", category: "Visual", status: patent.figure_page_url ? "available" : "unavailable" },
  ];

  const availableCount = fields.filter((f) => f.status === "available").length;
  const categories = [...new Set(fields.map((f) => f.category))];

  return (
    <div className="mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-4 py-2.5 text-left hover:bg-[var(--bg-elevated)] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-[var(--text-secondary)]">Data completeness</span>
          <span className="text-xs text-[var(--text-muted)]">
            {availableCount}/{fields.length} fields available
          </span>
          <div className="hidden sm:flex items-center gap-1">
            {categories.map((cat) => {
              const catFields = fields.filter((f) => f.category === cat);
              const catAvailable = catFields.filter((f) => f.status === "available").length;
              const allAvailable = catAvailable === catFields.length;
              const noneAvailable = catAvailable === 0;
              return (
                <span
                  key={cat}
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    allAvailable
                      ? "bg-[var(--score-high-bg)] text-[var(--score-high)]"
                      : noneAvailable
                      ? "bg-[var(--score-medium-bg)] text-[var(--expiry-lapsed-confirmed)]"
                      : "bg-[var(--score-medium-bg)] text-[var(--score-medium)]"
                  }`}
                >
                  {cat} {catAvailable}/{catFields.length}
                </span>
              );
            })}
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-[var(--text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="mt-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            {categories.map((cat) => (
              <div key={cat}>
                <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-1.5">
                  {cat}
                </h4>
                <div className="space-y-1">
                  {fields
                    .filter((f) => f.category === cat)
                    .map((f) => (
                      <div key={f.label} className="flex items-center gap-2 text-xs">
                        <span className={f.status === "available" ? "text-[var(--score-high)]" : "text-[var(--text-muted)]"}>
                          {f.status === "available" ? "●" : "○"}
                        </span>
                        <span className={f.status === "available" ? "text-[var(--text-secondary)]" : "text-[var(--text-muted)]"}>
                          {f.label}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-3 pt-3 border-t border-[var(--border-subtle)]">
            Data completeness reflects what {BRAND.name} has ingested from patent office sources.
            Missing fields may be available from the patent office directly.
            {!patent.abstract && " Abstracts populate gradually via scheduled enrichment."}
            {!patent.claims_text && " Claims ingestion is limited in the current data pipeline."}
          </p>
        </div>
      )}
    </div>
  );
}

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
        <p className="text-[var(--text-muted)]">Patent not found</p>
        <Link href="/patents" className="text-[var(--accent)] mt-2 inline-block">Back to patents</Link>
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
    { id: "usage", label: "Usage Signals" },
  ];

  return (
    <div>
      {/* --- Header (always visible) --- */}
      <div className="mb-6">
        <Link href="/patents" className="text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] mb-2 inline-flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to patents
        </Link>

        <div className="flex items-start justify-between gap-4 mt-2">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{patent.title || "Untitled Patent"}</h1>
          <div className="flex items-start gap-3">
            <Link
              href={`/chat?seed=${encodeURIComponent("Tell me about " + patent.title + " (" + patent.doc_id + ").")}`}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[var(--border-subtle)] text-sm text-[var(--accent)] hover:bg-[var(--accent-muted)] transition-colors"
              title="Ask AI about this patent"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              Ask AI
            </Link>
            <button
              onClick={handleToggleWatchlist}
              disabled={watchlistLoading}
              className={`p-2 rounded-lg border transition-colors ${
                watchlistStatus?.in_watchlist
                  ? "bg-[var(--bg-elevated)] border-border-[var(--accent)]/30 text-[var(--accent)]"
                  : "border-[var(--border-default)] text-[var(--text-muted)] hover:text-[var(--accent)] hover:border-border-[var(--accent)]/30"
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

        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-[var(--text-muted)]">
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
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {/* Citation counts — clickable, jumps to Citations tab */}
          {((patent.citations_backward?.length ?? 0) > 0 || (patent.citations_forward?.length ?? 0) > 0) ? (
            <button
              onClick={() => setActiveTab("citations")}
              className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors"
            >
              <span>Citations:</span>
              <span className="font-medium">{patent.citations_backward?.length ?? 0} ←</span>
              <span className="font-medium">{patent.citations_forward?.length ?? 0} →</span>
            </button>
          ) : (
            <span className="text-xs text-[var(--text-muted)]">Citations: none</span>
          )}
        </div>
        <div className="mt-3">
          <ExternalPatentLinks publicationNumber={patent.publication_number} office={patent.office} docId={patent.doc_id} />
          <SourceAttribution office={patent.office} />

          {/* Figures — thumbnail via Google Patents og:image (backend-resolved + Redis-cached).
              Brand rule "link-only, never host or re-serve" explicitly overridden 2026-06-02 per Andy.
              We extract Google's CDN URL and embed <img> directly; bytes are NOT proxied through us.
              Falls back to link-card if the scrape fails or the patent has no og:image. */}
          {patent.figure_page_url && (
            <PatentFiguresPanel
              publicationNumber={patent.publication_number}
              figurePageUrl={patent.figure_page_url}
            />
          )}
        </div>
      </div>

      {/* Data Completeness Panel */}
      <DataCompletenessPanel patent={patent} />

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
      {activeTab === "usage" && (
        <UsageSignalsPanel patentId={patent.id} />
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
        {/* Sprint 3: Inventors moved to prominent main-column position */}
        {patent.inventors.length > 0 && (
          <InventorsPanel inventors={patent.inventors} />
        )}

        <AISummaryPanel summary={displaySummary} isLoading={summaryLoading && !patent.summarized_at} />

        {patent.tags && (
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">Tags</h2>
            <TagsPanel tags={patent.tags} variant="full" />
          </div>
        )}

        {patent.abstract && (
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">Abstract</h2>
            <p className="text-[var(--text-secondary)] leading-relaxed">{patent.abstract}</p>
          </div>
        )}
      </div>

      <div className="space-y-6">
        <DetailsPanel patent={patent} />

        {patent.assignees.length > 0 && (
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">Assignees</h2>
            <ul className="space-y-1">
              {patent.assignees.map((assignee, i) => (
                <li key={i}>
                  <Link
                    href={`/companies/${encodeURIComponent(assignee)}`}
                    className="text-sm text-[var(--accent)] hover:text-text-[var(--accent-hover)] hover:underline"
                  >
                    {assignee}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {patent.cpc.length > 0 && (
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">Classifications (CPC)</h2>
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
        <LinkedInPostPanel patentId={patent.id} />
        <WhyNowPanel patent={patent} artifact={effectiveWhyNow} isLoading={whyNowLoading} onGenerate={handleGenerateWhyNow} />
        <OpportunityNarrativePanel patent={patent} artifact={oppNarrativeArtifact} isLoading={oppNarrativeLoading} onGenerate={handleGenerateOppNarrative} />
        <TrendSnapshotPanel patent={patent} artifact={trendArtifact} isLoading={trendLoading} onGenerate={handleGenerateTrend} />
        <AssigneeIntelligencePanel patent={patent} artifact={assigneeArtifact} isLoading={assigneeLoading} onGenerate={handleGenerateAssignee} />
      </div>

      <div className="space-y-6">
        {patent.opportunity_breakdown && (
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <OpportunityBreakdown breakdown={patent.opportunity_breakdown} />
          </div>
        )}

        {patent.score_breakdown && (
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-3">Interest Score Breakdown</h2>
            <dl className="space-y-2 text-sm">
              {Object.entries(patent.score_breakdown).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <dt className="text-[var(--text-muted)] capitalize">{key.replace(/_/g, " ")}</dt>
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
      <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-8 text-center">
        <p className="text-[var(--text-muted)]">No family members found for this patent.</p>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          Family data depends on INPADOC resolution, which may not cover all
          patents. Absence of family data does not mean no related patents exist —
          verify with official registers.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <h2 className="font-semibold text-[var(--text-primary)] mb-1">
        Patent Family ({patent.family_members.length} members)
      </h2>
      <p className="text-xs text-[var(--text-muted)] mb-4">
        This patent is part of a family of related filings across jurisdictions.
        Active family members in other jurisdictions may still be enforceable.
      </p>

      {/* Family awareness — generic disclaimer, applies to any patent family */}
      <div className="mb-4 p-3 bg-[var(--score-medium-bg)] border border-[var(--score-medium)]/30 rounded text-sm text-[var(--score-medium)]">
        <strong>Family awareness:</strong> A patent&apos;s family may have
        active members in other jurisdictions. Expired or expiring status in
        one jurisdiction does not imply global freedom to operate — verify
        each jurisdiction independently.
      </div>

      <div className="space-y-1.5">
        {patent.family_members.map((member, i) => {
          const juris = parseJurisdiction(member);
          const isSelf = member === patent.publication_number;

          return (
            <div
              key={i}
              className="flex items-center gap-3 py-2 px-3 bg-[var(--bg-base)] rounded text-sm"
            >
              <span
                className={`flex-shrink-0 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                  juris.color
                }`}
                title={juris.label}
              >
                {juris.code}
              </span>
              <span className="text-[var(--text-secondary)] font-mono text-xs flex-1 truncate">
                {member}
              </span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  isSelf
                    ? "bg-[var(--bg-elevated)] text-[var(--accent)] font-medium"
                    : "text-[var(--text-muted)]"
                }`}
              >
                {isSelf ? "This patent" : "Unknown"}
              </span>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-[var(--text-muted)] mt-4">
        Per-member legal status is not currently available. Active family risk
        is assessed at the patent level; individual member status requires
        verification with each issuing patent office.
      </p>
    </div>
  );
}

// ── Jurisdiction parser ──────────────────────────────────────────────

const JURISDICTION_MAP: Record<string, { code: string; label: string; color: string }> = {
  US: { code: "US", label: "United States",          color: "bg-[var(--accent-muted)] text-[var(--accent)]" },
  EP: { code: "EP", label: "European Patent Office", color: "bg-[var(--accent-muted)] text-[var(--accent)]" },
  WO: { code: "WO", label: "WIPO / PCT",             color: "bg-[var(--score-high-bg)] text-[var(--score-high)]" },
  JP: { code: "JP", label: "Japan",                  color: "bg-[var(--bg-glass-strong)] text-[var(--expiry-lapsed-confirmed)]" },
  CN: { code: "CN", label: "China",                  color: "bg-[var(--bg-glass-strong)] text-[var(--expiry-lapsed-possible)]" },
  KR: { code: "KR", label: "South Korea",            color: "bg-[var(--bg-glass-strong)] text-[var(--type-foryou)]" },
  GB: { code: "GB", label: "United Kingdom",         color: "bg-[var(--accent-muted)] text-[var(--accent)]" },
  DE: { code: "DE", label: "Germany",                color: "bg-[var(--score-medium-bg)] text-[var(--score-medium)]" },
  FR: { code: "FR", label: "France",                 color: "bg-[var(--accent-muted)] text-[var(--type-foryou)]" },
  CA: { code: "CA", label: "Canada",                 color: "bg-[var(--bg-glass-strong)] text-[var(--expiry-lapsed-confirmed)]" },
  AU: { code: "AU", label: "Australia",              color: "bg-[var(--score-high-bg)] text-[var(--score-high)]" },
  IN: { code: "IN", label: "India",                  color: "bg-[var(--score-medium-bg)] text-[var(--score-medium)]" },
};

function parseJurisdiction(pubNumber: string): {
  code: string;
  label: string;
  color: string;
} {
  // Extract leading 2 characters that look like a country/office code.
  const match = pubNumber.match(/^([A-Z]{2})/);
  if (match && JURISDICTION_MAP[match[1]]) {
    return JURISDICTION_MAP[match[1]];
  }
  const prefix = match ? match[1] : "??";
  return {
    code: prefix,
    label: prefix,
    color: "bg-[var(--bg-elevated)] text-[var(--text-muted)]",
  };
}

function CitationsTab({ patent }: { patent: PatentDetail }) {
  const hasBackward = (patent.citations_backward?.length ?? 0) > 0;
  const hasForward = (patent.citations_forward?.length ?? 0) > 0;

  if (!hasBackward && !hasForward) {
    return (
      <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-8 text-center">
        <p className="text-[var(--text-muted)]">No citation data available for this patent.</p>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          Citation data is sourced from patent filings and may be incomplete.
          Verify with official registers.
        </p>
      </div>
    );
  }

  const CitationLink = ({ pubNumber }: { pubNumber: string }) => (
    <div className="flex items-center justify-between py-2 px-3 bg-[var(--bg-base)] rounded text-sm">
      <span className="text-[var(--text-secondary)] font-medium">{pubNumber}</span>
      <a
        href={`https://patents.google.com/patent/${pubNumber.replace(/[^A-Za-z0-9]/g, "")}`}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-[var(--accent)] hover:text-text-[var(--accent-hover)]"
      >
        View →
      </a>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Backward citations */}
      {hasBackward ? (
        <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
          <h2 className="font-semibold text-[var(--text-primary)] mb-4">
            ← Cited By This Patent ({patent.citations_backward!.length})
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            Patents cited by this application. These represent prior art the
            applicant disclosed.
          </p>
          <div className="space-y-2">
            {patent.citations_backward!.map((citation, i) => (
              <CitationLink key={i} pubNumber={citation} />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-6 text-center">
          <p className="text-[var(--text-muted)] text-sm">No backward citations recorded.</p>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Citation data is sourced from patent filings and may be incomplete.
          </p>
        </div>
      )}

      {/* Forward citations */}
      {hasForward ? (
        <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
          <h2 className="font-semibold text-[var(--text-primary)] mb-4">
            Citing This Patent → ({patent.citations_forward!.length})
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            Patents that cite this one. A high count suggests this invention
            is actively referenced by newer work.
          </p>
          <div className="space-y-2">
            {patent.citations_forward!.map((citation, i) => (
              <CitationLink key={i} pubNumber={citation} />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-6 text-center">
          <p className="text-[var(--text-muted)] text-sm">
            No forward citations recorded yet.
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Patents citing this one may not have been ingested. Forward
            citation data depends on patent office feeds covering newer
            filings. Verify with official registers.
          </p>
        </div>
      )}
    </div>
  );
}

function LegalExpiryTab({ patent }: { patent: PatentDetail }) {
  return (
    <div className="max-w-2xl space-y-6">
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <h2 className="font-semibold text-[var(--text-primary)] mb-4">Legal Status</h2>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-[var(--text-muted)]">Status</dt>
            <dd><Badge variant={patent.legal_status === "GRANTED" ? "success" : "default"}>{patent.legal_status || "Unknown"}</Badge></dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-[var(--text-muted)]">Confidence</dt>
            <dd><LegalConfidenceBadge confidence={patent.legal_status_confidence} legalStatus={patent.legal_status} /></dd>
          </div>
          {patent.maintenance_status && (
            <div className="flex justify-between">
              <dt className="text-[var(--text-muted)]">Maintenance Status</dt>
              <dd className="font-medium">{patent.maintenance_status}</dd>
            </div>
          )}
        </dl>
      </div>

      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <h2 className="font-semibold text-[var(--text-primary)] mb-4">Expiry Information</h2>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-[var(--text-muted)]">Estimated Expiry Date</dt>
            <dd className="font-medium">{formatDate(patent.estimated_expiry_date)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-[var(--text-muted)]">Filing Date</dt>
            <dd className="font-medium">{formatDate(patent.filing_date)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-[var(--text-muted)]">Grant Date</dt>
            <dd className="font-medium">{formatDate(patent.grant_date)}</dd>
          </div>
        </dl>
      </div>

      <div className="bg-[var(--score-medium-bg)] border border-[var(--score-medium)]/30 rounded-lg p-4">
        <p className="text-xs text-[var(--score-medium)]">
          <strong>Important:</strong> Expiry dates are estimates based on filing date + 20 years and
          do not account for maintenance fee status, patent term adjustment (PTA), patent term
          extension (PTE), or terminal disclaimers. Verify with official registers before making
          decisions based on patent expiry.
        </p>
      </div>
    </div>
  );
}

// ── Sprint 3: Inventors panel (prominent, main-column, expandable) ──

function InventorsPanel({ inventors }: { inventors: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const displayInventors = expanded ? inventors : inventors.slice(0, 5);
  const hasMore = inventors.length > 5;

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-[var(--text-primary)]">
          Inventors ({inventors.length})
        </h2>
        {hasMore && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-[var(--accent)] hover:text-text-[var(--accent-hover)] font-medium"
          >
            {expanded ? "Show fewer" : `+${inventors.length - 5} more`}
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {displayInventors.map((inventor, i) => (
          <span
            key={i}
            className="text-sm text-[var(--text-secondary)] bg-[var(--bg-base)] px-3 py-1.5 rounded-full"
          >
            {inventor}
          </span>
        ))}
      </div>
    </div>
  );
}

function DetailsPanel({ patent }: { patent: PatentDetail }) {
  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <h2 className="font-semibold text-[var(--text-primary)] mb-4">Details</h2>
      <dl className="space-y-3 text-sm">
        <div>
          <dt className="text-[var(--text-muted)]">Application Number</dt>
          <dd className="font-medium">{patent.application_number || "—"}</dd>
        </div>
        <div>
          <dt className="text-[var(--text-muted)]">Filing Date</dt>
          <dd className="font-medium">{formatDate(patent.filing_date)}</dd>
        </div>
        <div>
          <dt className="text-[var(--text-muted)]">Publication Date</dt>
          <dd className="font-medium">{formatDate(patent.publication_date)}</dd>
        </div>
        {patent.grant_date && (
          <div>
            <dt className="text-[var(--text-muted)]">Grant Date</dt>
            <dd className="font-medium">{formatDate(patent.grant_date)}</dd>
          </div>
        )}
        <div>
          <dt className="text-[var(--text-muted)]">Estimated Expiry</dt>
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
      <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-8 text-center">
        <p className="text-[var(--text-muted)]">
          {isNoEmbedding
            ? "This patent does not have an embedding yet. Similar patents require embeddings to be generated."
            : "Could not load similar patents."}
        </p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-8 text-center">
        <p className="text-[var(--text-muted)]">No similar patents found above the similarity threshold.</p>
        <p className="text-xs text-[var(--text-muted)] mt-1">Similarity is computed using semantic embeddings of patent abstracts and claims.</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <h2 className="font-semibold text-[var(--text-primary)] mb-4">
        Similar Patents ({data.results.length})
      </h2>
      <div className="space-y-3">
        {data.results.map((result) => (
          <Link
            key={result.patent.id}
            href={`/patents/${result.patent.id}`}
            className="block p-4 bg-[var(--bg-base)] rounded-lg hover:bg-[var(--bg-elevated)] transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {result.patent.title || result.patent.doc_id}
                </p>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  {result.patent.doc_id} · {result.patent.assignees?.[0] || "Unknown assignee"}
                </p>
              </div>
              <span className="flex-shrink-0 text-xs font-semibold px-2 py-1 rounded-full bg-[var(--accent-muted)] text-[var(--accent)]">
                {Math.round(result.similarity * 100)}% similar
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
