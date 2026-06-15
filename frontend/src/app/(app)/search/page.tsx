"use client";

import { Suspense, useState, useCallback, useEffect, type FormEvent } from "react";
import { useSearchParams as useNextSearchParams, useRouter, usePathname } from "next/navigation";
import { usePatentSearch } from "@/hooks/usePatents";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import type { SearchParams } from "@/lib/types";

type SearchMode = "fulltext" | "semantic" | "hybrid";

const NL_PLACEHOLDERS = [
  "battery thermal management for electric vehicles",
  "CRISPR delivery vectors for gene therapy",
  "solid-state electrolyte manufacturing",
  "autonomous drone navigation in GPS-denied environments",
  "Explain what you're looking for...",
];

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
    (urlParams.get("mode") as SearchMode) || "hybrid"
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

  const minChars = mode === "fulltext" ? 3 : 1;
  const canSubmit = query.trim().length >= minChars;

  const searchParams: SearchParams | null =
    submitted.length >= minChars
      ? { q: submitted, mode, page, page_size: 20 }
      : null;

  const { data: results, isLoading } = usePatentSearch(searchParams);

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (canSubmit) {
        setSubmitted(query.trim());
        setPage(1);
      }
    },
    [query, canSubmit]
  );

  const hasResults = results && results.items.length > 0;

  const placeholder =
    mode === "fulltext"
      ? "Search by title, abstract, or keywords..."
      : NL_PLACEHOLDERS[Math.floor(Math.random() * NL_PLACEHOLDERS.length)];

  return (
    <div>
      <PageHeader
        title="Search Patents"
        description="Find patents by keyword or describe the technology you're looking for."
        freshnessSources={["patents"]}
      />

      {/* Search bar */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              className="w-full rounded-lg border border-[var(--border-default)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={!canSubmit}
            className="px-6 py-3 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Search
          </button>
        </div>

        {/* Mode toggle */}
        <div className="mt-3 flex items-center gap-3 flex-wrap">
          <span className="text-xs text-[var(--text-muted)]">Search mode:</span>
          {(["hybrid", "semantic", "fulltext"] as SearchMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => {
                setMode(m);
                setSubmitted("");
              }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                mode === m
                  ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {m === "fulltext"
                ? "Keyword"
                : m === "semantic"
                  ? "Semantic"
                  : "Hybrid"}
            </button>
          ))}
          {mode === "hybrid" && (
            <span className="text-xs text-[var(--text-muted)]">
              Combines meaning, keywords &amp; recency — best for natural language
            </span>
          )}
          {mode === "semantic" && (
            <span className="text-xs text-[var(--text-muted)]">
              Finds patents by conceptual similarity
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
          <p className="text-[var(--text-muted)] mt-3">
            {mode === "fulltext"
              ? "Search patents by keyword — title, abstract, and claims text"
              : "Describe a technology, problem, or invention — semantic search understands meaning, not just keywords"}
          </p>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            {mode === "fulltext"
              ? "Minimum 3 characters"
              : "Natural language queries work best — try a full sentence"}
          </p>
          {mode !== "fulltext" && (
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {["battery thermal management", "CRISPR delivery vectors", "solid-state electrolyte", "autonomous drone navigation"].map(
                (example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => { setQuery(example); }}
                    className="px-3 py-1.5 rounded-full text-xs bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-glass)] border border-[var(--border-subtle)] transition-colors"
                  >
                    {example}
                  </button>
                )
              )}
            </div>
          )}
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <PatentCardSkeleton key={i} />
          ))}
        </div>
      ) : !hasResults ? (
        <EmptyState
          icon="search"
          title={`No patents found for "${submitted}"`}
          message={
            mode === "fulltext"
              ? "No patents matched your keywords. Try different terms or switch to semantic search for broader results."
              : mode === "semantic"
              ? "No patents were similar enough to your description. Try rephrasing or switching to keyword search."
              : "No patents matched across keyword and semantic indexes. Try a different query."
          }
          detail="Patent data is continuously ingested from USPTO, EPO, and WIPO. New records appear weekly."
          actions={[
            { label: `Try "${submitted}" as keyword search`, href: `?q=${encodeURIComponent(submitted)}&mode=fulltext`, primary: mode !== "fulltext" },
            { label: "Browse all patents", href: "/patents" },
            { label: "Explore by topic", href: "/themes" },
          ]}
        />
      ) : (
        <>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            {results!.total.toLocaleString()} results for &ldquo;{submitted}&rdquo;
            {mode !== "fulltext" && " · ranked by relevance"}
            {results!.pages > 1 && ` · page ${results!.page} of ${results!.pages}`}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {results!.items.map((patent) => (
              <div key={patent.id} className="relative">
                <PatentCard patent={patent} />
                {mode !== "fulltext" && patent.similarity != null && (
                  <div className="absolute top-2 right-2">
                    <Badge
                      variant="default"
                      size="sm"
                      className="bg-[var(--accent-muted)] text-[var(--type-foryou)] border-[var(--type-foryou)]/30"
                    >
                      {(patent.similarity * 100).toFixed(0)}% match
                    </Badge>
                  </div>
                )}
              </div>
            ))}
          </div>
          {results!.pages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} / {results!.pages}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= results!.pages}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      <div className="mt-8">
        <SourceAttribution />
      </div>
    </div>
  );
}
