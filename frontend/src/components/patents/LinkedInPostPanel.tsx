"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { AISourceFooter } from "@/components/patents/AISourceFooter";
import { contentApi, patentsApi } from "@/lib/api";
import type { LinkedInPostResponse } from "@/lib/types";

interface LinkedInPostPanelProps {
  patentId: string;
}

const TONES = [
  { value: "analytical", label: "Analytical" },
  { value: "curiosity", label: "Curiosity Hook" },
  { value: "news", label: "News Update" },
] as const;

export function LinkedInPostPanel({ patentId }: LinkedInPostPanelProps) {
  const [artifact, setArtifact] = useState<LinkedInPostResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tone, setTone] = useState<string>("analytical");
  const [copied, setCopied] = useState(false);

  // Auto-load existing draft on mount
  const { data: existingDraft, isLoading: draftLoading } = useSWR(
    ["linkedin-draft", patentId],
    () => contentApi.getDraft(patentId),
    { revalidateOnFocus: false }
  );

  const handleGenerate = async () => {
    setError(null);
    try {
      const data = await patentsApi.generateLinkedInPost(patentId, tone);
      setArtifact(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate post");
    }
  };

  const [handleGenerateSafe, isGenerating] = useAsyncAction(handleGenerate);

  const handleCopy = async () => {
    const text = artifact?.post_markdown;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may not be available
    }
  };

  // --- Render: loading draft from server ---
  if (draftLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-3 text-gray-400">
          <Spinner size="sm" />
          <span className="text-sm">Loading saved draft...</span>
        </div>
      </div>
    );
  }

  // --- Render: existing draft from server (before any generation) ---
  if (!artifact && existingDraft?.post_markdown) {
    return (
      <DraftView
        postMarkdown={existingDraft.post_markdown}
        sourceCitation={existingDraft.source_citation}
        onGenerate={handleGenerateSafe}
        isGenerating={isGenerating}
        tone={tone}
        onToneChange={setTone}
        onCopy={handleCopy}
        copied={copied}
      />
    );
  }

  // --- Render: loading ---
  if (isGenerating) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-3 text-gray-500">
          <Spinner size="sm" />
          <span>Generating LinkedIn post...</span>
        </div>
      </div>
    );
  }

  // --- Render: error ---
  if (error && !artifact) {
    return (
      <div className="bg-white rounded-lg border border-red-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-2">LinkedIn Post</h2>
        <p className="text-sm text-red-600 mb-4">{error}</p>
        <Button onClick={handleGenerateSafe} variant="outline" size="sm">
          Retry
        </Button>
      </div>
    );
  }

  // --- Render: empty (no draft, no generation yet) ---
  if (!artifact) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-4">LinkedIn Post</h2>
        <p className="text-sm text-gray-500 mb-4">
          Generate a professional LinkedIn post about this patent — includes
          a compelling hook, key insights, and source citation.
        </p>

        {/* Tone selector */}
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            Tone
          </label>
          <div className="flex gap-2">
            {TONES.map((t) => (
              <button
                key={t.value}
                onClick={() => setTone(t.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  tone === t.value
                    ? "bg-primary-100 text-primary-700 border border-primary-300"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <Button onClick={handleGenerateSafe} variant="default" size="sm" disabled={isGenerating}>
          Generate LinkedIn Post
        </Button>
      </div>
    );
  }

  // --- Render: success (generated artifact) ---
  return (
    <SuccessView
      artifact={artifact}
      tone={tone}
      onToneChange={setTone}
      onGenerate={handleGenerateSafe}
      isGenerating={isGenerating}
      onCopy={handleCopy}
      copied={copied}
    />
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DraftView({
  postMarkdown,
  sourceCitation,
  onGenerate,
  isGenerating,
  tone,
  onToneChange,
  onCopy,
  copied,
}: {
  postMarkdown: string;
  sourceCitation: string;
  onGenerate: () => Promise<void>;
  isGenerating: boolean;
  tone: string;
  onToneChange: (t: string) => void;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900">LinkedIn Post</h2>
        <div className="flex items-center gap-2">
          <Button onClick={onCopy} variant="outline" size="sm">
            {copied ? "Copied!" : "Copy"}
          </Button>
          <Button onClick={onGenerate} variant="outline" size="sm" disabled={isGenerating}>
            {isGenerating ? "Generating..." : "Regenerate"}
          </Button>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
          {postMarkdown}
        </pre>
      </div>

      {sourceCitation && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
          {sourceCitation}
        </div>
      )}

      <AISourceFooter />

      <div className="mt-4 flex items-center gap-3">
        <label className="text-xs font-medium text-gray-500">Tone for regenerate:</label>
        <div className="flex gap-2">
          {TONES.map((t) => (
            <button
              key={t.value}
              onClick={() => onToneChange(t.value)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                tone === t.value
                  ? "bg-primary-100 text-primary-700 border border-primary-300"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SuccessView({
  artifact,
  tone,
  onToneChange,
  onGenerate,
  isGenerating,
  onCopy,
  copied,
}: {
  artifact: LinkedInPostResponse;
  tone: string;
  onToneChange: (t: string) => void;
  onGenerate: () => Promise<void>;
  isGenerating: boolean;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-gray-900">LinkedIn Post</h2>
          <span
            className={`text-xs font-medium px-2 py-1 rounded-full ${
              artifact.tone === "curiosity"
                ? "bg-purple-100 text-purple-700"
                : artifact.tone === "news"
                ? "bg-blue-100 text-blue-700"
                : "bg-green-100 text-green-700"
            }`}
          >
            {artifact.tone}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={onCopy} variant="outline" size="sm">
            {copied ? "Copied!" : "Copy"}
          </Button>
          <Button onClick={onGenerate} variant="outline" size="sm" disabled={isGenerating}>
            {isGenerating ? "Generating..." : "Regenerate"}
          </Button>
        </div>
      </div>

      {/* Hook */}
      {artifact.hook && (
        <p className="text-sm font-medium text-primary-700 mb-3 italic">
          &ldquo;{artifact.hook}&rdquo;
        </p>
      )}

      {/* Post body */}
      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
          {artifact.post_markdown}
        </pre>
      </div>

      {/* Source citation */}
      <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
        {artifact.source_citation}
      </div>

      <AISourceFooter />

      {/* Caveats */}
      {artifact.caveats.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Caveats
          </h3>
          <ul className="space-y-1">
            {artifact.caveats.map((cav, i) => (
              <li key={i} className="text-xs text-gray-500 flex items-start gap-2">
                <span>&bull;</span>
                {cav}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tone selector for regenerate */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-gray-500">Tone for regenerate:</label>
          <div className="flex gap-2">
            {TONES.map((t) => (
              <button
                key={t.value}
                onClick={() => onToneChange(t.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  tone === t.value
                    ? "bg-primary-100 text-primary-700 border border-primary-300"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
