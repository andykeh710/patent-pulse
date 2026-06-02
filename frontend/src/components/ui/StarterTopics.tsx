"use client";

import { useState } from "react";
import { topicsApi } from "@/lib/api";
import { STARTER_TOPICS, type StarterTopic } from "@/lib/starterTopics";
import { Badge } from "@/components/ui/Badge";

interface StarterTopicsProps {
  onCreated?: (name: string) => void;
  showHeading?: boolean;
}

export function StarterTopics({ onCreated, showHeading = true }: StarterTopicsProps) {
  const [creating, setCreating] = useState<string | null>(null);
  const [created, setCreated] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (topic: StarterTopic) => {
    setCreating(topic.name);
    setError(null);
    try {
      await topicsApi.create({
        name: topic.name,
        description: topic.description,
        cpc_prefixes: topic.cpc_prefixes,
        keywords: topic.keywords,
      });
      setCreated((prev) => new Set(prev).add(topic.name));
      onCreated?.(topic.name);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create topic";
      setError(msg);
    } finally {
      setCreating(null);
    }
  };

  return (
    <div>
      {showHeading && (
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
          Starter topics — one click to get started
        </h3>
      )}

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 text-red-400 text-sm border border-red-400/20">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {STARTER_TOPICS.map((topic) => {
          const isCreated = created.has(topic.name);
          const isLoading = creating === topic.name;

          return (
            <button
              key={topic.name}
              onClick={() => !isCreated && handleCreate(topic)}
              disabled={isCreated || isLoading}
              className={`text-left rounded-lg border p-4 transition-all ${
                isCreated
                  ? "border-[var(--score-high)]/30 bg-[var(--score-high)]/8 cursor-default"
                  : "border-[var(--border-subtle)] bg-[var(--bg-glass)] hover:border-[var(--accent)]/40 hover:shadow-[var(--shadow-sm)] cursor-pointer"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{topic.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-sm text-[var(--text-primary)]">{topic.name}</h4>
                    {isCreated && (
                      <Badge variant="success" size="sm">
                        created
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-1 line-clamp-2">{topic.description}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {topic.cpc_prefixes.map((cpc) => (
                      <span
                        key={cpc}
                        className="text-xs text-[var(--text-muted)] bg-[var(--bg-glass)] rounded px-1.5 py-0.5"
                      >
                        {cpc}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
