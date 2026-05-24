"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { ApiError, usageSignalsApi } from "@/lib/api";
import type {
  UsageSignalResponse,
  UsageEvidenceItem,
  UsageNarrativeResponse,
} from "@/lib/types";

// ── helpers ──────────────────────────────────────────────────────────

const TIER_COLORS: Record<string, string> = {
  strong: "bg-green-100 text-green-800 border-green-300",
  medium: "bg-amber-100 text-amber-800 border-amber-300",
  weak: "bg-gray-100 text-gray-600 border-gray-300",
};

function scoreColor(score: number): string {
  if (score >= 70) return "bg-green-100 text-green-800 border-green-400";
  if (score >= 40) return "bg-amber-100 text-amber-800 border-amber-400";
  return "bg-gray-100 text-gray-600 border-gray-300";
}

function scoreLabel(score: number): string {
  if (score >= 70) return "High";
  if (score >= 40) return "Medium";
  if (score > 0) return "Low";
  return "Insufficient evidence";
}

// ── evidence item ────────────────────────────────────────────────────

function EvidenceRow({ item }: { item: UsageEvidenceItem }) {
  const [expanded, setExpanded] = useState(false);
  const tierColor = TIER_COLORS[item.evidence_tier] || TIER_COLORS.weak;

  return (
    <div className="border border-gray-100 rounded p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-gray-900 truncate font-medium">
            {item.source_patent_title || "Untitled patent"}
          </p>
          <p className="text-gray-500 text-xs">
            {item.source_patent_assignee || "Unknown assignee"}
            {item.source_patent_filing_date &&
              ` · ${item.source_patent_filing_date.slice(0, 4)}`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {item.similarity_score != null && (
            <span className="text-xs text-gray-400">
              {(item.similarity_score * 100).toFixed(0)}%
            </span>
          )}
          <span
            className={`text-xs px-2 py-0.5 rounded-full border ${tierColor}`}
          >
            {item.evidence_tier}
          </span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-600 hover:underline"
          >
            {expanded ? "less" : "more"}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="mt-2 text-xs text-gray-500 space-y-1">
          {item.matched_cpc.length > 0 && (
            <p>
              Shared CPC:{" "}
              {item.matched_cpc.map((c) => (
                <code key={c} className="bg-gray-100 px-1 rounded text-xs mr-1">
                  {c}
                </code>
              ))}
            </p>
          )}
          {item.cpc_overlap_count > 0 && (
            <p>CPC overlap: {item.cpc_overlap_count} codes</p>
          )}
          <p>Source: {item.source_type.replace(/_/g, " ")}</p>
        </div>
      )}
    </div>
  );
}

// ── narrative section ────────────────────────────────────────────────

function NarrativeSection({
  patentId,
  score,
  hasCachedNarrativeRow,
}: {
  patentId: string;
  score: number;
  hasCachedNarrativeRow: boolean;
}) {
  const [generating, setGenerating] = useState(false);
  const [narrative, setNarrative] = useState<UsageNarrativeResponse | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  const callNarrativeApi = async () => {
    setGenerating(true);
    setError(null);
    try {
      const result = await usageSignalsApi.narrative(patentId);
      setNarrative(result);
    } catch (_e) {
      setError("Narrative generation failed. Try again.");
    } finally {
      setGenerating(false);
    }
  };

  // Auto-load the full cached narrative when a row exists. The backend's
  // POST /narrative is idempotent on cache hit — it returns the cached
  // artifact (cached=true) without regenerating.
  useEffect(() => {
    if (hasCachedNarrativeRow && !narrative && !generating && score >= 40) {
      void callNarrativeApi();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasCachedNarrativeRow, patentId]);

  const handleGenerate = async () => {
    if (score < 40) return;
    await callNarrativeApi();
  };

  const stale = narrative?.stale;

  if (score < 40) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200 text-sm text-gray-500">
        Not enough evidence for narrative generation (score {score.toFixed(0)}
        /100). At least 40 points of evidence are needed.
      </div>
    );
  }

  return (
    <div className="mt-4">
      {!narrative ? (
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {generating
            ? hasCachedNarrativeRow
              ? "Loading cached analysis…"
              : "Generating…"
            : "Analyze Usage Signals"}
        </button>
      ) : (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-gray-700 mb-2 leading-relaxed">
            {narrative.summary}
          </p>
          {narrative.evidence_summary && (
            <p className="text-xs text-gray-500 mb-2">
              {narrative.evidence_summary}
            </p>
          )}
          {narrative.limitations.length > 0 && (
            <div className="mt-2 space-y-1">
              {narrative.limitations.map((lim, i) => (
                <p key={i} className="text-xs text-amber-700 flex gap-1">
                  <span>⚠</span> {lim}
                </p>
              ))}
            </div>
          )}
          {stale && (
            <p className="text-xs text-amber-600 mt-2">
              Evidence has been updated since this narrative was generated.
              Regenerate for latest analysis.
            </p>
          )}
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-gray-400">
              AI-generated analysis{narrative.cached ? " (cached)" : ""}
            </span>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="text-xs text-blue-600 hover:underline"
            >
              {generating ? "Regenerating…" : "Regenerate"}
            </button>
          </div>
        </div>
      )}
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </div>
  );
}

// ── main panel ───────────────────────────────────────────────────────

export function UsageSignalsPanel({ patentId }: { patentId: string }) {
  const { data, isLoading, error, mutate } = useSWR(
    `usage-signals-${patentId}`,
    () => usageSignalsApi.get(patentId),
    { revalidateOnFocus: false }
  );

  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-32" />
        <div className="h-4 bg-gray-200 rounded w-64" />
        <div className="h-24 bg-gray-200 rounded" />
      </div>
    );
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="text-center py-12 text-gray-500 space-y-2">
        <p className="font-medium">Usage signals not yet assessed</p>
        <p className="text-sm max-w-md mx-auto">
          This patent has not been processed for usage signal analysis yet.
          Once an embedding is generated and assessment runs, evidence-based
          signals will appear here.
        </p>
        <p className="text-xs text-gray-400 mt-4">
          Evidence is patent-based only — no product-level verification has
          been performed. Verify independently before making business or legal
          decisions.
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Unable to load usage signals.</p>
        <button
          onClick={() => mutate()}
          className="text-sm text-blue-600 hover:underline mt-2"
        >
          Retry
        </button>
      </div>
    );
  }

  const signal: UsageSignalResponse = data;
  const hasEvidence = signal.evidence_count > 0;
  const hasCachedNarrativeRow = Boolean(signal.narrative_summary);

  return (
    <div className="space-y-4">
      {/* ── header ── */}
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${scoreColor(
            signal.score
          )}`}
        >
          {signal.score.toFixed(0)} / 100 · {scoreLabel(signal.score)}
        </span>
        {signal.confidence === "high" && (
          <span className="text-xs text-green-700">High confidence</span>
        )}
      </div>

      {/* ── evidence summary ── */}
      {hasEvidence && (
        <div className="flex flex-wrap gap-2 text-xs text-gray-500">
          <span>{signal.evidence_count} evidence pieces</span>
          {signal.strong_count > 0 && (
            <span className="text-green-700">
              {signal.strong_count} strong
            </span>
          )}
          {signal.medium_count > 0 && (
            <span className="text-amber-700">
              {signal.medium_count} medium
            </span>
          )}
          {signal.weak_count > 0 && (
            <span className="text-gray-500">
              {signal.weak_count} weak
            </span>
          )}
          {signal.has_self_citation_risk && (
            <span className="text-amber-600 font-medium">
              ⚠ Self-citation risk
            </span>
          )}
        </div>
      )}

      {/* ── evidence list ── */}
      {hasEvidence && signal.evidence.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">Evidence</h3>
          {signal.evidence.map((item) => (
            <EvidenceRow key={item.id} item={item} />
          ))}
        </div>
      )}

      {/* ── narrative ── */}
      {hasEvidence && (
        <NarrativeSection
          patentId={patentId}
          score={signal.score}
          hasCachedNarrativeRow={hasCachedNarrativeRow}
        />
      )}

      {/* ── empty state ── */}
      {!hasEvidence && (
        <div className="text-center py-8 text-gray-500 space-y-2">
          <p className="font-medium">No Usage Signals Detected</p>
          <p className="text-sm max-w-md mx-auto">
            Based on similar newer patents only (citation analysis pending).
            No similar patents met the significance threshold. This does
            not mean the technology is unused — evidence is patent-based
            only. Product-level usage is not tracked.
          </p>
          <p className="text-xs text-gray-400 mt-4">
            Evidence is patent-based only — no product-level verification
            has been performed. Verify independently before making business
            or legal decisions.
          </p>
        </div>
      )}

      {/* ── disclaimer ── */}
      {hasEvidence && (
        <div className="mt-4 text-xs text-gray-400 border-t pt-3 space-y-1">
          <p>
            Evidence is patent-based only — no product-level verification
            has been performed.
          </p>
          <p>
            These signals are evidence-backed hypotheses, not confirmation
            of commercial use. Verify independently before making business
            or legal decisions.
          </p>
        </div>
      )}
    </div>
  );
}
