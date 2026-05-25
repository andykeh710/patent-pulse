"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { useAuth } from "@/lib/AuthContext";
import { subscriptionsApi, topicsApi } from "@/lib/api";
import type { TopicSubscription, Topic } from "@/lib/types";

export default function AccountPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-gray-100 rounded" />;
  }

  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Account</h1>
          <p className="text-gray-600 text-sm">{user?.email}</p>
        </div>
        <button
          onClick={async () => {
            await logout();
            router.push("/");
          }}
          className="text-sm px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Sign out
        </button>
      </div>

      <SubscriptionsSection />
    </div>
  );
}

function SubscriptionsSection() {
  const { data: subs, mutate } = useSWR<TopicSubscription[]>(
    ["subscriptions"],
    () => subscriptionsApi.list()
  );

  const { data: themes } = useSWR<Topic[]>(["themes"], () => topicsApi.list());

  const isLoading = !subs || !themes;

  if (isLoading) {
    return <div className="animate-pulse h-24 bg-gray-100 rounded" />;
  }

  const themeMap = new Map(themes.map((t) => [t.id, t]));

  if (!subs.length) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>You&apos;re not subscribed to any topics yet.</p>
        <Link href="/themes" className="text-sm text-blue-600 hover:underline mt-2 inline-block">
          Browse topics to subscribe
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Your Subscriptions</h2>
      <div className="space-y-3">
        {subs.map((sub) => {
          const theme = themeMap.get(sub.theme_id);
          return (
            <div
              key={sub.id}
              className="border border-gray-200 rounded-lg p-4 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {theme?.name || "Unknown topic"}
                </p>
                <p className="text-xs text-gray-500 space-x-2">
                  <span className={sub.mode === "instant_alert" ? "text-orange-600" : "text-blue-600"}>
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
                  className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
                >
                  {sub.paused ? "Resume" : "Pause"}
                </button>
                <button
                  onClick={async () => {
                    const newMode = sub.mode === "instant_alert" ? "weekly_digest" : "instant_alert";
                    await subscriptionsApi.update(sub.id, { mode: newMode });
                    mutate();
                  }}
                  className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
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
