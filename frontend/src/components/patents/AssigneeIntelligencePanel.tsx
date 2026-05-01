"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import type { PatentDetail } from "@/lib/types";

interface AssigneeComponent {
  sub_score: number;
  weight: number;
  contribution: number;
}

interface AssigneeIntelligenceArtifact {
  assignee_intelligence_score: number;
  components: Record<string, AssigneeComponent>;
}

interface AssigneeIntelligencePanelProps {
  patent: PatentDetail;
  artifact: AssigneeIntelligenceArtifact | null;
  isLoading: boolean;
  onGenerate: () => Promise<void>;
}

export function AssigneeIntelligencePanel({ patent, artifact, isLoading, onGenerate }: AssigneeIntelligencePanelProps) {
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
          <span>Generating Assignee Intelligence...</span>
        </div>
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Assignee Intelligence</h2>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Analyze assignee type, portfolio signals, commercial orientation, and licensing potential.
        </p>
        <Button onClick={handleGenerate} variant="default" size="sm">
          Generate Assignee Intelligence
        </Button>
      </div>
    );
  }

  const score = artifact.assignee_intelligence_score;
  const components = artifact.components || {};

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900">Assignee Intelligence</h2>
        <span className={`text-sm font-semibold ${score >= 60 ? "text-green-600" : score >= 40 ? "text-yellow-600" : "text-gray-500"}`}>
          {score}/100
        </span>
      </div>

      <div className="space-y-3">
        {Object.entries(components).map(([name, comp]) => (
          <div key={name} className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-700 capitalize">{name.replace(/_/g, " ")}</span>
                <span className="text-xs text-gray-500">{Math.round(comp.contribution * 100)} pts</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${comp.sub_score >= 0.6 ? "bg-green-500" : comp.sub_score >= 0.4 ? "bg-yellow-500" : "bg-gray-400"}`}
                  style={{ width: `${Math.round(comp.sub_score * 100)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
