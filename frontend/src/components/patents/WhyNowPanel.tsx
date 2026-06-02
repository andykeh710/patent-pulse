"use client";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { AISourceFooter } from "@/components/patents/AISourceFooter";
import type { PatentDetail } from "@/lib/types";

interface WhyNowSignal {
  type: string;
  explanation: string;
}

interface WhyNowArtifact {
  headline: string;
  summary: string;
  signals: WhyNowSignal[];
  confidence: string;
  limitations: string[];
}

interface WhyNowPanelProps {
  patent: PatentDetail;
  artifact: WhyNowArtifact | null;
  isLoading: boolean;
  onGenerate: () => Promise<void>;
}

export function WhyNowPanel({ patent, artifact, isLoading, onGenerate }: WhyNowPanelProps) {
  const [handleGenerate, isGenerating] = useAsyncAction(onGenerate);

  if (isLoading || isGenerating) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center gap-3 text-[var(--text-muted)]">
          <Spinner size="sm" />
          <span>Generating Why Now narrative...</span>
        </div>
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-[var(--text-primary)]">Why Now?</h2>
        </div>
        <p className="text-sm text-[var(--text-muted)] mb-4">
          Analyze why this patent is relevant today — timing, urgency, and market signals.
        </p>
        <Button onClick={handleGenerate} variant="default" size="sm" disabled={isGenerating}>
          Generate Why Now
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-[var(--text-primary)]">Why Now?</h2>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-medium px-2 py-1 rounded-full ${
              artifact.confidence === "high"
                ? "bg-[var(--score-high-bg)] text-[var(--score-high)]"
                : artifact.confidence === "medium"
                ? "bg-[var(--score-medium-bg)] text-[var(--score-medium)]"
                : "bg-[var(--bg-elevated)] text-[var(--text-secondary)]"
            }`}
          >
            {artifact.confidence.charAt(0).toUpperCase() + artifact.confidence.slice(1)} confidence
          </span>
          <Button onClick={handleGenerate} variant="outline" size="sm" disabled={isGenerating}>
            Regenerate
          </Button>
        </div>
      </div>

      {artifact.headline && (
        <p className="text-sm font-medium text-[var(--text-primary)] mb-3">{artifact.headline}</p>
      )}
      {artifact.summary && (
        <p className="text-sm text-[var(--text-secondary)] mb-4">{artifact.summary}</p>
      )}

      {artifact.signals.length > 0 && (
        <div className="space-y-2 mb-4">
          <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
            Signals
          </h3>
          {artifact.signals.map((signal, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-xs font-medium text-[var(--accent)] bg-bg-[var(--bg-elevated)] px-2 py-1 rounded flex-shrink-0">
                {signal.type}
              </span>
              <p className="text-sm text-[var(--text-secondary)]">{signal.explanation}</p>
            </div>
          ))}
        </div>
      )}

      <AISourceFooter />

      {artifact.limitations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
            Limitations
          </h3>
          <ul className="space-y-1">
            {artifact.limitations.map((lim, i) => (
              <li key={i} className="text-xs text-[var(--text-muted)] flex items-start gap-2">
                <span>•</span>
                {lim}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
