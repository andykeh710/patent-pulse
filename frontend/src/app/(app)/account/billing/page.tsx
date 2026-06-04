"use client";

import { useState } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";

interface SubscriptionData {
  tier: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string | null;
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

export default function BillingPage() {
  const router = useRouter();
  const { data, error } = useSWR<SubscriptionData>("/api/v1/billing/subscription", fetcher);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

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

  if (error) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <p className="text-[var(--text-muted)]">Failed to load billing info.</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <p className="text-[var(--text-muted)]">Loading...</p>
      </div>
    );
  }

  const isFree = data.tier === "free";
  const periodEnd = data.current_period_end
    ? new Date(data.current_period_end).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <div className="max-w-lg mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Billing</h1>
      <p className="text-[var(--text-secondary)] mb-8">
        Manage your subscription and payment method.
      </p>

      {message && (
        <div className="mb-6 p-3 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)]">
          {message}
        </div>
      )}

      {/* Current plan */}
      <div className="p-6 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] mb-6">
        <p className="text-sm text-[var(--text-muted)] uppercase tracking-wide mb-1">Current Plan</p>
        <p className="text-xl font-bold text-[var(--text-primary)]">{TIER_LABELS[data.tier] || data.tier}</p>

        {data.status !== "active" && data.status !== "trialing" && (
          <p className="text-sm text-[var(--warning)] mt-1">Status: {data.status}</p>
        )}

        {periodEnd && (
          <p className="text-sm text-[var(--text-secondary)] mt-2">
            {data.cancel_at_period_end ? "Access until" : "Next billing date"}: {periodEnd}
          </p>
        )}

        {data.cancel_at_period_end && (
          <p className="text-sm text-[var(--warning)] mt-1">
            Your subscription will end on {periodEnd}. Reactivate via the billing portal.
          </p>
        )}
      </div>

      {/* Actions */}
      {isFree ? (
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
        <button
          onClick={handlePortal}
          disabled={loading}
          className="w-full py-3 px-4 rounded-lg border border-[var(--border-default)] text-[var(--text-primary)] font-medium hover:bg-[var(--bg-glass)] transition-colors disabled:opacity-50"
        >
          Manage Subscription in Stripe Portal
        </button>
      )}

      <button
        onClick={() => router.back()}
        className="mt-8 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        ← Back
      </button>
    </div>
  );
}
