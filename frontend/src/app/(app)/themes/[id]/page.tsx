"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { themesApi } from "@/lib/api";
import { SubscribePanel } from "@/components/topics/SubscribePanel";
import type { Topic, PaginatedResponse, PatentListItem } from "@/lib/types";

export default function ThemeDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: themes, isLoading, error } = useSWR<Topic[]>(
    ["themes"],
    () => themesApi.list()
  );

  const theme = themes?.find((t) => t.id === id);

  const { data: patents } = useSWR(
    id ? ["theme-patents", id, 1] : null,
    () => themesApi.getPatents(id, { page: 1, page_size: 10 })
  );

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-[var(--bg-surface)] rounded w-64" />
        <div className="h-4 bg-[var(--bg-surface)] rounded w-96" />
        <div className="h-40 bg-[var(--bg-surface)] rounded" />
      </div>
    );
  }

  if (error || !theme) {
    return (
      <div className="text-center py-12 text-[var(--text-muted)]">
        <p>Topic not found.</p>
        <Link href="/themes" className="text-sm text-[var(--accent)] hover:underline mt-2 inline-block">
          Browse all topics
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link href="/themes" className="text-sm text-[var(--accent)] hover:underline">
        ← All Topics
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{theme.name}</h1>
        {theme.description && (
          <p className="text-[var(--text-secondary)] mt-1">{theme.description}</p>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {theme.cpc_prefixes?.map((c) => (
          <span key={c} className="px-2 py-0.5 bg-blue-50 text-[var(--accent)] rounded text-xs">
            CPC: {c}
          </span>
        ))}
        {theme.keywords?.map((k) => (
          <span key={k} className="px-2 py-0.5 bg-[var(--bg-elevated)] text-[var(--text-secondary)] rounded text-xs">
            {k}
          </span>
        ))}
        {theme.min_opportunity_score != null && (
          <span className="px-2 py-0.5 bg-[var(--score-medium-bg)] text-[var(--score-medium)] rounded text-xs">
            Min score: {theme.min_opportunity_score}
          </span>
        )}
      </div>

      <SubscribePanel theme={theme} />

      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Recent Matching Patents</h2>
        {patents?.items?.length ? (
          <div className="space-y-2">
            {patents.items.map((p: PatentListItem) => (
              <Link
                key={p.id}
                href={`/patents/${p.id}`}
                className="block border border-[var(--border-subtle)] rounded-lg p-3 hover:border-blue-300 transition-colors"
              >
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {p.title || p.doc_id}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {(p.assignees || [])[0]} · {p.doc_id}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">
            Match history coming soon — theme matching runs weekly.
          </p>
        )}
      </div>
    </div>
  );
}
