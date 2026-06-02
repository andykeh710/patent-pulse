"use client";

import { useState } from "react";
import type { Summary } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";

interface AISummaryPanelProps {
  summary: Summary | null;
  isLoading?: boolean;
}

export function AISummaryPanel({ summary, isLoading }: AISummaryPanelProps) {
  const [showSources, setShowSources] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <Skeleton className="h-5 w-5 rounded-full" />
          <Skeleton className="h-5 w-32" />
        </div>
        <Skeleton className="h-6 w-full mb-4" />
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-3/4 mb-4" />
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-[var(--bg-base)] rounded-lg border border-[var(--border-subtle)] p-6 text-center">
        <div className="animate-pulse flex flex-col items-center">
          <svg
            className="w-8 h-8 text-bg-[var(--bg-elevated)]0 mb-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <p className="text-[var(--text-secondary)] font-medium">Generating AI Summary...</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">This may take a few moments</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] overflow-hidden">
      <div className="bg-[var(--bg-elevated)] px-6 py-3 border-b border-bg-[var(--accent-muted)]">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-[var(--accent)]"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <span className="font-medium text-[var(--accent)]">AI Summary</span>
        </div>
      </div>

      <div className="p-6 space-y-5">
        <div>
          <p className="text-lg font-medium text-[var(--text-primary)] leading-relaxed">
            {summary.what_it_is}
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-sm font-medium text-[var(--text-muted)] mb-1">
              Problem Solved
            </h4>
            <p className="text-[var(--text-secondary)]">{summary.problem_solved}</p>
          </div>
          <div>
            <h4 className="text-sm font-medium text-[var(--text-muted)] mb-1">
              How It Works
            </h4>
            <p className="text-[var(--text-secondary)]">{summary.how_it_works}</p>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-[var(--text-muted)] mb-1">
            Commercial Significance
          </h4>
          <p className="text-[var(--text-secondary)]">{summary.commercial_significance}</p>
        </div>

        <div>
          <h4 className="text-sm font-medium text-[var(--text-muted)] mb-2">
            Who Should Care
          </h4>
          <div className="flex flex-wrap gap-2">
            {summary.who_should_care.map((role, i) => (
              <Badge key={i} variant="default" size="md">
                {role}
              </Badge>
            ))}
          </div>
        </div>

        {summary.novel_applications.length > 0 && (
          <div className="bg-[var(--score-medium-bg)] rounded-lg p-4 border border-[var(--score-medium)]/30">
            <h4 className="text-sm font-medium text-[var(--score-medium)] mb-2 flex items-center gap-2">
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
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              Novel Applications
            </h4>
            <ul className="space-y-2">
              {summary.novel_applications.map((app, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Badge variant="speculative" size="sm">
                    SPECULATIVE
                  </Badge>
                  <span className="text-amber-900">{app.application}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-start gap-2 text-sm text-[var(--text-muted)] bg-[var(--bg-base)] rounded-lg p-3">
          <svg
            className="w-4 h-4 mt-0.5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{summary.confidence_note}</span>
        </div>

        {summary.source_spans.length > 0 && (
          <div>
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-sm text-[var(--accent)] hover:text-[var(--accent)] font-medium flex items-center gap-1"
            >
              {showSources ? "Hide" : "Show"} source references
              <svg
                className={`w-4 h-4 transition-transform ${showSources ? "rotate-180" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {showSources && (
              <div className="mt-3 space-y-2">
                {summary.source_spans.map((span, i) => (
                  <div
                    key={i}
                    className="bg-[var(--bg-base)] rounded p-3 border border-[var(--border-default)]"
                  >
                    <p className="text-sm text-[var(--text-secondary)] italic">
                      &ldquo;{span.quote}&rdquo;
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      Source: {span.field}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
