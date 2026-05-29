"use client";

import Link from "next/link";
import type { PatentListItem } from "@/lib/types";
import { formatDate, truncate } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { ScoreBadge } from "./ScoreBadge";
import { OpportunityScoreBadge } from "./OpportunityScoreBadge";
import { TagsPanel } from "./TagsPanel";
import { LegalConfidenceBadge } from "./LegalConfidenceBadge";
import { RiskFlagsBadge } from "./RiskFlagsBadge";
import { SourceAttribution } from "@/components/ui/SourceAttribution";

interface PatentCardProps {
  patent: PatentListItem;
}

export function PatentCard({ patent }: PatentCardProps) {
  return (
    <Link
      href={`/patents/${patent.id}`}
      className="block bg-white rounded-lg border border-gray-200 p-4 hover:border-primary-300 hover:shadow-md transition-all"
    >
      <div className="flex justify-between items-start gap-3 mb-2">
        <h3 className="font-medium text-gray-900 leading-tight">
          {truncate(patent.title, 80) || "Untitled Patent"}
        </h3>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <OpportunityScoreBadge score={patent.opportunity_score} showLabel={false} />
          <ScoreBadge score={patent.interesting_score} showLabel={false} />
        </div>
      </div>

      {patent.summary_what_it_is && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {patent.summary_what_it_is}
        </p>
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

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-2">
          <span>{patent.publication_number}</span>
          <span>•</span>
          <span>
            {patent.legal_status === "GRANTED" ? "Granted" : "Published"}{" "}
            {formatDate(patent.grant_date || patent.publication_date)}
          </span>
          <LegalConfidenceBadge
            confidence={patent.legal_status_confidence}
            legalStatus={patent.legal_status}
          />
        </div>
        {patent.assignees.length > 0 && (
          <span className="truncate max-w-[150px]">{patent.assignees[0]}</span>
        )}
      </div>
      <SourceAttribution docId={patent.doc_id} />
    </Link>
  );
}
