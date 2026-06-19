"use client";

import { useState } from "react";
import Link from "next/link";
import { preferencesApi } from "@/lib/api";

export interface FeedItemType {
  id: string;
  object_type: string;
  object_id: string;
  feed_type: string;
  title: string;
  summary: string;
  why_this: string;
  why_now: string;
  why_for_user: string;
  evidence: Record<string, unknown>;
  confidence: string;
  source_date: string | null;
  related_patents: string[];
  related_companies: string[];
  related_topics: string[];
  primary_action: { type: string; label: string; target_id: string } | null;
  secondary_action: { type: string; label: string; target_id: string } | null;
  rank_score: number;
  seen_state: string;
  feedback_state: string;
  created_at: string;
}

const FEED_TYPE_LABELS: Record<string, string> = {
  expiry_opportunity: "Expiry Opportunity",
  high_opportunity_patent: "High Opportunity",
  followed_company_signal: "Company Signal",
  company_new_patents: "Company Activity",
  topic_new_patents: "Topic Signal",
  similar_topic_patent: "Related Patent",
  fresh_ingestion_summary: "Data Freshness",
  recommended_action: "Recommended",
  filing_trend: "Filing Trend",
  notable_patent: "Notable Patent",
};

interface Props {
  item: FeedItemType;
  onHide?: (id: string) => void;
  onFeedback?: (id: string, type: "useful" | "not_useful") => void;
}

export function ForYouCard({ item, onHide, onFeedback }: Props) {
  const [hidden, setHidden] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (hidden) return null;

  const handleHide = async () => {
    setSaving(true);
    try {
      await preferencesApi.hideItem(item.object_type, item.object_id);
      setHidden(true);
      onHide?.(item.id);
    } catch {
      setSaving(false);
    }
  };

  const handleFeedback = async (type: "useful" | "not_useful") => {
    if (feedback) return;
    setSaving(true);
    try {
      await fetch("/api/v1/me/feed/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          object_type: item.object_type,
          object_id: item.object_id,
          feedback_type: type,
        }),
      });
      setFeedback(type);
      onFeedback?.(item.id, type);
    } catch {
      setSaving(false);
    }
  };

  const typeLabel = FEED_TYPE_LABELS[item.feed_type] || item.feed_type;
  const confidenceColor =
    item.confidence === "high"
      ? "bg-green-500/20 text-green-700 dark:text-green-400"
      : item.confidence === "low" || item.confidence === "estimated"
        ? "bg-amber-500/20 text-amber-700 dark:text-amber-400"
        : "bg-blue-500/20 text-blue-700 dark:text-blue-400";

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 hover:border-[var(--text-muted)]/30 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              {typeLabel}
            </span>
            {item.confidence && (
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${confidenceColor}`}
              >
                {item.confidence}
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)] leading-snug">
            {item.title}
          </h3>
        </div>
        {item.rank_score > 0 && (
          <span className="text-[10px] text-[var(--text-muted)] tabular-nums shrink-0">
            #{item.rank_score}
          </span>
        )}
      </div>

      {/* Summary */}
      {item.summary && (
        <p className="text-sm text-[var(--text-secondary)] mb-3 line-clamp-2">
          {item.summary}
        </p>
      )}

      {/* Why shown */}
      <WhyShown item={item} />

      {/* Evidence */}
      {Object.keys(item.evidence || {}).length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            {Object.entries(item.evidence)
              .filter(([, v]) => v != null)
              .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
              .join(" · ")}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] flex items-center gap-2 flex-wrap">
        {item.object_type === "patent" && (
          <CardAction
            label="Save"
            onClick={() => {
              fetch("/api/v1/watchlist", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ patent_id: item.object_id }),
              }).catch(() => {});
            }}
          />
        )}
        {item.related_topics?.map((t) => (
          <Link
            key={t}
            href="/themes"
            className="text-[11px] text-[var(--accent)] hover:underline"
          >
            {t}
          </Link>
        ))}
        {item.related_companies?.map((c) => (
          <CardAction
            key={c}
            label={`Follow ${c.slice(0, 20)}`}
            onClick={() => {
              fetch(`/api/v1/suppliers/follow/${encodeURIComponent(c)}`, {
                method: "POST",
                credentials: "include",
              }).catch(() => {});
            }}
          />
        ))}

        <div className="flex-1" />

        {!feedback && (
          <>
            <CardAction
              label="Useful"
              variant="positive"
              onClick={() => handleFeedback("useful")}
              disabled={saving}
            />
            <CardAction
              label="Not useful"
              variant="negative"
              onClick={() => handleFeedback("not_useful")}
              disabled={saving}
            />
          </>
        )}
        {feedback && (
          <span className="text-[11px] text-[var(--text-muted)]">
            {feedback === "useful" ? "✓ Marked useful" : "✗ Marked not useful"}
          </span>
        )}
        <CardAction label="Hide" variant="ghost" onClick={handleHide} disabled={saving} />
      </div>
    </div>
  );
}

function WhyShown({ item }: { item: FeedItemType }) {
  const reasons: string[] = [];
  if (item.why_for_user) reasons.push(item.why_for_user);
  if (item.why_this && item.why_this !== item.why_for_user) reasons.push(item.why_this);
  if (item.why_now && item.why_now !== item.why_for_user && item.why_now !== item.why_this)
    reasons.push(item.why_now);

  if (reasons.length === 0) return null;

  return (
    <div className="mb-2 rounded-md bg-[var(--bg-glass)] px-3 py-2">
      <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
        {reasons.map((r, i) => (
          <span key={i}>
            {i > 0 && " "}
            {r}
          </span>
        ))}
      </p>
    </div>
  );
}

function CardAction({
  label,
  onClick,
  variant = "default",
  disabled = false,
}: {
  label: string;
  onClick: () => void;
  variant?: "default" | "positive" | "negative" | "ghost";
  disabled?: boolean;
}) {
  const colors: Record<string, string> = {
    default:
      "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-glass)]",
    positive:
      "text-green-600 dark:text-green-400 hover:bg-green-500/10",
    negative:
      "text-red-600 dark:text-red-400 hover:bg-red-500/10",
    ghost:
      "text-[var(--text-muted)]/50 hover:text-[var(--text-muted)] hover:bg-[var(--bg-glass)]",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`text-[11px] font-medium px-2 py-1 rounded transition-colors disabled:opacity-40 ${colors[variant]}`}
    >
      {label}
    </button>
  );
}
