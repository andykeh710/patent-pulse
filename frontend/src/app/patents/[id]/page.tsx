"use client";

import { use } from "react";
import Link from "next/link";
import { usePatent, usePatentSummary } from "@/hooks/usePatents";
import { AISummaryPanel } from "@/components/patents/AISummaryPanel";
import { ScoreBadge } from "@/components/patents/ScoreBadge";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatDate } from "@/lib/utils";

export default function PatentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: patent, isLoading } = usePatent(id);
  const { data: summary, isLoading: summaryLoading } = usePatentSummary(
    patent?.summarized_at ? null : id
  );

  const displaySummary = patent?.summary || summary;

  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-64 mb-4" />
        <Skeleton className="h-6 w-96 mb-8" />
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
          <div>
            <Skeleton className="h-48 w-full rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (!patent) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Patent not found</p>
        <Link href="/patents" className="text-primary-600 mt-2 inline-block">
          Back to patents
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          href="/patents"
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-flex items-center gap-1"
        >
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to patents
        </Link>

        <div className="flex items-start justify-between gap-4 mt-2">
          <h1 className="text-2xl font-bold text-gray-900">
            {patent.title || "Untitled Patent"}
          </h1>
          <ScoreBadge score={patent.interesting_score} />
        </div>

        <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
          <span>{patent.publication_number}</span>
          <span>•</span>
          <span>{patent.office}</span>
          <span>•</span>
          <Badge
            variant={patent.legal_status === "GRANTED" ? "success" : "default"}
          >
            {patent.legal_status}
          </Badge>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <AISummaryPanel
            summary={displaySummary}
            isLoading={summaryLoading && !patent.summarized_at}
          />

          {patent.abstract && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Abstract</h2>
              <p className="text-gray-700 leading-relaxed">{patent.abstract}</p>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Details</h2>

            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Application Number</dt>
                <dd className="font-medium">
                  {patent.application_number || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Filing Date</dt>
                <dd className="font-medium">{formatDate(patent.filing_date)}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Publication Date</dt>
                <dd className="font-medium">
                  {formatDate(patent.publication_date)}
                </dd>
              </div>
              {patent.grant_date && (
                <div>
                  <dt className="text-gray-500">Grant Date</dt>
                  <dd className="font-medium">
                    {formatDate(patent.grant_date)}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-gray-500">Estimated Expiry</dt>
                <dd className="font-medium">
                  {formatDate(patent.estimated_expiry_date)}
                </dd>
              </div>
            </dl>
          </div>

          {patent.assignees.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Assignees</h2>
              <ul className="space-y-1">
                {patent.assignees.map((assignee, i) => (
                  <li key={i} className="text-sm text-gray-700">
                    {assignee}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {patent.inventors.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">Inventors</h2>
              <ul className="space-y-1">
                {patent.inventors.map((inventor, i) => (
                  <li key={i} className="text-sm text-gray-700">
                    {inventor}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {patent.cpc.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">
                Classifications (CPC)
              </h2>
              <div className="flex flex-wrap gap-2">
                {patent.cpc.map((code, i) => (
                  <Badge key={i} variant="default" size="sm">
                    {code}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {patent.score_breakdown && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-3">
                Score Breakdown
              </h2>
              <dl className="space-y-2 text-sm">
                {Object.entries(patent.score_breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <dt className="text-gray-500 capitalize">
                      {key.replace(/_/g, " ")}
                    </dt>
                    <dd className="font-medium">
                      {Math.round(value * 100)}%
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
