"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import { useWatchlist, removeFromWatchlist } from "@/hooks/useWatchlist";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Score } from "@/components/ui/Score";
import { formatDate } from "@/lib/utils";
import { savedSearchesApi } from "@/lib/api";
import type { WatchlistItemResponse, SavedSearch } from "@/lib/types";

type Tab = "patents" | "companies" | "searches";

const PAGE_SIZE = 12;

export default function WatchlistPage() {
  const [activeTab, setActiveTab] = useState<Tab>("patents");

  return (
    <div>
      <PageHeader
        title="Your Workspace"
        description="Saved patents, followed companies, and saved searches — your personal intelligence space."
      />

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6">
        {[
          { id: "patents" as Tab, label: "Saved Patents" },
          { id: "companies" as Tab, label: "Followed Companies" },
          { id: "searches" as Tab, label: "Saved Searches" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : "text-[var(--text-secondary)] hover:bg-[var(--bg-glass)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "patents" && <SavedPatentsTab />}
      {activeTab === "companies" && <FollowedCompaniesTab />}
      {activeTab === "searches" && <SavedSearchesTab />}
    </div>
  );
}

// ── Saved Patents Tab ──────────────────────────────────────────

function SavedPatentsTab() {
  const { data: items, isLoading, mutate } = useWatchlist();
  const [removing, setRemoving] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const paginated = useMemo(() => {
    if (!items) return { pageItems: [] as WatchlistItemResponse[], totalPages: 0, total: 0 };
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

  if (isLoading) return <LoadingState variant="card" count={6} />;

  if (!items || items.length === 0) {
    return (
      <EmptyState
        icon="bookmark"
        title="No patents saved yet"
        message="Bookmark patents from any page to build your personal watchlist. Saved patents appear in your Today briefing."
        actions={[
          { label: "Browse patents", href: "/patents", primary: true },
          { label: "Search patents", href: "/search" },
        ]}
      />
    );
  }

  return (
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
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-[var(--text-muted)]">
                  {item.patent.assignees[0] || "Unknown assignee"}
                </span>
                {item.patent.opportunity_score != null && (
                  <Score value={item.patent.opportunity_score} kind="opportunity" size="sm" />
                )}
              </div>
            </div>
            <button
              onClick={() => handleRemove(item)}
              disabled={removing === item.id}
              className="flex-shrink-0 p-2 text-[var(--text-muted)] hover:text-[var(--expiry-lapsed-confirmed)] transition-colors disabled:opacity-50"
              title="Remove from watchlist"
              aria-label="Remove from watchlist"
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
  );
}

// ── Followed Companies Tab ─────────────────────────────────────

function FollowedCompaniesTab() {
  const { data, isLoading } = useSWR(
    "followed-companies",
    () =>
      fetch("/api/v1/suppliers/follows", { credentials: "include" }).then(
        (r) => (r.ok ? r.json() : [])
      ),
    { revalidateOnFocus: false }
  );

  if (isLoading) return <LoadingState variant="card" count={4} />;

  if (!data || data.length === 0) {
    return (
      <EmptyState
        icon="search"
        title="No companies followed"
        message="Follow companies from the Company Intelligence page to track their patent portfolio activity."
        actions={[
          { label: "Browse companies", href: "/companies", primary: true },
        ]}
      />
    );
  }

  return (
    <div className="space-y-2">
      {data.map((f: { company_name: string; normalized_name: string }) => (
        <Link
          key={f.normalized_name}
          href={`/companies/${encodeURIComponent(f.company_name)}`}
          className="flex items-center justify-between bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 hover:border-[var(--border-default)] transition-colors"
        >
          <span className="font-medium text-[var(--text-primary)]">{f.company_name}</span>
          <span className="text-xs text-[var(--text-muted)]">View profile →</span>
        </Link>
      ))}
    </div>
  );
}

// ── Saved Searches Tab ─────────────────────────────────────────

function SavedSearchesTab() {
  const { data, isLoading, mutate } = useSWR(
    "saved-searches-workspace",
    () => savedSearchesApi.list(),
    { revalidateOnFocus: false }
  );

  if (isLoading) return <LoadingState variant="card" count={4} />;

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon="search"
        title="No saved searches"
        message="Save your search queries from the Search page to return to them later. Saved searches preserve your query, filters, and sort order."
        actions={[
          { label: "Open search", href: "/search", primary: true },
        ]}
      />
    );
  }

  return (
    <div className="space-y-2">
      {data.items.map((s: SavedSearch) => (
        <div
          key={s.id}
          className="flex items-center justify-between bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4"
        >
          <Link
            href={`/search?q=${encodeURIComponent(s.query)}&mode=${s.mode}${s.sort_by !== "relevance" ? `&sort_by=${s.sort_by}&sort_order=${s.sort_order}` : ""}`}
            className="flex-1 min-w-0"
          >
            <p className="font-medium text-[var(--text-primary)] truncate">{s.name}</p>
            <p className="text-xs text-[var(--text-muted)] mt-0.5 truncate">
              &ldquo;{s.query}&rdquo; · {s.mode}
            </p>
          </Link>
          <button
            onClick={async () => {
              await savedSearchesApi.delete(s.id);
              mutate();
            }}
            className="ml-3 text-xs text-[var(--text-muted)] hover:text-[var(--expiry-lapsed-confirmed)] shrink-0"
            title="Delete saved search"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
