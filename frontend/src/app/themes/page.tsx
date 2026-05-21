"use client";

import { useState } from "react";
import Link from "next/link";
import { useThemes, useThemePatents } from "@/hooks/useThemes";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Theme } from "@/lib/types";

export default function ThemesPage() {
  const { data: themes, isLoading } = useThemes();
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data: patents, isLoading: patentsLoading } = useThemePatents(
    selectedTheme,
    page,
    12
  );

  const selected = themes?.find((t) => t.id === selectedTheme);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Technology Themes</h1>
        <p className="text-gray-600 mt-1">
          Tracked technology areas and their matched patents
        </p>
      </div>

      {/* Theme cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-lg" />
          ))}
        </div>
      ) : !themes || themes.length === 0 ? (
        <div className="rounded-lg bg-gray-50 py-12 text-center mb-6">
          <p className="text-gray-500">No themes configured yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Seed default themes via{" "}
            <Link href="/admin/ai-runs" className="text-primary-600 hover:underline">
              Admin
            </Link>
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
          {themes.map((theme) => (
            <ThemeCard
              key={theme.id}
              theme={theme}
              isSelected={selectedTheme === theme.id}
              onClick={() => {
                setSelectedTheme(selectedTheme === theme.id ? null : theme.id);
                setPage(1);
              }}
            />
          ))}
        </div>
      )}

      {/* Selected theme patents */}
      {selectedTheme && selected && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {selected.name} — Matched Patents
              </h2>
              {patents && (
                <p className="text-sm text-gray-500">
                  {patents.total} {patents.total === 1 ? "patent" : "patents"} matched
                </p>
              )}
            </div>
            <button
              onClick={() => setSelectedTheme(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear selection
            </button>
          </div>

          {patentsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <PatentCardSkeleton key={i} />
              ))}
            </div>
          ) : patents && patents.items.length > 0 ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {patents.items.map((patent) => (
                  <PatentCard key={patent.id} patent={patent} />
                ))}
              </div>

              {patents.pages > 1 && (
                <div className="mt-4 flex items-center justify-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {page} of {patents.pages}
                  </span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= patents.pages}
                    className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-lg bg-gray-50 py-8 text-center text-gray-500">
              No patents matched this theme yet. Run theme matching via Admin.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ThemeCard({
  theme,
  isSelected,
  onClick,
}: {
  theme: Theme;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left rounded-lg border p-4 transition-all ${
        isSelected
          ? "border-primary-400 bg-primary-50 shadow-sm"
          : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-gray-900">{theme.name}</h3>
        {!theme.is_active && (
          <Badge variant="default" size="sm" className="text-gray-400">
            inactive
          </Badge>
        )}
      </div>
      {theme.description && (
        <p className="text-sm text-gray-600 mt-1 line-clamp-2">{theme.description}</p>
      )}
      <div className="flex flex-wrap gap-1 mt-2">
        {theme.cpc_prefixes.slice(0, 4).map((cpc) => (
          <Badge key={cpc} variant="default" size="sm">
            {cpc}
          </Badge>
        ))}
        {theme.cpc_prefixes.length > 4 && (
          <span className="text-xs text-gray-400">+{theme.cpc_prefixes.length - 4}</span>
        )}
      </div>
    </button>
  );
}
