"use client";

import Link from "next/link";
import type { PatentListItem } from "@/lib/types";
import { formatDate, truncate } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Score } from "@/components/ui/Score";
import { TagsPanel } from "./TagsPanel";
import { LegalConfidenceBadge } from "./LegalConfidenceBadge";
import { RiskFlagsBadge } from "./RiskFlagsBadge";
import { SourceAttribution } from "@/components/ui/SourceAttribution";

interface PatentCardProps {
  patent: PatentListItem;
  isSaved?: boolean;
  onToggleSave?: (patentId: string) => void;
}

export function PatentCard({ patent, isSaved, onToggleSave }: PatentCardProps) {
  return (
    <Link
      href={`/patents/${patent.id}`}
      className="block bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--accent)]/30 hover:shadow-[var(--shadow-sm)] transition-all relative"
    >
      {/* Save/bookmark button */}
      {onToggleSave && (
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleSave(patent.id); }}
          className={`absolute top-3 right-3 p-1.5 rounded-lg transition-colors ${
            isSaved
              ? "text-[var(--accent)] bg-[var(--accent-muted)]"
              : "text-[var(--text-muted)] hover:text-[var(--accent)] hover:bg-[var(--accent-muted)]"
          }`}
          title={isSaved ? "Remove from watchlist" : "Save to watchlist"}
          aria-label={isSaved ? "Remove from watchlist" : "Save to watchlist"}
        >
          <svg className="w-4 h-4" fill={isSaved ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
        </button>
      )}

      <div className="flex justify-between items-start gap-3 mb-2">
        <h3 className="font-medium text-[var(--text-primary)] leading-tight">
          {truncate(patent.title, 80) || "Untitled Patent"}
        </h3>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <Score value={patent.opportunity_score} kind="opportunity" size="sm" showLabel={false} />
          <Score value={patent.interesting_score} kind="interesting" size="sm" showLabel={false} />
        </div>
      </div>

      {patent.summary_what_it_is && (
        <p className="text-sm text-[var(--text-secondary)] mb-3 line-clamp-2">
          {patent.summary_what_it_is}
        </p>
      )}

      {/* V3.8I: patent figure thumbnail */}
      {patent.thumbnail_url && (
        <div className="mb-3 aspect-[4/3] rounded-lg overflow-hidden bg-[var(--surface)] border border-[var(--border)]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={patent.thumbnail_url}
            alt={`Figure from patent ${patent.publication_number}`}
            className="w-full h-full object-contain"
            loading="lazy"
          />
        </div>
      )}

      {patent.tags && (
        <div className="mb-3">
          <TagsPanel tags={patent.tags} variant="compact" />
        </div>
      )}

      {patent.tags?.risk_flags && patent.tags.risk_flags.length > 0 && (
        <div className="mb-3">
          <RiskFlagsBadge flags={patent.tags.risk_flags} collapse />
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-3">
        {patent.cpc.slice(0, 3).map((code) => (
          <Badge key={code} variant="default" size="sm">
            {code.split(" ")[0]}
          </Badge>
        ))}
        {patent.cpc.length > 3 && (
          <Badge variant="default" size="sm">
            +{patent.cpc.length - 3}
          </Badge>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
        <div className="flex items-center gap-2">
          {patent.doc_id && (
            <Badge variant="default" size="sm" className="bg-[var(--bg-elevated)] text-[var(--text-secondary)] font-mono">
              {patent.doc_id.split(":")[0]}
            </Badge>
          )}
          <span>{patent.publication_number}</span>
          <span>&bull;</span>
          <span>
            {patent.legal_status === "GRANTED" ? "Granted" : "Published"}{" "}
            {formatDate(patent.grant_date || patent.publication_date)}
          </span>
          <LegalConfidenceBadge
            confidence={patent.legal_status_confidence}
            legalStatus={patent.legal_status}
          />
        </div>
        <div className="flex items-center gap-3">
          {patent.figure_page_url && (
            <a
              href={patent.figure_page_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--accent)] hover:text-[var(--accent)] flex items-center gap-1"
              onClick={(e) => e.stopPropagation()}
              title="View patent figures at Google Patents"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Figures
            </a>
          )}
          {patent.assignees.length > 0 && (
            <span className="truncate max-w-[150px]">{patent.assignees[0]}</span>
          )}
        </div>
      </div>
      <SourceAttribution docId={patent.doc_id} />
    </Link>
  );
}
