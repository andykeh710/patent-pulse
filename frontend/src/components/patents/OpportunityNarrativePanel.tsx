"use client";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { AISourceFooter } from "@/components/patents/AISourceFooter";
import type { PatentDetail } from "@/lib/types";

interface OpportunityNarrativeArtifact {
  opportunity_type: string;
  plain_english_opportunity: string;
  possible_products: string[];
  target_customers: string[];
  implementation_difficulty: string;
  commercial_timing: string;
  risks: string[];
}

interface OpportunityNarrativePanelProps {
  patent: PatentDetail;
  artifact: OpportunityNarrativeArtifact | null;
  isLoading: boolean;
  onGenerate: () => Promise<void>;
}

const typeLabels: Record<string, string> = {
  startup_idea: "Startup Idea",
  enterprise_tooling: "Enterprise Tooling",
  licensing: "Licensing Opportunity",
  research_signal: "Research Signal",
  defensive_monitoring: "Defensive Monitoring",
  revival_candidate: "Revival Candidate",
  cross_industry_transfer: "Cross-Industry Transfer",
};

const difficultyColors: Record<string, string> = {
  low: "bg-[var(--score-high-bg)] text-[var(--score-high)]",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
  unknown: "bg-[var(--bg-elevated)] text-[var(--text-secondary)]",
};

const timingColors: Record<string, string> = {
  now: "bg-[var(--score-high-bg)] text-[var(--score-high)]",
  near_term: "bg-[var(--accent-muted)] text-[var(--accent)]",
  long_term: "bg-[var(--accent-muted)] text-[var(--type-foryou)]",
  uncertain: "bg-[var(--bg-elevated)] text-[var(--text-secondary)]",
};

export function OpportunityNarrativePanel({
  patent,
  artifact,
  isLoading,
  onGenerate,
}: OpportunityNarrativePanelProps) {
  const [handleGenerate, isGenerating] = useAsyncAction(onGenerate);

  if (isLoading || isGenerating) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center gap-3 text-[var(--text-muted)]">
          <Spinner size="sm" />
          <span>Generating Opportunity Narrative...</span>
        </div>
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-[var(--text-primary)]">What Could Someone Build?</h2>
        </div>
        <p className="text-sm text-[var(--text-muted)] mb-4">
          Generate a commercialization narrative: target customers, possible products, risks, and timing.
        </p>
        <Button onClick={handleGenerate} variant="default" size="sm" disabled={isGenerating}>
          Generate Opportunity Narrative
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-[var(--text-primary)]">What Could Someone Build?</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium px-2 py-1 rounded-full bg-bg-[var(--accent-muted)] text-[var(--accent)]">
            {typeLabels[artifact.opportunity_type] || artifact.opportunity_type}
          </span>
          <Button onClick={handleGenerate} variant="outline" size="sm" disabled={isGenerating}>
            Regenerate
          </Button>
        </div>
      </div>

      {artifact.plain_english_opportunity && (
        <p className="text-sm text-[var(--text-secondary)] mb-4">{artifact.plain_english_opportunity}</p>
      )}

      <div className="flex flex-wrap gap-2 mb-4">
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${difficultyColors[artifact.implementation_difficulty] || difficultyColors.unknown}`}>
          Difficulty: {artifact.implementation_difficulty.replace("_", " ")}
        </span>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${timingColors[artifact.commercial_timing] || timingColors.uncertain}`}>
          Timing: {artifact.commercial_timing.replace("_", " ")}
        </span>
      </div>

      {artifact.possible_products.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
            Possible Products / Services
          </h3>
          <ul className="space-y-1">
            {artifact.possible_products.map((product, i) => (
              <li key={i} className="text-sm text-[var(--text-secondary)] flex items-start gap-2">
                <span className="text-bg-[var(--bg-elevated)]0 mt-0.5">●</span>
                {product}
              </li>
            ))}
          </ul>
        </div>
      )}

      {artifact.target_customers.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
            Target Customers
          </h3>
          <div className="flex flex-wrap gap-2">
            {artifact.target_customers.map((customer, i) => (
              <span key={i} className="text-xs bg-[var(--bg-elevated)] text-[var(--text-secondary)] px-2 py-1 rounded">
                {customer}
              </span>
            ))}
          </div>
        </div>
      )}

      {artifact.risks.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
            Risks
          </h3>
          <ul className="space-y-1">
            {artifact.risks.map((risk, i) => (
              <li key={i} className="text-sm text-[var(--text-secondary)] flex items-start gap-2">
                <span className="text-red-400 mt-0.5">▸</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}

      <AISourceFooter />
    </div>
  );
}
