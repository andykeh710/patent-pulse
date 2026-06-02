"use client";

import { useState } from "react";
import useSWR from "swr";
import { useAuth } from "@/lib/AuthContext";
import { subscriptionsApi } from "@/lib/api";
import type { Topic, TopicSubscription, SubscriptionMode } from "@/lib/types";
import Link from "next/link";

interface Props {
  theme: Topic;
}

export function SubscribePanel({ theme }: Props) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  if (authLoading) {
    return <div className="h-20 bg-[var(--bg-elevated)] rounded animate-pulse" />;
  }

  if (!isAuthenticated) {
    return (
      <div className="bg-blue-50 border border-[var(--accent)]/30 rounded-lg p-4 text-sm text-[var(--accent)]">
        <Link href="/login" className="underline font-medium">
          Sign in
        </Link>{" "}
        to subscribe to alerts for this topic.
      </div>
    );
  }

  return <SubscribeForm theme={theme} />;
}

function SubscribeForm({ theme }: { theme: Topic }) {
  const [mode, setMode] = useState<SubscriptionMode>("weekly_digest");
  const [minScore, setMinScore] = useState<number | null>(null);
  const [subscribing, setSubscribing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [pausing, setPausing] = useState(false);

  const { data: subs, mutate } = useSWR<TopicSubscription[]>(
    ["subscriptions"],
    () => subscriptionsApi.list()
  );

  const existing = subs?.find((s) => s.theme_id === theme.id);

  const handleSubscribe = async () => {
    setSubscribing(true);
    setFeedback(null);
    try {
      await subscriptionsApi.create({
        theme_id: theme.id,
        mode,
        min_score: minScore,
      });
      mutate();
      setFeedback("Subscribed!");
    } catch {
      setFeedback("Failed to subscribe. Try again.");
    } finally {
      setSubscribing(false);
    }
  };

  const handleTogglePause = async () => {
    if (!existing) return;
    setPausing(true);
    try {
      await subscriptionsApi.update(existing.id, { paused: !existing.paused });
      mutate();
    } catch {
      setFeedback("Failed to update.");
    } finally {
      setPausing(false);
    }
  };

  const handleChangeMode = async (newMode: SubscriptionMode) => {
    if (!existing) return;
    try {
      await subscriptionsApi.update(existing.id, { mode: newMode });
      mutate();
    } catch {
      setFeedback("Failed to change mode.");
    }
  };

  const handleDelete = async () => {
    if (!existing || !confirm("Unsubscribe from this topic?")) return;
    try {
      await subscriptionsApi.delete(existing.id);
      mutate();
    } catch {
      setFeedback("Failed to unsubscribe.");
    }
  };

  if (existing) {
    return (
      <div className="bg-[var(--score-high-bg)] border border-[var(--score-high)]/30 rounded-lg p-4 space-y-3 text-sm">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2 py-0.5 bg-[var(--score-high-bg)] text-[var(--score-high)] rounded-full text-xs font-medium">
            {existing.mode === "instant_alert" ? "Instant" : "Weekly Digest"}
          </span>
          {existing.min_score != null && (
            <span className="px-2 py-0.5 bg-[var(--bg-elevated)] text-[var(--text-secondary)] rounded-full text-xs">
              min score: {existing.min_score}
            </span>
          )}
          {existing.paused && (
            <span className="px-2 py-0.5 bg-[var(--score-medium-bg)] text-[var(--score-medium)] rounded-full text-xs">
              Paused
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleTogglePause}
            disabled={pausing}
            className="text-xs px-3 py-1 border rounded hover:bg-[var(--bg-glass)]"
          >
            {existing.paused ? "Resume" : "Pause"}
          </button>

          {existing.mode !== "instant_alert" && (
            <button
              onClick={() => handleChangeMode("instant_alert")}
              className="text-xs px-3 py-1 border rounded hover:bg-[var(--bg-glass)]"
            >
              Switch to Instant
            </button>
          )}
          {existing.mode !== "weekly_digest" && (
            <button
              onClick={() => handleChangeMode("weekly_digest")}
              className="text-xs px-3 py-1 border rounded hover:bg-[var(--bg-glass)]"
            >
              Switch to Weekly
            </button>
          )}

          <button
            onClick={handleDelete}
            className="text-xs px-3 py-1 border border-red-200 text-red-600 rounded hover:bg-red-50"
          >
            Unsubscribe
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-4 text-sm">
      <h3 className="font-medium text-[var(--text-primary)]">Subscribe</h3>

      <div className="flex gap-4">
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="mode"
            value="weekly_digest"
            checked={mode === "weekly_digest"}
            onChange={() => setMode("weekly_digest")}
          />
          Weekly Digest
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="mode"
            value="instant_alert"
            checked={mode === "instant_alert"}
            onChange={() => setMode("instant_alert")}
          />
          Instant Alert
        </label>
      </div>

      <div>
        <label className="text-xs text-[var(--text-muted)]">
          Minimum opportunity score (optional): {minScore ?? "none"}
        </label>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={minScore ?? 0}
          onChange={(e) => {
            const v = Number(e.target.value);
            setMinScore(v === 0 ? null : v);
          }}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-[var(--text-muted)]">
          <span>0 (all matches)</span>
          <span>100 (best only)</span>
        </div>
      </div>

      <button
        onClick={handleSubscribe}
        disabled={subscribing}
        className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
      >
        {subscribing ? "Subscribing…" : "Subscribe"}
      </button>

      {feedback && (
        <p className={`text-xs ${feedback.includes("Failed") ? "text-red-600" : "text-green-600"}`}>
          {feedback}
        </p>
      )}
    </div>
  );
}
