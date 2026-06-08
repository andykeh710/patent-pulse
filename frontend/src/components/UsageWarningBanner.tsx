"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import Link from "next/link";

// ── types ────────────────────────────────────────────────────────────

interface FeatureUsage {
  used: number;
  limit: number | null;
  remaining: number | null;
  unlimited: boolean;
  period: string | null;
}

interface UsageData {
  tier: string;
  features: Record<string, FeatureUsage>;
  renews_at: string | null;
}

const DISMISS_KEY = "usage-banner-dismissed-at";
const DISMISS_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

const FEATURE_LABELS: Record<string, string> = {
  themes: "topics",
  companies: "companies",
  chat: "chat messages",
};

function isDismissed(): boolean {
  if (typeof window === "undefined") return false;
  const raw = localStorage.getItem(DISMISS_KEY);
  if (!raw) return false;
  const timestamp = parseInt(raw, 10);
  if (isNaN(timestamp)) return false;
  return Date.now() - timestamp < DISMISS_TTL_MS;
}

function dismiss() {
  if (typeof window !== "undefined") {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  }
}

// ── component ────────────────────────────────────────────────────────

export function UsageWarningBanner() {
  const { data } = useSWR<UsageData>("/api/v1/account/usage", {
    refreshInterval: 5 * 60 * 1000, // re-fetch every 5 min
  });
  const [visible, setVisible] = useState(false);
  const [bannerText, setBannerText] = useState("");
  const [dismissedByUser, setDismissedByUser] = useState(false);

  useEffect(() => {
    setDismissedByUser(isDismissed());
  }, []);

  useEffect(() => {
    if (dismissedByUser) {
      setVisible(false);
      return;
    }
    if (!data || data.tier !== "free") {
      setVisible(false);
      return;
    }

    // Find first feature at >=80% usage
    for (const [key, feat] of Object.entries(data.features)) {
      if (feat.unlimited || feat.limit == null || feat.limit === 0) continue;
      const pct = feat.used / feat.limit;
      if (pct >= 0.8) {
        const label = FEATURE_LABELS[key] || key;
        setBannerText(
          `You've used ${feat.used}/${feat.limit} ${label}. Upgrade to Basic for more.`
        );
        setVisible(true);
        return;
      }
    }

    setVisible(false);
  }, [data, dismissedByUser]);

  const handleDismiss = () => {
    dismiss();
    setDismissedByUser(true);
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="bg-[var(--accent)]/10 border-b border-[var(--accent)]/20 px-4 py-2">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between gap-4">
        <p className="text-sm text-[var(--text-primary)]">{bannerText}</p>
        <div className="flex items-center gap-2 shrink-0">
          <Link
            href="/account/billing"
            className="text-xs font-semibold px-3 py-1 rounded bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-colors"
          >
            Upgrade →
          </Link>
          <button
            onClick={handleDismiss}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] px-2 py-1"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
