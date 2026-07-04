"use client";

import { useState } from "react";
import type { ToolCallRecord } from "@/hooks/useChatStream";

export function ToolCallCard({ toolCall }: { toolCall: ToolCallRecord }) {
  const [expanded, setExpanded] = useState(false);
  const isPending = toolCall.status === "pending";
  const hasResult = (toolCall.status === "done" && toolCall.result != null) as boolean;

  const label =
    toolCall.name === "search_patents"
      ? "Searching patents"
      : toolCall.name === "open_patent"
        ? "Opening patent"
        : toolCall.name === "compare_companies"
          ? "Comparing companies"
          : `Tool: ${toolCall.name}`;

  function getResultSummary(result: Record<string, unknown>): string {
    if (typeof result.count === "number") return `Found ${result.count} patents`;
    if (typeof result.doc_id === "string") return `Opened ${result.doc_id}`;
    if (typeof result.compared === "number") return `Compared ${result.compared} companies`;
    return "Done";
  }

  const resultSummary = hasResult ? getResultSummary(toolCall.result!) : null;

  return (
    <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-xs overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--bg-glass)] transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          {isPending ? (
            <span className="inline-block w-2.5 h-2.5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          ) : (
            <span className="text-[var(--accent)]">✓</span>
          )}
          <span className="text-[var(--text-secondary)]">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          {resultSummary && (
            <span className="text-[var(--text-muted)]">{resultSummary}</span>
          )}
          <svg
            className={`w-3 h-3 text-[var(--text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-3 py-2 border-t border-[var(--border-subtle)] space-y-2">
          <div>
            <span className="text-[var(--text-muted)]">Input: </span>
            <code className="text-[var(--text-secondary)]">
              {JSON.stringify(toolCall.input)}
            </code>
          </div>

          {hasResult && (
            <div>
              <span className="text-[var(--text-muted)]">Result: </span>
              <pre className="text-[var(--text-secondary)] whitespace-pre-wrap max-h-32 overflow-y-auto mt-1 font-mono">
                {JSON.stringify(toolCall.result, null, 2)}
              </pre>
            </div>
          )}

          {hasResult && typeof (toolCall.result as Record<string, unknown>).error === "string" && (
            <div className="text-red-500 text-xs">
              Error: {(toolCall.result as Record<string, unknown>).error as string}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
