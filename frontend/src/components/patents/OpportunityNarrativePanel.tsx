"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
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
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
  unknown: "bg-gray-100 text-gray-600",
};

const timingColors: Record<string, string> = {
  now: "bg-green-100 text-green-700",
  near_term: "bg-blue-100 text-blue-700",
  long_term: "bg-purple-100 text-purple-700",
  uncertain: "bg-gray-100 text-gray-600",
};

export function OpportunityNarrativePanel({
  patent,
  artifact,
  isLoading,
  onGenerate,
}: OpportunityNarrativePanelProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      await onGenerate();
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading || isGenerating) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-3 text-gray-500">
          <Spinner size="sm" />
          <span>Generating Opportunity Narrative...</span>
        </div>
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">What Could Someone Build?</h2>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Generate a commercialization narrative: target customers, possible products, risks, and timing.
        </p>
        <Button onClick={handleGenerate} variant="default" size="sm">
          Generate Opportunity Narrative
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900">What Could Someone Build?</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium px-2 py-1 rounded-full bg-primary-100 text-primary-700">
            {typeLabels[artifact.opportunity_type] || artifact.opportunity_type}
          </span>
          <Button onClick={handleGenerate} variant="outline" size="sm">
            Regenerate
          </Button>
        </div>
      </div>

      {artifact.plain_english_opportunity && (
        <p className="text-sm text-gray-700 mb-4">{artifact.plain_english_opportunity}</p>
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
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Possible Products / Services
          </h3>
          <ul className="space-y-1">
            {artifact.possible_products.map((product, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-primary-500 mt-0.5">●</span>
                {product}
              </li>
            ))}
          </ul>
        </div>
      )}

      {artifact.target_customers.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Target Customers
          </h3>
          <div className="flex flex-wrap gap-2">
            {artifact.target_customers.map((customer, i) => (
              <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                {customer}
              </span>
            ))}
          </div>
        </div>
      )}

      {artifact.risks.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Risks
          </h3>
          <ul className="space-y-1">
            {artifact.risks.map((risk, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="text-red-400 mt-0.5">▸</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
