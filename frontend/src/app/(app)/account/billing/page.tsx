"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { useRouter, useSearchParams } from "next/navigation";

// ── types ────────────────────────────────────────────────────────────

interface SubscriptionData {
  tier: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string | null;
}

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

const fetcher = (url: string, options?: RequestInit) =>
  fetch(url, options).then((r) => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  basic: "Basic",
  lifetime: "Lifetime",
  enterprise: "Enterprise",
};

const TIER_BADGE_CLASS: Record<string, string> = {
  free: "bg-[var(--bg-glass)] text-[var(--text-secondary)]",
  basic: "bg-[var(--accent)]/10 text-[var(--accent)]",
  lifetime: "bg-[var(--score-high)]/10 text-[var(--score-high)]",
  enterprise: "bg-purple-500/10 text-purple-400",
};

const FEATURE_LABELS: Record<string, string> = {
  views: "Patent views",
  search: "Searches",
  themes: "Topics",
  companies: "Companies followed",
  chat: "Chat messages",
};

const FEATURE_ICONS: Record<string, string> = {
  views: "📄",
  search: "🔍",
  themes: "📂",
  companies: "🏢",
  chat: "💬",
};

// ── pricing comparison (hardcoded — mirrors Stripe LIVE) ─────────────

const PLANS = [
  {
    tier: "free",
    price: "$0",
    period: "",
    features: ["1 topic", "3 companies", "5 chat/day"],
    highlighted: false,
  },
  {
    tier: "basic",
    price: "$8",
    period: "/year",
    features: ["Unlimited topics", "Unlimited companies", "50 chat/day", "CSV export"],
    highlighted: true,
  },
  {
    tier: "lifetime",
    price: "$108",
    period: " once",
    features: [
      "Everything in Basic",
      "PDF reports",
      "Unlimited chat",
      "Early supporter badge",
    ],
    highlighted: false,
  },
  {
    tier: "enterprise",
    price: "$1,000",
    period: "/year",
    features: [
      "Everything in Lifetime",
      "API access",
      "Admin tools",
      "Priority support",
    ],
    highlighted: false,
  },
];

// ── component ────────────────────────────────────────────────────────

export default function BillingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { data: sub, error: subError } = useSWR<SubscriptionData>(
    "/api/v1/billing/subscription",
    fetcher
  );
  const { data: usage, error: usageError } = useSWR<UsageData>(
    "/api/v1/account/usage",
    fetcher
  );

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [toast, setToast] = useState<{ type: "success" | "info"; text: string } | null>(null);

  // ── URL param toasts ───────────────────────────────────────────
  useEffect(() => {
    const upgraded = searchParams.get("upgraded");
    const cancelled = searchParams.get("cancelled");
    if (upgraded) {
      setToast({
        type: "success",
        text: `Upgrade successful. You now have ${TIER_LABELS[upgraded] || upgraded} access.`,
      });
    } else if (cancelled === "true") {
      setToast({
        type: "info",
        text: "Upgrade cancelled. You're still on the Free tier.",
      });
    }
  }, [searchParams]);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 6000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const handleCheckout = async (tier: string) => {
    setLoading(true);
    setMessage("");
    try {
      const r = await fetcher("/api/v1/billing/checkout-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier }),
      });
      window.location.href = r.checkout_url;
    } catch {
      setMessage("Failed to start checkout. Try again.");
      setLoading(false);
    }
  };

  const handlePortal = async () => {
    setLoading(true);
    try {
      const r = await fetcher("/api/v1/billing/portal-session", {
        method: "POST",
      });
      window.location.href = r.portal_url;
    } catch {
      setMessage("Failed to open billing portal.");
      setLoading(false);
    }
  };

  // ── loading / error ─────────────────────────────────────────────
  if (subError || usageError) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <p className="text-[var(--text-muted)]">Failed to load billing info.</p>
      </div>
    );
  }

  if (!sub || !usage) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <p className="text-[var(--text-muted)]">Loading...</p>
      </div>
    );
  }

  const tier = sub.tier || "free";
  const isFree = tier === "free";
  const isLifetime = tier === "lifetime";
  const periodEnd = sub.current_period_end
    ? new Date(sub.current_period_end).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      {/* ── Toast ── */}
      {toast && (
        <div
          className={`mb-6 p-3 rounded-lg text-sm font-medium border ${
            toast.type === "success"
              ? "bg-[var(--score-high)]/10 border-[var(--score-high)]/30 text-[var(--score-high)]"
              : "bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-secondary)]"
          }`}
        >
          {toast.text}
          <button
            onClick={() => setToast(null)}
            className="ml-3 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            ×
          </button>
        </div>
      )}

      {message && (
        <div className="mb-6 p-3 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)]">
          {message}
        </div>
      )}

      <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Billing</h1>
      <p className="text-[var(--text-secondary)] mb-8">
        Manage your subscription, view usage, and upgrade your plan.
      </p>

      {/* ── Current plan badge ── */}
      <div className="p-6 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm text-[var(--text-muted)] uppercase tracking-wide mb-1">
              Current Plan
            </p>
            <div className="flex items-center gap-3">
              <p className="text-xl font-bold text-[var(--text-primary)]">
                {TIER_LABELS[tier] || tier}
              </p>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${TIER_BADGE_CLASS[tier] || ""}`}
              >
                {tier}
              </span>
            </div>
          </div>

          {!isFree && periodEnd && (
            <div className="text-right">
              <p className="text-xs text-[var(--text-muted)]">
                {sub.cancel_at_period_end ? "Access until" : "Renews"}
              </p>
              <p className="text-sm text-[var(--text-primary)]">{periodEnd}</p>
            </div>
          )}
        </div>

        {sub.status !== "active" && sub.status !== "trialing" && (
          <p className="text-sm text-[var(--warning)]">Status: {sub.status}</p>
        )}
        {sub.cancel_at_period_end && (
          <p className="text-sm text-[var(--warning)] mt-1">
            Your subscription will end on {periodEnd}. Reactivate via the billing portal.
          </p>
        )}

        {/* ── Lifetime special ── */}
        {isLifetime && (
          <div className="mt-3 p-3 rounded bg-[var(--score-high)]/5 border border-[var(--score-high)]/20 text-sm text-[var(--score-high)]">
            You&apos;re on Lifetime. Thank you for early support.
          </div>
        )}
      </div>

      {/* ── Usage bars ── */}
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Usage</h2>
      <div className="space-y-3 mb-8">
        {Object.entries(usage.features).map(([key, feat]) => (
          <div
            key={key}
            className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)]"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm">{FEATURE_ICONS[key] || "•"}</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">
                  {FEATURE_LABELS[key] || key}
                </span>
              </div>
              <span className="text-xs text-[var(--text-muted)]">
                {feat.unlimited
                  ? "Unlimited"
                  : `${feat.used} / ${feat.limit}${feat.period ? ` (${feat.period})` : ""}`}
              </span>
            </div>

            {/* ── Progress bar ── */}
            {!feat.unlimited && feat.limit != null && feat.limit > 0 ? (
              <div className="w-full h-2 bg-[var(--bg-base)] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    feat.used / feat.limit >= 0.9
                      ? "bg-[var(--expiry-lapsed-confirmed)]"
                      : feat.used / feat.limit >= 0.8
                        ? "bg-[var(--warning)]"
                        : "bg-[var(--accent)]"
                  }`}
                  style={{
                    width: `${Math.min(100, (feat.used / feat.limit) * 100)}%`,
                  }}
                />
              </div>
            ) : (
              <div className="w-full h-2 bg-[var(--accent)]/20 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--accent)]/40"
                  style={{ width: "100%" }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Pricing comparison table ── */}
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Plans</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {PLANS.map((plan) => {
          const isCurrent = plan.tier === tier;
          return (
            <div
              key={plan.tier}
              className={`p-4 rounded-lg border text-center ${
                isCurrent
                  ? "border-[var(--accent)] bg-[var(--accent)]/5"
                  : plan.highlighted
                    ? "border-[var(--border-subtle)] bg-[var(--bg-surface)] ring-1 ring-[var(--accent)]/30"
                    : "border-[var(--border-subtle)] bg-[var(--bg-surface)]"
              }`}
            >
              <p className="text-xs font-semibold text-[var(--text-primary)] uppercase mb-1">
                {plan.tier}
              </p>
              <p className="text-lg font-bold text-[var(--text-primary)] mb-1">
                {plan.price}
                <span className="text-xs text-[var(--text-muted)] font-normal">
                  {plan.period}
                </span>
              </p>
              {isCurrent && (
                <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[var(--accent)] text-white mb-2">
                  Current
                </span>
              )}
              <ul className="text-[10px] text-[var(--text-secondary)] space-y-1 text-left">
                {plan.features.map((f) => (
                  <li key={f}>• {f}</li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {/* ── Actions ── */}
      {isLifetime ? (
        <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)]">
          Lifetime access — no billing needed.{" "}
          {sub.stripe_customer_id && (
            <button
              onClick={handlePortal}
              disabled={loading}
              className="text-[var(--accent)] hover:underline ml-1"
            >
              View invoice history →
            </button>
          )}
        </div>
      ) : isFree ? (
        <div className="space-y-3">
          <p className="text-sm text-[var(--text-secondary)] mb-3">Upgrade your plan:</p>
          <button
            onClick={() => handleCheckout("basic")}
            disabled={loading}
            className="w-full py-3 px-4 rounded-lg bg-[var(--accent)] text-white font-medium hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
          >
            Upgrade to Basic — $8/year
          </button>
          <button
            onClick={() => handleCheckout("lifetime")}
            disabled={loading}
            className="w-full py-3 px-4 rounded-lg border border-[var(--accent)] text-[var(--accent)] font-medium hover:bg-[var(--accent)]/10 transition-colors disabled:opacity-50"
          >
            Buy Lifetime — $108 once
          </button>
          <button
            onClick={() => handleCheckout("enterprise")}
            disabled={loading}
            className="w-full py-3 px-4 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] font-medium hover:border-[var(--accent)] transition-colors disabled:opacity-50"
          >
            Enterprise — $1,000/year
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <button
            onClick={handlePortal}
            disabled={loading}
            className="w-full py-3 px-4 rounded-lg border border-[var(--border-default)] text-[var(--text-primary)] font-medium hover:bg-[var(--bg-glass)] transition-colors disabled:opacity-50"
          >
            Manage billing in Stripe Portal
          </button>
          <button
            onClick={handlePortal}
            disabled={loading}
            className="w-full py-2 px-4 rounded-lg border border-[var(--expiry-lapsed-confirmed)]/30 text-[var(--expiry-lapsed-confirmed)] text-sm font-medium hover:bg-[var(--expiry-lapsed-confirmed)]/5 transition-colors disabled:opacity-50"
          >
            Cancel subscription
          </button>
        </div>
      )}

      <div className="mt-10 flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          ← Back
        </button>
        <a
          href="/pricing"
          className="text-sm text-[var(--accent)] hover:underline"
        >
          Compare all plans →
        </a>
      </div>
    </div>
  );
}
