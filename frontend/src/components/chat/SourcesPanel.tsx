"use client";

import { useState } from "react";
import type { SourcePatent } from "@/hooks/useChatStream";

export function SourcesPanel({ patents }: { patents: SourcePatent[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-xs overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--bg-glass)] transition-colors text-left"
      >
        <span className="text-[var(--text-secondary)]">
          Sources ({patents.length} patent{patents.length !== 1 ? "s" : ""})
        </span>
        <svg
          className={`w-3 h-3 text-[var(--text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="divide-y divide-[var(--border-subtle)]">
          {patents.map((p) => (
            <a
              key={p.doc_id}
              href={`/patents?q=${encodeURIComponent(p.doc_id)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block px-3 py-2 hover:bg-[var(--bg-glass)] transition-colors no-underline"
            >
              <div className="font-medium text-[var(--text-primary)] truncate">
                {p.title}
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[var(--text-muted)]">
                <span className="font-mono text-[10px]">{p.doc_id}</span>
                {p.assignees?.length > 0 && (
                  <>
                    <span>·</span>
                    <span>{p.assignees[0]}</span>
                  </>
                )}
                {p.publication_date && (
                  <>
                    <span>·</span>
                    <span>{p.publication_date}</span>
                  </>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
