"use client";

import { Suspense, useState, useCallback, useEffect, type FormEvent } from "react";
import { useSearchParams as useNextSearchParams, useRouter, usePathname } from "next/navigation";
import useSWR from "swr";
import { usePatentSearch } from "@/hooks/usePatents";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { FilterChips } from "@/components/ui/FilterChips";
import { PatentCard } from "@/components/patents/PatentCard";
import { SourceAttribution } from "@/components/ui/SourceAttribution";
import { savedSearchesApi } from "@/lib/api";
import type { SearchParams, SavedSearch } from "@/lib/types";

type SearchMode = "fulltext" | "semantic" | "hybrid";

const NL_PLACEHOLDERS = [
  "battery thermal management for electric vehicles",
  "CRISPR delivery vectors for gene therapy",
  "solid-state electrolyte manufacturing",
  "autonomous drone navigation in GPS-denied environments",
  "Explain what you're looking for...",
];

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "relevance", label: "Relevance" },
  { value: "publication_date", label: "Newest first" },
  { value: "publication_date_asc", label: "Oldest first" },
  { value: "estimated_expiry_date", label: "Expiring soonest" },
];

const STATUS_OPTIONS = [
  { value: "", label: "Any status" },
  { value: "GRANTED", label: "Granted" },
  { value: "PUBLISHED", label: "Published" },
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

  // Parse URL state
  const [query, setQuery] = useState(urlParams.get("q") || "");
  const [submitted, setSubmitted] = useState(urlParams.get("q") || "");
  const [mode, setMode] = useState<SearchMode>(
    (urlParams.get("mode") as SearchMode) || "hybrid"
  );
  const [legalStatus, setLegalStatus] = useState(urlParams.get("legal_status") || "");
  const [sortBy, setSortBy] = useState(urlParams.get("sort_by") || "relevance");
  const [sortOrder, setSortOrder] = useState(urlParams.get("sort_order") || "desc");
  const [page, setPage] = useState(
    urlParams.get("page") ? Number(urlParams.get("page")) : 1
  );

  // Saved searches
  const { data: savedSearches, mutate: mutateSaved } = useSWR(
    "saved-searches",
    () => savedSearchesApi.list(),
    { revalidateOnFocus: false }
  );
  const [savingSearch, setSavingSearch] = useState(false);
  const [saveName, setSaveName] = useState("");

  // Sync to URL
  useEffect(() => {
    const sp = new URLSearchParams();
    if (submitted) sp.set("q", submitted);
    if (mode !== "hybrid") sp.set("mode", mode);
    if (legalStatus) sp.set("legal_status", legalStatus);
    if (sortBy !== "relevance") sp.set("sort_by", sortBy);
    if (sortOrder !== "desc") sp.set("sort_order", sortOrder);
    if (page > 1) sp.set("page", String(page));
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [submitted, mode, legalStatus, sortBy, sortOrder, page, pathname, router]);

  // Build search params
  const minChars = mode === "fulltext" ? 3 : 1;
  const canSubmit = query.trim().length >= minChars;

  const searchParams: SearchParams | null =
    submitted.length >= minChars
      ? {
          q: submitted,
          mode,
          legal_status: legalStatus || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          page,
          page_size: 20,
        }
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

  // Build filter chips
  const chips: { key: string; label: string; onRemove: () => void }[] = [];
  if (legalStatus) {
    chips.push({
      key: "legal",
      label: `Status: ${legalStatus}`,
      onRemove: () => setLegalStatus(""),
    });
  }
  if (sortBy !== "relevance") {
    const opt = SORT_OPTIONS.find((o) => o.value === sortBy);
    if (opt) chips.push({ key: "sort", label: `Sort: ${opt.label}`, onRemove: () => { setSortBy("relevance"); setSortOrder("desc"); } });
  }

  // Handle save/unsave
  const handleSaveSearch = async () => {
    const name = saveName.trim() || submitted.slice(0, 40);
    setSavingSearch(true);
    try {
      await savedSearchesApi.create({
        name,
        query: submitted,
        mode,
        filters_json: legalStatus ? { legal_status: legalStatus } : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      setSaveName("");
      mutateSaved();
    } finally {
      setSavingSearch(false);
    }
  };

  const handleDeleteSaved = async (id: string) => {
    await savedSearchesApi.delete(id);
    mutateSaved();
  };

  const handleOpenSaved = (s: SavedSearch) => {
    setQuery(s.query);
    setSubmitted(s.query);
    setMode(s.mode as SearchMode);
    setLegalStatus((s.filters_json?.legal_status as string) || "");
    setSortBy(s.sort_by);
    setSortOrder(s.sort_order);
    setPage(1);
  };

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
      <form onSubmit={handleSubmit} className="mb-4">
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
            className="px-6 py-3 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Search
          </button>
        </div>

        {/* Mode + Filters row */}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span className="text-xs text-[var(--text-muted)]">Mode:</span>
          {(["hybrid", "semantic", "fulltext"] as SearchMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setSubmitted(""); }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                mode === m
                  ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                  : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {m === "fulltext" ? "Keyword" : m === "semantic" ? "Semantic" : "Hybrid"}
            </button>
          ))}

          <span className="text-xs text-[var(--text-muted)] ml-2">Status:</span>
          <select
            value={legalStatus}
            onChange={(e) => setLegalStatus(e.target.value)}
            className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <span className="text-xs text-[var(--text-muted)] ml-2">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "publication_date_asc") { setSortBy("publication_date"); setSortOrder("asc"); }
              else { setSortBy(v); setSortOrder("desc"); }
            }}
            className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          >
            <option value="relevance">Relevance</option>
            <option value="publication_date">Newest first</option>
            <option value="publication_date_asc">Oldest first</option>
            <option value="estimated_expiry_date">Expiring soonest</option>
          </select>
        </div>

        {/* Filter chips */}
        {chips.length > 0 && (
          <div className="mt-2">
            <FilterChips chips={chips} onClearAll={() => { setLegalStatus(""); setSortBy("relevance"); setSortOrder("desc"); }} />
          </div>
        )}
      </form>

      {/* Results */}
      {!submitted ? (
        <div>
          <div className="rounded-lg bg-[var(--bg-base)] py-16 text-center mb-6">
            <svg className="mx-auto h-12 w-12 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-[var(--text-muted)] mt-3">
              {mode === "fulltext"
                ? "Search patents by keyword — title, abstract, and claims text"
                : "Describe a technology, problem, or invention — semantic search understands meaning, not just keywords"}
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

          {/* Saved searches */}
          {savedSearches && savedSearches.items.length > 0 && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-5">
              <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Saved Searches</h2>
              <div className="space-y-2">
                {savedSearches.items.map((s) => (
                  <div key={s.id} className="flex items-center justify-between gap-3 p-2 rounded hover:bg-[var(--bg-base)] transition-colors">
                    <button
                      onClick={() => handleOpenSaved(s)}
                      className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)] text-left flex-1 min-w-0"
                    >
                      <span className="truncate block">{s.name}</span>
                      <span className="text-xs text-[var(--text-muted)] block truncate">
                        &ldquo;{s.query}&rdquo; · {s.mode}
                      </span>
                    </button>
                    <button
                      onClick={() => handleDeleteSaved(s.id)}
                      className="text-xs text-[var(--text-muted)] hover:text-[var(--expiry-lapsed-confirmed)] shrink-0"
                      title="Delete saved search"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : isLoading ? (
        <LoadingState variant="card" count={6} />
      ) : !hasResults ? (
        <EmptyState
          icon="search"
          title={`No patents found for "${submitted}"`}
          message={
            mode === "fulltext"
              ? "No patents matched your keywords. Try different terms or switch to semantic search."
              : mode === "semantic"
              ? "No patents were similar enough to your description. Try rephrasing or switching to keyword search."
              : "No patents matched across keyword and semantic indexes."
          }
          detail={legalStatus ? "Try removing the status filter to broaden results." : "Patent data is continuously ingested. New records appear weekly."}
          actions={[
            ...(legalStatus ? [{ label: "Remove status filter", onClick: () => setLegalStatus(""), primary: true }] : []),
            { label: `Try "${submitted}" as keyword search`, href: `?q=${encodeURIComponent(submitted)}&mode=fulltext`, primary: mode !== "fulltext" && !legalStatus },
            { label: "Browse all patents", href: "/patents" },
            { label: "Explore by topic", href: "/themes" },
          ]}
        />
      ) : (
        <div>
          {/* Result header */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-[var(--text-muted)]">
              {results!.total.toLocaleString()} results for &ldquo;{submitted}&rdquo;
              {mode !== "fulltext" && " · ranked by relevance"}
              {results!.pages > 1 && ` · page ${results!.page} of ${results!.pages}`}
            </p>
            {/* Save search button */}
            {submitted && (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="Save search as..."
                  className="text-xs rounded border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1 w-32 focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                />
                <button
                  onClick={handleSaveSearch}
                  disabled={savingSearch}
                  className="text-xs px-3 py-1 rounded bg-[var(--accent-muted)] text-[var(--accent)] hover:bg-[var(--accent)]/20 disabled:opacity-50 transition-colors"
                >
                  {savingSearch ? "Saving..." : "Save"}
                </button>
              </div>
            )}
          </div>

          {/* Result cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {results!.items.map((patent) => (
              <PatentCard key={patent.id} patent={patent} />
            ))}
          </div>

          {/* Pagination */}
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
        </div>
      )}

      <div className="mt-8">
        <SourceAttribution />
      </div>
    </div>
  );
}
