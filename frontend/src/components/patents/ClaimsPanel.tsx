"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";

interface ClaimsPanelProps {
  claimsText: string | null;
}

interface ParsedClaim {
  number: number;
  text: string;
  isIndependent: boolean;
}

/**
 * Parse raw claims text into structured claims.
 * Independent claims don't reference other claims (no "claim N" dependency).
 * Dependent claims reference a parent claim (e.g., "The method of claim 1, wherein...").
 */
function parseClaims(rawText: string): ParsedClaim[] {
  const claims: ParsedClaim[] = [];

  const claimPattern = /(?:^|\n)\s*(\d+)\.\s+/g;
  const matches = [...rawText.matchAll(claimPattern)];

  if (matches.length === 0) {
    return [{ number: 1, text: rawText.trim(), isIndependent: true }];
  }

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i];
    const claimNum = parseInt(match[1], 10);
    const startIdx = match.index! + match[0].length;
    const endIdx = i + 1 < matches.length ? matches[i + 1].index! : rawText.length;
    const claimText = rawText.slice(startIdx, endIdx).trim();

    const dependsOnPattern = /\bclaims?\s+\d+/i;
    const isIndependent = !dependsOnPattern.test(claimText);

    claims.push({
      number: claimNum,
      text: claimText,
      isIndependent,
    });
  }

  return claims;
}

// ── Sprint 3: Key mechanisms extractor ───────────────────────────────

const MECHANISM_PATTERNS = [
  /\bcomprising\s+(?:a\s+|an\s+|the\s+)?([^,;.]+?)(?=\s*,|\s*;|\s*\.|$)/gi,
  /\bwherein\s+(?:the\s+)?([^,;.]+?)(?=\s*,|\s*;|\s*\.|$)/gi,
  /\bconfigured to\s+([^,;.]+?)(?=\s*,|\s*;|\s*\.|$)/gi,
  /\badapted to\s+([^,;.]+?)(?=\s*,|\s*;|\s*\.|$)/gi,
];

const MECHANISM_STOPWORDS = new Set([
  "a", "an", "the", "at", "by", "for", "in", "of", "on", "to",
  "and", "or", "is", "are", "be", "said", "such", "each",
]);

function extractMechanisms(claimText: string): string[] {
  const found = new Set<string>();
  for (const pattern of MECHANISM_PATTERNS) {
    // Reset lastIndex since we reuse the regex with the global flag.
    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(claimText)) !== null) {
      const raw = (match[1] || "").trim().toLowerCase();
      // Filter: skip short fragments and stopwords-only fragments.
      const words = raw.split(/\s+/).filter((w) => w.length >= 2);
      const meaningful = words.filter((w) => !MECHANISM_STOPWORDS.has(w));
      if (meaningful.length >= 2) {
        // Take first ~6 words for the tag label.
        const label = meaningful.slice(0, 6).join(" ");
        if (label.length >= 3) found.add(label);
      }
    }
  }
  return [...found].slice(0, 5);
}

// ── Sprint 3: Broadness indicator ────────────────────────────────────

function getBroadness(claimText: string): "Broad" | "Narrow" | "Mixed" | null {
  const lower = claimText.toLowerCase();
  const hasOpen = /\bcomprising\b|\bincluding\b/i.test(lower);
  const hasClosed = /\bconsisting of\b|\bconsists of\b/i.test(lower);

  if (hasOpen && hasClosed) return "Mixed";
  if (hasOpen) return "Broad";
  if (hasClosed) return "Narrow";
  return null;
}

// ── Component ────────────────────────────────────────────────────────

export function ClaimsPanel({ claimsText }: ClaimsPanelProps) {
  const [showAll, setShowAll] = useState(false);

  if (!claimsText || claimsText.trim().length === 0) {
    return null;
  }

  const claims = parseClaims(claimsText);
  const independentClaims = claims.filter((c) => c.isIndependent);
  const dependentClaims = claims.filter((c) => !c.isIndependent);
  const displayClaims = showAll ? claims : independentClaims;

  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-[var(--text-primary)]">Claims</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--text-muted)]">
            {claims.length} total · {independentClaims.length} independent
          </span>
          {dependentClaims.length > 0 && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-xs text-[var(--accent)] hover:text-text-[var(--accent-hover)] font-medium"
            >
              {showAll
                ? "Show independent only"
                : `Show all ${claims.length} claims`}
            </button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {displayClaims.map((claim) => {
          const mechanisms = extractMechanisms(claim.text);
          const broadness = getBroadness(claim.text);

          return (
            <div key={claim.number} className="group">
              <div className="flex items-start gap-3">
                <span
                  className={`flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                    claim.isIndependent
                      ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                      : "bg-[var(--bg-elevated)] text-[var(--text-muted)]"
                  }`}
                >
                  {claim.number}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {claim.isIndependent && (
                      <span className="inline-block text-[10px] font-semibold uppercase tracking-wider text-[var(--accent)]">
                        Independent
                      </span>
                    )}
                    {/* Sprint 3: broadness indicator */}
                    {broadness && (
                      <span
                        className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                          broadness === "Broad"
                            ? "bg-[var(--score-medium-bg)] text-[var(--score-medium)]"
                            : broadness === "Narrow"
                            ? "bg-[var(--score-high-bg)] text-[var(--score-high)]"
                            : "bg-[var(--accent-muted)] text-[var(--type-foryou)]"
                        }`}
                        title={
                          broadness === "Broad"
                            ? "Open-ended language (comprising/including) — broader scope"
                            : broadness === "Narrow"
                            ? "Closed language (consisting of) — narrower scope"
                            : "Mixed open and closed language"
                        }
                      >
                        {broadness}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
                    {claim.text}
                  </p>

                  {/* Sprint 3: key mechanisms */}
                  {mechanisms.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {mechanisms.map((mech, i) => (
                        <Badge key={i} variant="default" size="sm">
                          {mech}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {!showAll && dependentClaims.length > 0 && (
        <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
          <button
            onClick={() => setShowAll(true)}
            className="text-sm text-[var(--accent)] hover:text-text-[var(--accent-hover)] font-medium"
          >
            Show {dependentClaims.length} dependent claims
          </button>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
        <p className="text-xs text-[var(--text-muted)]">
          Claims are extracted from patent filings and may be incomplete.
          Key mechanisms and broadness indicators are identified heuristically —
          not a legal determination of claim scope.
        </p>
      </div>
    </div>
  );
}
