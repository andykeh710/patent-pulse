"use client";

import Link from "next/link";

export interface Suggestion {
  companies: { normalized_name: string; display_name: string; patent_count: number }[];
  themes: { id: string; name: string; description: string | null }[];
}

export function StepConfirm({
  suggestions,
  onRemoveCompany,
  onRemoveTheme,
}: {
  suggestions: Suggestion | null;
  onRemoveCompany: (name: string) => void;
  onRemoveTheme: (id: string) => void;
}) {
  if (!suggestions) return null;

  return (
    <div>
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
        We built a starter feed for you.
      </h2>
      <p className="text-sm text-[var(--text-muted)] mb-4">
        Edit anything before continuing.
      </p>

      {suggestions.companies.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Followed companies</h3>
          <div className="space-y-1">
            {suggestions.companies.map((c) => (
              <div key={c.normalized_name} className="flex items-center justify-between px-3 py-1.5 rounded bg-[var(--bg-elevated)] text-sm">
                <span className="text-[var(--text-primary)]">{c.display_name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[var(--text-muted)]">{c.patent_count} patents</span>
                  <button
                    type="button"
                    onClick={() => onRemoveCompany(c.normalized_name)}
                    className="text-[var(--text-muted)] hover:text-red-400 text-xs"
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {suggestions.themes.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Suggested themes</h3>
          <div className="space-y-1">
            {suggestions.themes.map((t) => (
              <div key={t.id} className="flex items-center justify-between px-3 py-1.5 rounded bg-[var(--bg-elevated)] text-sm">
                <div>
                  <span className="text-[var(--text-primary)]">{t.name}</span>
                  {t.description && <span className="text-xs text-[var(--text-muted)] ml-2">{t.description}</span>}
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveTheme(t.id)}
                  className="text-[var(--text-muted)] hover:text-red-400 text-xs"
                  title="Remove"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {suggestions.companies.length === 0 && suggestions.themes.length === 0 && (
        <p className="text-sm text-[var(--text-muted)] mb-4">
          No specific suggestions available yet. You can browse after setup.
        </p>
      )}

      <div className="flex gap-4 mt-2">
        <Link href="/companies" className="text-xs text-[var(--accent)] hover:underline">
          Browse more companies →
        </Link>
        <Link href="/themes" className="text-xs text-[var(--accent)] hover:underline">
          Browse more themes →
        </Link>
      </div>
    </div>
  );
}
