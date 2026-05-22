"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import useSWR from "swr";
import { useThemes, useThemePatents } from "@/hooks/useThemes";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { topicsApi } from "@/lib/api";
import type { Topic } from "@/lib/types";

export default function ThemesPage() {
  const { data: themes, isLoading, mutate } = useThemes();
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Create form state
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formCpc, setFormCpc] = useState("");
  const [formKeywords, setFormKeywords] = useState("");

  const { data: patents, isLoading: patentsLoading } = useThemePatents(
    selectedTheme,
    page,
    12
  );

  const selected = themes?.find((t) => t.id === selectedTheme);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;
    setCreating(true);
    try {
      await topicsApi.create({
        name: formName.trim(),
        description: formDescription.trim() || undefined,
        cpc_prefixes: formCpc
          ? formCpc.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        keywords: formKeywords
          ? formKeywords.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
      });
      setShowCreate(false);
      setFormName("");
      setFormDescription("");
      setFormCpc("");
      setFormKeywords("");
      mutate();
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this topic? Its matches will also be deleted.")) return;
    setDeleting(id);
    try {
      await topicsApi.delete(id);
      if (selectedTheme === id) setSelectedTheme(null);
      mutate();
    } finally {
      setDeleting(null);
    }
  };

  // Separate system themes (CPC sections, no user_id) from user topics
  const systemThemes = themes?.filter((t) => !t.user_id) || [];
  const userTopics = themes?.filter((t) => t.user_id) || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Topics</h1>
          <p className="text-gray-600 mt-1">
            Tracked technology areas and their matched patents
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)} variant="default" size="sm">
          {showCreate ? "Cancel" : "Create Topic"}
        </Button>
      </div>

      {/* Create Topic Form */}
      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="mb-6 bg-white rounded-lg border border-primary-200 p-6"
        >
          <h2 className="font-semibold text-gray-900 mb-4">New Topic</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text"
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder='e.g. "AI Agents & LLMs"'
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="What this topic tracks"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CPC Prefixes <span className="text-gray-400 text-xs">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={formCpc}
                onChange={(e) => setFormCpc(e.target.value)}
                placeholder="G06N, G06F, H04L"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Keywords <span className="text-gray-400 text-xs">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={formKeywords}
                onChange={(e) => setFormKeywords(e.target.value)}
                placeholder="agent, LLM, autonomous, reasoning"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button type="submit" variant="default" size="sm" disabled={creating || !formName.trim()}>
              {creating ? "Creating..." : "Create Topic"}
            </Button>
            <p className="text-xs text-gray-400">
              After creation, run theme matching via Admin → AI Runs to populate matches.
            </p>
          </div>
        </form>
      )}

      {/* System Themes section */}
      {systemThemes.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            System Themes
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {systemThemes.map((theme) => (
              <ThemeCard
                key={theme.id}
                theme={theme}
                isSelected={selectedTheme === theme.id}
                isSystem
                onClick={() => {
                  setSelectedTheme(selectedTheme === theme.id ? null : theme.id);
                  setPage(1);
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* User Topics section */}
      {userTopics.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Your Topics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {userTopics.map((topic) => (
              <ThemeCard
                key={topic.id}
                theme={topic}
                isSelected={selectedTheme === topic.id}
                isSystem={false}
                onDelete={() => handleDelete(topic.id)}
                isDeleting={deleting === topic.id}
                onClick={() => {
                  setSelectedTheme(selectedTheme === topic.id ? null : topic.id);
                  setPage(1);
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Loading / empty state */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-lg" />
          ))}
        </div>
      ) : !themes || themes.length === 0 ? (
        <div className="rounded-lg bg-gray-50 py-12 text-center mb-6">
          <p className="text-gray-500">No topics configured yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Create a topic above or seed defaults via{" "}
            <Link href="/admin/ai-runs" className="text-primary-600 hover:underline">
              Admin
            </Link>
          </p>
        </div>
      ) : null}

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
              No patents matched this topic yet. Run theme matching via Admin.
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
  isSystem,
  onDelete,
  isDeleting,
  onClick,
}: {
  theme: Topic;
  isSelected: boolean;
  isSystem: boolean;
  onDelete?: () => void;
  isDeleting?: boolean;
  onClick: () => void;
}) {
  const tagColor = theme.opportunity_tags?.length
    ? "bg-green-100 text-green-800"
    : "bg-blue-100 text-blue-800";

  return (
    <div
      className={`rounded-lg border p-4 transition-all ${
        isSelected
          ? "border-primary-400 bg-primary-50 shadow-sm"
          : isSystem
          ? "border-gray-200 bg-gray-50"
          : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
      }`}
    >
      <button onClick={onClick} className="w-full text-left">
        <div className="flex items-start justify-between">
          <h3 className="font-semibold text-gray-900 text-sm">{theme.name}</h3>
          <div className="flex items-center gap-1">
            {!theme.is_active && (
              <Badge variant="default" size="sm" className="text-gray-400">
                inactive
              </Badge>
            )}
            {isSystem ? (
              <Badge variant="default" size="sm" className="bg-blue-100 text-blue-800">
                system
              </Badge>
            ) : (
              <Badge variant="default" size="sm" className={tagColor}>
                topic
              </Badge>
            )}
          </div>
        </div>
        {theme.description && (
          <p className="text-xs text-gray-600 mt-1 line-clamp-2">{theme.description}</p>
        )}
      </button>

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

      {theme.keywords && theme.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {theme.keywords.slice(0, 3).map((kw) => (
            <span key={kw} className="text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5">
              {kw}
            </span>
          ))}
          {theme.keywords.length > 3 && (
            <span className="text-xs text-gray-400">+{theme.keywords.length - 3}</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-gray-500">
          {theme.patent_count} {theme.patent_count === 1 ? "patent" : "patents"}
        </span>
        {!isSystem && onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            disabled={isDeleting}
            className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        )}
      </div>
    </div>
  );
}
