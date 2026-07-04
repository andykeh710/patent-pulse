"use client";

import { useCallback, useEffect, useState } from "react";
import useSWR from "swr";
import { patentsApi } from "@/lib/api";

// ═══════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════
interface FigureData {
  ordinal: number;
  thumbnail_url: string;
  full_url: string;
  width: number | null;
  height: number | null;
}

interface PatentFiguresPanelProps {
  patentId: string;
  publicationNumber: string;
  figuresStatus: string | null;
}

// ═══════════════════════════════════════════════════════════════════════
// Figure Lightbox
// ═══════════════════════════════════════════════════════════════════════
function FigureLightbox({
  figures,
  initialIndex,
  publicationNumber,
  onClose,
}: {
  figures: FigureData[];
  initialIndex: number;
  publicationNumber: string;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(initialIndex);
  const [zoom, setZoom] = useState(1);

  const goNext = useCallback(() => setIndex((i) => (i + 1) % figures.length), [figures.length]);
  const goPrev = useCallback(() => setIndex((i) => (i - 1 + figures.length) % figures.length), [figures.length]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") goNext();
      if (e.key === "ArrowLeft") goPrev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, goNext, goPrev]);

  useEffect(() => {
    const el = document.getElementById("figure-lightbox");
    el?.focus();
  }, []);

  const current = figures[index];
  if (!current) return null;

  return (
    <div
      id="figure-lightbox"
      role="dialog"
      aria-label={`Figure ${current.ordinal} from patent ${publicationNumber}`}
      className="fixed inset-0 z-[100] bg-[var(--bg)]/95 flex flex-col items-center justify-center"
      tabIndex={-1}
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-2 rounded-full bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] transition-colors z-10"
        aria-label="Close lightbox"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Navigation */}
      {figures.length > 1 && (
        <>
          <button
            onClick={(e) => { e.stopPropagation(); goPrev(); }}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-2 rounded-full bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] transition-colors z-10"
            aria-label="Previous figure"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); goNext(); }}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-full bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] hover:text-[var(--text)] transition-colors z-10"
            aria-label="Next figure"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </>
      )}

      {/* Image */}
      <div
        className="max-w-[90vw] max-h-[85vh] flex items-center justify-center"
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => {
          e.preventDefault();
          setZoom((z) => Math.max(0.5, Math.min(5, z + (e.deltaY > 0 ? -0.25 : 0.25))));
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={current.full_url}
          alt={`Figure ${current.ordinal} from patent ${publicationNumber}`}
          className="max-w-full max-h-full object-contain transition-transform duration-150"
          style={{ transform: `scale(${zoom})` }}
          draggable={false}
        />
      </div>

      {/* Counter */}
      <div className="absolute bottom-4 text-xs text-[var(--text-muted)] bg-[var(--surface)] px-3 py-1.5 rounded-full border border-[var(--border)]">
        {index + 1} / {figures.length}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Skeleton shimmer
// ═══════════════════════════════════════════════════════════════════════
function SkeletonThumbnail() {
  return (
    <div className="aspect-[4/3] rounded-lg bg-[var(--surface)] border border-[var(--border)] animate-pulse" />
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Thumbnail strip item
// ═══════════════════════════════════════════════════════════════════════
function ThumbnailItem({
  figure,
  publicationNumber,
  onClick,
}: {
  figure: FigureData;
  publicationNumber: string;
  onClick: () => void;
}) {
  const [error, setError] = useState(false);
  if (error) return null;

  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 w-24 h-18 rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden hover:border-[var(--accent)]/40 transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      aria-label={`View figure ${figure.ordinal} from patent ${publicationNumber}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={figure.thumbnail_url}
        alt={`Figure ${figure.ordinal} from patent ${publicationNumber}`}
        className="w-full h-full object-cover"
        loading="lazy"
        onError={() => setError(true)}
      />
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════════
export function PatentFiguresPanel({
  patentId,
  publicationNumber,
  figuresStatus,
}: PatentFiguresPanelProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Fetch figure list from our API
  const { data, isLoading, error } = useSWR(
    patentId ? ["patent-figures", patentId] : null,
    () => patentsApi.getPatentFigures(patentId),
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );

  // Don't show anything for pending — no polling
  if (figuresStatus === "pending") return null;

  // Loading state
  if (isLoading) {
    return (
      <div className="mt-6">
        <FiguresHeading />
        <div className="flex gap-2 overflow-x-auto pb-2">
          <SkeletonThumbnail />
          <SkeletonThumbnail />
        </div>
      </div>
    );
  }

  // Error or no figures
  if (error || !data?.figures?.length) {
    // Silent fallback — log to console only
    if (error) console.warn("Patent figures fetch failed:", error);
    return null;
  }

  const figures: FigureData[] = data.figures;

  return (
    <div className="mt-6">
      <FiguresHeading count={figures.length} />

      {/* Thumbnail strip */}
      <div className="flex gap-2 overflow-x-auto pb-2" role="list" aria-label="Patent figures">
        {figures.map((fig, i) => (
          <ThumbnailItem
            key={fig.ordinal}
            figure={fig}
            publicationNumber={publicationNumber}
            onClick={() => setLightboxIndex(i)}
          />
        ))}
      </div>

      {/* Attribution */}
      <p className="text-xs text-[var(--text-muted)] mt-2">
        Images © patent office — verify at source.
      </p>

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <FigureLightbox
          figures={figures}
          initialIndex={lightboxIndex}
          publicationNumber={publicationNumber}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </div>
  );
}

function FiguresHeading({ count }: { count?: number }) {
  return (
    <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-3 flex items-center gap-1.5">
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      Patent Figures{count !== undefined ? ` (${count})` : ""}
    </h3>
  );
}
