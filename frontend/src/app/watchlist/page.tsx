"use client";

import { useState } from "react";
import Link from "next/link";
import { useWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { WatchlistItemResponse } from "@/lib/types";

export default function WatchlistPage() {
  const { data: items, isLoading, mutate } = useWatchlist();
  const [removing, setRemoving] = useState<string | null>(null);

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
        <h1 className="text-2xl font-bold text-gray-900">Watchlist</h1>
        <p className="text-gray-600 mt-1">
          {items?.length
            ? `${items.length} saved ${items.length === 1 ? "patent" : "patents"}`
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
        <div className="rounded-lg bg-gray-50 py-16 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
          <p className="text-gray-500 mt-3">No patents saved yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Click the bookmark icon on any patent to save it here
          </p>
          <Link
            href="/patents"
            className="inline-block mt-4 text-sm text-primary-600 hover:underline"
          >
            Browse patents
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-4 bg-white rounded-lg border border-gray-200 p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="font-mono">{item.patent.doc_id}</span>
                  <span>·</span>
                  <span>Saved {formatDate(item.added_at)}</span>
                </div>
                <Link
                  href={`/patents/${item.patent.id}`}
                  className="mt-1 block font-medium text-gray-900 hover:text-primary-700"
                >
                  {item.patent.title || "Untitled patent"}
                </Link>
                {item.patent.summary_what_it_is && (
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                    {item.patent.summary_what_it_is}
                  </p>
                )}
                {item.note && (
                  <p className="text-sm text-primary-700 mt-2 italic">
                    Note: {item.note}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs text-gray-500">
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
                className="flex-shrink-0 p-2 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
                title="Remove from watchlist"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
