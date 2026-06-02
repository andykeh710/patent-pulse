"use client";

import { Suspense, useState, useCallback, useEffect, type FormEvent } from "react";
import { useSearchParams as useNextSearchParams, useRouter, usePathname } from "next/navigation";
import { BRAND } from "@/lib/brand";
import { usePatentSearch } from "@/hooks/usePatents";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { FreshnessBanner } from "@/components/ui/FreshnessBanner";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { Badge } from "@/components/ui/Badge";
import type { SearchParams } from "@/lib/types";
import useSWR from "swr";
import { semanticApi } from "@/lib/api";
import type { SemanticSearchResponse } from "@/lib/types";

type SearchMode = "fulltext" | "semantic";

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-[var(--text-muted)]">Loading...</div>}>
      <SearchContent />
    </Suspense>
  );
}

function SearchContent() {
  const urlParams = useNextSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [query, setQuery] = useState(urlParams.get("q") || "");
  const [submitted, setSubmitted] = useState(urlParams.get("q") || "");
  const [mode, setMode] = useState<SearchMode>(
    (urlParams.get("mode") as SearchMode) || "fulltext"
  );
  const [page, setPage] = useState(
    urlParams.get("page") ? Number(urlParams.get("page")) : 1
  );

  // Sync to URL
  useEffect(() => {
    const sp = new URLSearchParams();
    if (submitted) sp.set("q", submitted);
    if (mode !== "fulltext") sp.set("mode", mode);
    if (page > 1) sp.set("page", String(page));
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [submitted, mode, page, pathname, router]);

  const searchParams: SearchParams | null = submitted
    ? { q: submitted, page, page_size: 20 }
    : null;

  const { data: fulltextResults, isLoading: ftLoading } = usePatentSearch(
    mode === "fulltext" ? searchParams : null
  );

  const { data: semanticResults, isLoading: semLoading } = useSWR<SemanticSearchResponse>(
    mode === "semantic" && submitted ? ["semantic", submitted] : null,
    () => semanticApi.query(submitted, 20)
  );

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (query.trim().length >= 3) {
        setSubmitted(query.trim());
        setPage(1);
      }
    },
    [query]
  );

  const isLoading = mode === "fulltext" ? ftLoading : semLoading;
  const hasResults = mode === "fulltext"
    ? fulltextResults && fulltextResults.items.length > 0
    : semanticResults && semanticResults.results.length > 0;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Search Patents</h1>
        <FreshnessBanner show={["patents"]} className="mt-2" />
        <p className="text-[var(--text-secondary)] mt-1">
          Find patents by keyword or describe what you&apos;re looking for
        </p>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                mode === "fulltext"
                  ? "Search by title, abstract, or keywords..."
                  : "Describe the technology you're looking for..."
              }
              className="w-full rounded-lg border border-[var(--border-default)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={query.trim().length < 3}
            className="px-6 py-3 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Search
          </button>
        </div>

        {/* Mode toggle */}
        <div className="mt-3 flex items-center gap-3">
          <span className="text-xs text-[var(--text-muted)]">Search mode:</span>
          <button
            type="button"
            onClick={() => { setMode("fulltext"); setSubmitted(""); }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              mode === "fulltext"
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
            }`}
          >
            Keyword Search
          </button>
          <button
            type="button"
            onClick={() => { setMode("semantic"); setSubmitted(""); }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              mode === "semantic"
                ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
            }`}
          >
            Semantic Search
          </button>
          {mode === "semantic" && (
            <span className="text-xs text-[var(--text-muted)]">
              Uses AI embeddings to find patents by meaning
            </span>
          )}
        </div>
      </form>

      {/* Results */}
      {!submitted ? (
        <div className="rounded-lg bg-[var(--bg-base)] py-16 text-center">
          <svg className="mx-auto h-12 w-12 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-[var(--text-muted)] mt-3">Enter a search query to find patents</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">Minimum 3 characters</p>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <PatentCardSkeleton key={i} />
          ))}
        </div>
      ) : !hasResults ? (
        <div className="rounded-lg bg-[var(--bg-base)] py-12 text-center">
          <p className="text-[var(--text-muted)]">No patents found for &ldquo;{submitted}&rdquo;</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            {mode === "fulltext"
              ? "Try different keywords or switch to semantic search"
              : "Try rephrasing your description or switch to keyword search"}
          </p>
        </div>
      ) : mode === "fulltext" && fulltextResults ? (
        <>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            {fulltextResults.total.toLocaleString()} results for &ldquo;{submitted}&rdquo;
            {fulltextResults.pages > 1 && ` · page ${fulltextResults.page} of ${fulltextResults.pages}`}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {fulltextResults.items.map((patent) => (
              <PatentCard key={patent.id} patent={patent} />
            ))}
          </div>
          {fulltextResults.pages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} / {fulltextResults.pages}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= fulltextResults.pages}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : semanticResults ? (
        <>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            Search across {BRAND.name}&apos;s indexed publications using keywords or semantic similarity
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {semanticResults.results.map((result) => (
              <div key={result.patent.id} className="relative">
                <PatentCard patent={result.patent} />
                <div className="absolute top-2 right-2">
                  <Badge
                    variant="default"
                    size="sm"
                    className="bg-[var(--accent-muted)] text-[var(--type-foryou)] border-[var(--type-foryou)]/30"
                  >
                    {(result.similarity * 100).toFixed(0)}% match
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      <div className="mt-8">
        <SourceAttribution />
      </div>
    </div>
  );
}
