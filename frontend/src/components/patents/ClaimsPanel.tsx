"use client";

import { useState } from "react";

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

  // Split by claim numbers: "1.", "2.", etc. at start of line or after newline
  const claimPattern = /(?:^|\n)\s*(\d+)\.\s+/g;
  const matches = [...rawText.matchAll(claimPattern)];

  if (matches.length === 0) {
    // Fallback: treat the whole text as a single claim block
    return [{ number: 1, text: rawText.trim(), isIndependent: true }];
  }

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i];
    const claimNum = parseInt(match[1], 10);
    const startIdx = match.index! + match[0].length;
    const endIdx = i + 1 < matches.length ? matches[i + 1].index! : rawText.length;
    const claimText = rawText.slice(startIdx, endIdx).trim();

    // A dependent claim typically references another claim
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
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900">Claims</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            {claims.length} total · {independentClaims.length} independent
          </span>
          {dependentClaims.length > 0 && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-xs text-primary-600 hover:text-primary-800 font-medium"
            >
              {showAll
                ? "Show independent only"
                : `Show all ${claims.length} claims`}
            </button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {displayClaims.map((claim) => (
          <div key={claim.number} className="group">
            <div className="flex items-start gap-3">
              <span
                className={`flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                  claim.isIndependent
                    ? "bg-primary-100 text-primary-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                {claim.number}
              </span>
              <div className="flex-1 min-w-0">
                {claim.isIndependent && (
                  <span className="inline-block text-[10px] font-semibold uppercase tracking-wider text-primary-600 mb-1">
                    Independent
                  </span>
                )}
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {claim.text}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {!showAll && dependentClaims.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <button
            onClick={() => setShowAll(true)}
            className="text-sm text-primary-600 hover:text-primary-800 font-medium"
          >
            Show {dependentClaims.length} dependent claims
          </button>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Claims are extracted from patent filings and may be incomplete. Independent
          claims are identified heuristically.
        </p>
      </div>
    </div>
  );
}
