"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { WatchlistItemResponse } from "@/lib/types";

const PAGE_SIZE = 12;

export default function WatchlistPage() {
  const { data: items, isLoading, mutate } = useWatchlist();
  const [removing, setRemoving] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const paginated = useMemo(() => {
    if (!items) return { pageItems: [], totalPages: 0, total: 0 };
    const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
    const safePage = Math.min(page, totalPages);
    const start = (safePage - 1) * PAGE_SIZE;
    return {
      pageItems: items.slice(start, start + PAGE_SIZE),
      totalPages,
      total: items.length,
    };
  }, [items, page]);

  const handleRemove = async (item: WatchlistItemResponse) => {
    setRemoving(item.id);
    try {
      await removeFromWatchlist(item.id, item.patent.id);
      mutate();
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Watchlist</h1>
        <p className="text-[var(--text-secondary)] mt-1">
          {paginated.total
            ? `${paginated.total} saved ${paginated.total === 1 ? "patent" : "patents"}`
            : "Save patents to track them here"}
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <PatentCardSkeleton key={i} />
          ))}
        </div>
      ) : !items || items.length === 0 ? (
        <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] py-16 px-8 text-center">
          <svg className="mx-auto h-12 w-12 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
          <p className="text-[var(--text-muted)] mt-3 font-medium">No patents saved yet</p>
          <p className="text-sm text-[var(--text-muted)] mt-1 max-w-sm mx-auto">
            Bookmark patents from any page to build your personal watchlist.
            Saved patents will also appear in your Today briefing.
          </p>
          <div className="flex items-center justify-center gap-3 mt-5">
            <Link
              href="/patents"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent)] transition-colors"
            >
              Browse patents
            </Link>
            <Link
              href="/search"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] text-sm font-medium hover:bg-[var(--bg-base)] transition-colors"
            >
              Search patents
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {paginated.pageItems.map((item) => (
              <div
                key={item.id}
                className="flex items-start gap-4 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--border-default)] transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                    <span className="font-mono">{item.patent.doc_id}</span>
                    <span>·</span>
                    <span>Saved {formatDate(item.added_at)}</span>
                  </div>
                  <Link
                    href={`/patents/${item.patent.id}`}
                    className="mt-1 block font-medium text-[var(--text-primary)] hover:text-[var(--accent)]"
                  >
                    {item.patent.title || "Untitled patent"}
                  </Link>
                  {item.patent.summary_what_it_is && (
                    <p className="text-sm text-[var(--text-secondary)] mt-1 line-clamp-2">
                      {item.patent.summary_what_it_is}
                    </p>
                  )}
                  {item.note && (
                    <p className="text-sm text-[var(--accent)] mt-2 italic">
                      Note: {item.note}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-[var(--text-muted)]">
                      {item.patent.assignees[0] || "Unknown assignee"}
                    </span>
                    {item.patent.opportunity_score != null && (
                      <Badge variant="default" size="sm">
                        Opp: {item.patent.opportunity_score.toFixed(0)}
                      </Badge>
                    )}
                    {item.tags.map((tag) => (
                      <Badge key={tag} variant="default" size="sm">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => handleRemove(item)}
                  disabled={removing === item.id}
                  className="flex-shrink-0 p-2 text-[var(--text-muted)] hover:text-red-500 transition-colors disabled:opacity-50"
                  title="Remove from watchlist"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {paginated.totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} of {paginated.totalPages}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= paginated.totalPages}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
