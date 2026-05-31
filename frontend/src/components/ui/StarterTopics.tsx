"use client";

import { useState } from "react";
import { topicsApi } from "@/lib/api";
import { STARTER_TOPICS, type StarterTopic } from "@/lib/starterTopics";
import { Badge } from "@/components/ui/Badge";

interface StarterTopicsProps {
  onCreated?: (name: string) => void;
  /** If true, show a heading. Default true. */
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
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Starter topics — one click to get started
        </h3>
      )}

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
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
                  ? "border-green-300 bg-green-50 cursor-default"
                  : "border-gray-200 bg-white hover:border-primary-300 hover:shadow-sm cursor-pointer"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{topic.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-sm text-gray-900">{topic.name}</h4>
                    {isCreated && (
                      <Badge variant="default" size="sm" className="bg-green-100 text-green-700">
                        created
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{topic.description}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {topic.cpc_prefixes.map((cpc) => (
                      <span
                        key={cpc}
                        className="text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5"
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
