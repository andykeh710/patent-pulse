"use client";

import { useState } from "react";
import useSWR from "swr";
import { patentsApi } from "@/lib/api";

interface PatentFiguresPanelProps {
  publicationNumber: string;
  figurePageUrl: string;
}

const FiguresHeading = () => (
  <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-2 flex items-center gap-1.5">
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
    Patent Figures
  </h3>
);

const LinkCardFallback = ({ figurePageUrl }: { figurePageUrl: string }) => (
  <a
    href={figurePageUrl}
    target="_blank"
    rel="noopener noreferrer"
    className="group block rounded-lg bg-[var(--bg-glass)] backdrop-blur-md border border-[var(--border-subtle)] hover:border-[var(--accent)]/40 hover:bg-[var(--bg-glass-strong)] p-5 transition-all duration-200"
  >
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="text-sm font-medium text-[var(--text-primary)]">View official figures</div>
        <div className="text-xs text-[var(--text-muted)] mt-0.5">
          Opens at the source in a new tab
        </div>
      </div>
      <span className="text-[var(--text-muted)] group-hover:text-[var(--accent)] transition-colors text-lg">
        ↗
      </span>
    </div>
  </a>
);

const SkeletonThumbnail = () => (
  <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-glass)] aspect-[4/5] max-w-sm animate-pulse" />
);

export function PatentFiguresPanel({ publicationNumber, figurePageUrl }: PatentFiguresPanelProps) {
  const [imgError, setImgError] = useState(false);

  const { data, isLoading, error } = useSWR(
    publicationNumber ? ["patent-thumbnail", publicationNumber] : null,
    () => patentsApi.getThumbnailUrl(publicationNumber),
    { revalidateOnFocus: false, dedupingInterval: 60_000 }
  );

  return (
    <div className="mt-4">
      <FiguresHeading />

      {isLoading && <SkeletonThumbnail />}

      {!isLoading && (error || !data?.url || imgError) && (
        <LinkCardFallback figurePageUrl={figurePageUrl} />
      )}

      {!isLoading && data?.url && !imgError && (
        <a
          href={figurePageUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="group block max-w-sm"
        >
          <div className="relative rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-glass)] overflow-hidden hover:border-[var(--accent)]/40 transition-colors">
            <img
              src={data.url}
              alt={`Figure from patent ${publicationNumber}`}
              className="block w-full h-auto"
              loading="lazy"
              onError={() => setImgError(true)}
            />
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[var(--bg-base)]/90 to-transparent p-2.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-xs text-[var(--text-primary)] flex items-center justify-between">
                View all figures
                <span className="text-[var(--accent)]">↗</span>
              </span>
            </div>
          </div>
        </a>
      )}

      <p className="text-xs text-[var(--text-muted)] mt-2">
        {data?.url && !imgError
          ? "Thumbnail via Google Patents. Click to view all figures at source."
          : "Figures © patent office. We link to the official source."}
      </p>
    </div>
  );
}
