"use client";

import ReactMarkdown from "react-markdown";
import type { ChatMessage as ChatMessageType } from "@/hooks/useChatStream";
import { ToolCallCard } from "./ToolCallCard";
import { SourcesPanel } from "./SourcesPanel";

// ── Citation badge ────────────────────────────────────────────────────

function CitationBadge({
  docId,
  verified,
}: {
  docId: string;
  verified: boolean;
}) {
  return (
    <a
      href={`/patents?q=${encodeURIComponent(docId)}`}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono no-underline transition-colors ${
        verified
          ? "bg-[var(--accent-muted)] text-[var(--accent)] hover:bg-[var(--accent)]/20"
          : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/30 hover:bg-yellow-500/20"
      }`}
      title={
        verified
          ? "Verified citation"
          : "Reference could not be verified against retrieved sources"
      }
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          verified ? "bg-[var(--accent)]" : "bg-yellow-500"
        }`}
      />
      {docId}
    </a>
  );
}

// ── Citation-aware markdown renderer ──────────────────────────────────

const CITATION_RE = /\[((?:USPTO|EPO|WIPO):[A-Z0-9_/-]+)\]/g;

function renderWithCitations(
  content: string,
  verifiedIds: string[],
  unverifiedIds: string[]
) {
  const verified = new Set(verifiedIds);
  const all = new Set([...verifiedIds, ...unverifiedIds]);

  if (all.size === 0) {
    return <ReactMarkdown>{content}</ReactMarkdown>;
  }

  // Split content by citation markers and interleave badges
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  const regex = new RegExp(CITATION_RE.source, "g");
  let key = 0;

  while ((match = regex.exec(content)) !== null) {
    // Text before this citation
    if (match.index > lastIndex) {
      parts.push(
        <ReactMarkdown key={key++}>
          {content.slice(lastIndex, match.index)}
        </ReactMarkdown>
      );
    }
    // Citation badge
    const docId = match[1];
    parts.push(
      <CitationBadge
        key={key++}
        docId={docId}
        verified={verified.has(docId)}
      />
    );
    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  if (lastIndex < content.length) {
    parts.push(
      <ReactMarkdown key={key++}>{content.slice(lastIndex)}</ReactMarkdown>
    );
  }

  return <>{parts}</>;
}

// ── Component ─────────────────────────────────────────────────────────

export function ChatMessage({
  message,
}: {
  message: ChatMessageType;
}) {
  const isUser = message.role === "user";
  const verified = message.citations?.verified || [];
  const unverified = message.citations?.unverified || [];

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[85%] md:max-w-[70%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-[var(--accent)] text-white"
            : "bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)]"
        }`}
      >
        {/* User message — plain text */}
        {isUser && <p className="text-sm whitespace-pre-wrap">{message.content}</p>}

        {/* Assistant message — markdown + citations */}
        {!isUser && (
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1">
            {renderWithCitations(message.content, verified, unverified)}
          </div>
        )}

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.toolCalls.map((tc, i) => (
              <ToolCallCard key={i} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Streaming indicator */}
        {message.isStreaming && !message.content && !message.toolCalls?.length && (
          <div className="flex items-center gap-2 text-[var(--text-muted)]">
            <span className="inline-block w-2 h-2 bg-[var(--accent)] rounded-full animate-pulse" />
            <span className="text-xs">Thinking...</span>
          </div>
        )}

        {/* Sources panel */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3">
            <SourcesPanel patents={message.sources} />
          </div>
        )}
      </div>
    </div>
  );
}
