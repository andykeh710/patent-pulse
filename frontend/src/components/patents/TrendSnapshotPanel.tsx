"use client";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import type { PatentDetail } from "@/lib/types";

interface TrendComponent {
  sub_score: number;
  weight: number;
  contribution: number;
}

interface TrendSnapshotArtifact {
  trend_score: number;
  components: Record<string, TrendComponent>;
}

interface TrendSnapshotPanelProps {
  patent: PatentDetail;
  artifact: TrendSnapshotArtifact | null;
  isLoading: boolean;
  onGenerate: () => Promise<void>;
}

export function TrendSnapshotPanel({ patent, artifact, isLoading, onGenerate }: TrendSnapshotPanelProps) {
  const [handleGenerate, isGenerating] = useAsyncAction(onGenerate);

  if (isLoading || isGenerating) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center gap-3 text-[var(--text-muted)]">
          <Spinner size="sm" />
          <span>Generating Trend Snapshot...</span>
        </div>
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-[var(--text-primary)]">Trend Snapshot</h2>
        </div>
        <p className="text-sm text-[var(--text-muted)] mb-4">
          Technology-momentum signals, cross-industry relevance, and industry diversity analysis.
        </p>
        <Button onClick={handleGenerate} variant="default" size="sm" disabled={isGenerating}>
          Generate Trend Snapshot
        </Button>
      </div>
    );
  }

  const score = artifact.trend_score;
  const components = artifact.components || {};

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-[var(--text-primary)]">Trend Snapshot</h2>
        <span className={`text-sm font-semibold ${score >= 60 ? "text-green-600" : score >= 40 ? "text-yellow-600" : "text-[var(--text-muted)]"}`}>
          {score}/100
        </span>
      </div>

      <div className="space-y-3">
        {Object.entries(components).map(([name, comp]) => (
          <div key={name} className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-[var(--text-secondary)] capitalize">{name.replace(/_/g, " ")}</span>
                <span className="text-xs text-[var(--text-muted)]">{Math.round(comp.contribution * 100)} pts</span>
              </div>
              <div className="w-full bg-[var(--bg-elevated)] rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${comp.sub_score >= 0.6 ? "bg-[var(--score-high-bg)]0" : comp.sub_score >= 0.4 ? "bg-yellow-500" : "bg-gray-400"}`}
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
