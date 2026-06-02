"use client";

import { useState, type FormEvent } from "react";
import { useThemes, useThemePatents } from "@/hooks/useThemes";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { StarterTopics } from "@/components/ui/StarterTopics";
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
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Topics</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Tracked technology areas and their matched patents
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)} variant="default">
          {showCreate ? "Cancel" : "Create Topic"}
        </Button>
      </div>

      {/* Create Topic Form */}
      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="mb-6 bg-[var(--bg-surface)] rounded-lg border border-border-[var(--accent)]/20 p-6"
        >
          <h2 className="font-semibold text-[var(--text-primary)] mb-4">New Topic</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Name *</label>
              <input
                type="text"
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder='e.g. "AI Agents & LLMs"'
                className="w-full rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Description</label>
              <input
                type="text"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="What this topic tracks"
                className="w-full rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                CPC Prefixes <span className="text-[var(--text-muted)] text-xs">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={formCpc}
                onChange={(e) => setFormCpc(e.target.value)}
                placeholder="G06N, G06F, H04L"
                className="w-full rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Keywords <span className="text-[var(--text-muted)] text-xs">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={formKeywords}
                onChange={(e) => setFormKeywords(e.target.value)}
                placeholder="agent, LLM, autonomous, reasoning"
                className="w-full rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button type="submit" variant="default" disabled={creating || !formName.trim()}>
              {creating ? "Creating..." : "Create Topic"}
            </Button>
            <p className="text-xs text-[var(--text-muted)]">
              After creation, run theme matching via Admin → AI Runs to populate matches.
            </p>
          </div>
        </form>
      )}

      {/* System Themes section */}
      {systemThemes.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-3">
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
          <h2 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-3">
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
        <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] p-8 text-center mb-6">
          <div className="max-w-md mx-auto">
            <div className="text-3xl mb-3">🔬</div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Your patent intelligence starts here
            </h2>
            <p className="text-sm text-[var(--text-muted)] mb-6">
              Choose a starter topic below or create your own. When new patents match
              your topics, they&apos;ll appear here automatically.
            </p>
            <StarterTopics
              showHeading={false}
              onCreated={() => mutate()}
            />
            <div className="mt-6 pt-6 border-t border-[var(--border-subtle)]">
              <Button
                onClick={() => setShowCreate(true)}
                variant="default"
              >
                Or create your own topic
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Selected theme patents */}
      {selectedTheme && selected && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">
                {selected.name} — Matched Patents
              </h2>
              {patents && (
                <p className="text-sm text-[var(--text-muted)]">
                  {patents.total} {patents.total === 1 ? "patent" : "patents"} matched
                </p>
              )}
            </div>
            <button
              onClick={() => setSelectedTheme(null)}
              className="text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
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
                    className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-[var(--text-secondary)]">
                    Page {page} of {patents.pages}
                  </span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= patents.pages}
                    className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-glass)]"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-lg bg-[var(--bg-base)] py-8 text-center text-[var(--text-muted)]">
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
    ? "bg-[var(--score-high-bg)] text-[var(--score-high)]"
    : "bg-[var(--accent-muted)] text-[var(--accent)]";

  return (
    <div
      className={`rounded-lg border p-4 transition-all ${
        isSelected
          ? "border-bg-[var(--accent)]/70 bg-[var(--bg-elevated)] shadow-sm"
          : isSystem
          ? "border-[var(--border-subtle)] bg-[var(--bg-base)]"
          : "border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--border-default)] hover:shadow-sm"
      }`}
    >
      <button onClick={onClick} className="w-full text-left">
        <div className="flex items-start justify-between">
          <h3 className="font-semibold text-[var(--text-primary)] text-sm">{theme.name}</h3>
          <div className="flex items-center gap-1">
            {!theme.is_active && (
              <Badge variant="default" size="sm" className="text-[var(--text-muted)]">
                inactive
              </Badge>
            )}
            {isSystem ? (
              <Badge variant="default" size="sm" className="bg-[var(--accent-muted)] text-[var(--accent)]">
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
          <p className="text-xs text-[var(--text-secondary)] mt-1 line-clamp-2">{theme.description}</p>
        )}
      </button>

      <div className="flex flex-wrap gap-1 mt-2">
        {theme.cpc_prefixes.slice(0, 4).map((cpc) => (
          <Badge key={cpc} variant="default" size="sm">
            {cpc}
          </Badge>
        ))}
        {theme.cpc_prefixes.length > 4 && (
          <span className="text-xs text-[var(--text-muted)]">+{theme.cpc_prefixes.length - 4}</span>
        )}
      </div>

      {theme.keywords && theme.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {theme.keywords.slice(0, 3).map((kw) => (
            <span key={kw} className="text-xs text-[var(--text-muted)] bg-[var(--bg-elevated)] rounded px-1.5 py-0.5">
              {kw}
            </span>
          ))}
          {theme.keywords.length > 3 && (
            <span className="text-xs text-[var(--text-muted)]">+{theme.keywords.length - 3}</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-[var(--text-muted)]">
          {theme.patent_count} {theme.patent_count === 1 ? "patent" : "patents"}
        </span>
        {!isSystem && onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            disabled={isDeleting}
            className="text-xs text-[var(--expiry-lapsed-confirmed)] hover:opacity-80 disabled:opacity-50 transition-opacity"
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        )}
      </div>
    </div>
  );
}
