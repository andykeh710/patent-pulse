"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface QuotaData {
  tier: string;
  used: number;
  limit: number | null;
  unlimited: boolean;
  remaining: number | null;
}

export function QuotaIndicator() {
  const [quota, setQuota] = useState<QuotaData | null>(null);
  const [error, setError] = useState(false);

  const fetchQuota = async () => {
    try {
      const resp = await fetch("/api/v1/chat/quota", { credentials: "include" });
      if (resp.ok) {
        const data = await resp.json();
        setQuota(data);
        setError(false);
      }
    } catch {
      setError(true);
    }
  };

  useEffect(() => {
    fetchQuota();
  }, []);

  // Expose fetchQuota for parent to call after sending a message
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__refreshChatQuota = fetchQuota;
    return () => {
      delete (window as unknown as Record<string, unknown>).__refreshChatQuota;
    };
  }, []);

  if (error || !quota) return null;

  if (quota.unlimited) {
    return (
      <div className="px-3 py-2 text-xs text-[var(--text-muted)]">
        {quota.tier === "lifetime" ? "Lifetime" : "Enterprise"} — Unlimited chats
      </div>
    );
  }

  const atLimit = quota.remaining === 0;

  return (
    <div className="px-3 py-2">
      <div
        className={`text-xs ${atLimit ? "text-yellow-600 dark:text-yellow-400" : "text-[var(--text-muted)]"}`}
      >
        {quota.used}/{quota.limit} chats today
        {atLimit && (
          <span className="block mt-1">
            <Link
              href="/account/billing"
              className="text-[var(--accent)] hover:underline"
            >
              Upgrade to Basic for 50/day
            </Link>
          </span>
        )}
      </div>
      {/* Progress bar */}
      {quota.limit && (
        <div className="mt-1.5 h-1 rounded-full bg-[var(--bg-glass)] overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              atLimit ? "bg-yellow-500" : "bg-[var(--accent)]"
            }`}
            style={{ width: `${Math.min(100, (quota.used / quota.limit) * 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

// Re-export the refresh helper
export function refreshQuota() {
  ((window as unknown as Record<string, unknown>).__refreshChatQuota as (() => void) | undefined)?.();
}
