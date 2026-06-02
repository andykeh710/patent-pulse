"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { useAuth } from "@/lib/AuthContext";
import { subscriptionsApi, topicsApi, billingApi } from "@/lib/api";
import type { TopicSubscription, Topic, BillingSubscription } from "@/lib/types";

export default function AccountPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-[var(--bg-elevated)] rounded" />;
  }

  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Account</h1>
          <p className="text-[var(--text-secondary)] text-sm">{user?.email}</p>
        </div>
        <button
          onClick={async () => {
            await logout();
            router.push("/");
          }}
          className="text-sm px-4 py-2 border border-[var(--border-default)] rounded-lg hover:bg-[var(--bg-glass)]"
        >
          Sign out
        </button>
      </div>

      <SubscriptionsSection />

      <DangerZone />
    </div>
  );
}

function DangerZone() {
  const { logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const handleDelete = async () => {
    setError("");
    setDeleting(true);
    try {
      const res = await fetch("/api/v1/account/me", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm_email: confirmEmail }),
      });
      if (res.status === 204) {
        await logout();
        router.push("/");
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Account deletion failed");
      }
    } catch {
      setError("Network error — please try again");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <hr className="my-8 border-red-200" />
      <div>
        <h2 className="text-lg font-semibold text-red-700 mb-2">Danger Zone</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-3">
          Permanently delete your account and all associated data. This
          action cannot be undone.
        </p>
        <button
          onClick={() => setOpen(true)}
          className="text-sm px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Delete my account
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-[var(--bg-surface)] rounded-xl p-6 max-w-md w-full shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-[var(--text-primary)]">
              Delete your account?
            </h3>
            <p className="text-sm text-[var(--text-secondary)]">
              This will permanently delete your account, subscriptions,
              API keys, and billing records. Email delivery history will
              be anonymized. Type your email to confirm.
            </p>
            <input
              type="email"
              placeholder="your@email.com"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              className="w-full border border-[var(--border-default)] rounded-lg px-3 py-2 text-sm"
            />
            {error && (
              <p className="text-xs text-red-600">{error}</p>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setOpen(false);
                  setConfirmEmail("");
                  setError("");
                }}
                className="text-sm px-4 py-2 border rounded-lg hover:bg-[var(--bg-glass)]"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting || !confirmEmail}
                className="text-sm px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function SubscriptionsSection() {
  const { isAuthenticated } = useAuth();
  const { data: subscriptions, mutate } = useSWR<TopicSubscription[]>(
    isAuthenticated ? "account-subs" : null,
    () => subscriptionsApi.list()
  );

  const { data: billing } = useSWR<BillingSubscription>(
    isAuthenticated ? "account-billing" : null,
    () => billingApi.getSubscription()
  );

  const { data: themes } = useSWR<Topic[]>(["themes"], () => topicsApi.list());

  const loading = !subscriptions || !themes;

  if (loading) {
    return <div className="animate-pulse h-24 bg-[var(--bg-elevated)] rounded" />;
  }

  const themeMap = new Map(themes.map((t) => [t.id, t]));

  if (!subscriptions.length) {
    return (
      <div className="text-center py-12 text-[var(--text-muted)]">
        <p>You&apos;re not subscribed to any topics yet.</p>
        <Link href="/themes" className="text-sm text-[var(--accent)] hover:underline mt-2 inline-block">
          Browse topics to subscribe
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Billing */}
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Billing</h2>
      <div className="mb-6 p-4 border rounded">
        <p className="text-sm text-[var(--text-secondary)]">
          Current tier: <span className="font-semibold">{billing?.tier ?? "free"}</span>
          {billing?.status && ` · ${billing.status}`}
        </p>
        <Link href="/account/billing" className="text-sm text-[var(--accent)] hover:underline">
          Manage billing →
        </Link>
      </div>

      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Your Subscriptions</h2>
      <div className="space-y-3">
        {subscriptions.map((sub) => {
          const theme = themeMap.get(sub.theme_id);
          return (
            <div
              key={sub.id}
              className="border border-[var(--border-subtle)] rounded-lg p-4 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium text-[var(--text-primary)] truncate">
                  {theme?.name || "Unknown topic"}
                </p>
                <p className="text-xs text-[var(--text-muted)] space-x-2">
                  <span className={sub.mode === "instant_alert" ? "text-orange-600" : "text-[var(--accent)]"}>
                    {sub.mode === "instant_alert" ? "Instant" : "Weekly Digest"}
                  </span>
                  {sub.min_score != null && (
                    <span>· min score: {sub.min_score}</span>
                  )}
                  {sub.paused && (
                    <span className="text-amber-600">· Paused</span>
                  )}
                  {sub.last_delivered_at && (
                    <span>
                      · Last: {new Date(sub.last_delivered_at).toLocaleDateString()}
                    </span>
                  )}
                </p>
              </div>

              <div className="flex gap-1 shrink-0">
                <button
                  onClick={async () => {
                    await subscriptionsApi.update(sub.id, { paused: !sub.paused });
                    mutate();
                  }}
                  className="text-xs px-2 py-1 border rounded hover:bg-[var(--bg-glass)]"
                >
                  {sub.paused ? "Resume" : "Pause"}
                </button>
                <button
                  onClick={async () => {
                    const newMode = sub.mode === "instant_alert" ? "weekly_digest" : "instant_alert";
                    await subscriptionsApi.update(sub.id, { mode: newMode });
                    mutate();
                  }}
                  className="text-xs px-2 py-1 border rounded hover:bg-[var(--bg-glass)]"
                >
                  Switch
                </button>
                <button
                  onClick={async () => {
                    if (!confirm("Unsubscribe from this topic?")) return;
                    await subscriptionsApi.delete(sub.id);
                    mutate();
                  }}
                  className="text-xs px-2 py-1 border border-red-200 text-red-600 rounded hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
