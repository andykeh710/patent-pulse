"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";

interface EmailPrefs {
  weekly_briefing_enabled: boolean;
  instant_alerts_enabled: boolean;
}

const fetcher = (url: string, options?: RequestInit) =>
  fetch(url, options).then((r) => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });

export default function EmailPreferencesPage() {
  const router = useRouter();
  const { data, mutate } = useSWR<EmailPrefs>("/api/v1/account/email-preferences", fetcher);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const toggle = async (field: keyof EmailPrefs) => {
    if (!data) return;
    setSaving(true);
    setSaved(false);
    const next = { ...data, [field]: !data[field] };
    await fetcher("/api/v1/account/email-preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: next[field] }),
    });
    mutate(next, false);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!data) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <p className="text-[var(--text-muted)]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Email Preferences</h1>
      <p className="text-[var(--text-secondary)] mb-8">
        Control which emails you receive from Invention Index 8.
      </p>

      <div className="space-y-6">
        <label className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] cursor-pointer">
          <div>
            <p className="font-medium text-[var(--text-primary)]">Weekly Briefing</p>
            <p className="text-sm text-[var(--text-muted)]">A weekly summary of patent activity in your topics and companies.</p>
          </div>
          <button
            role="switch"
            aria-checked={data.weekly_briefing_enabled}
            disabled={saving}
            onClick={() => toggle("weekly_briefing_enabled")}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              data.weekly_briefing_enabled ? "bg-[var(--accent)]" : "bg-[var(--border-default)]"
            }`}
          >
            <span
              className={`block w-5 h-5 rounded-full bg-white shadow transition-transform ${
                data.weekly_briefing_enabled ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </button>
        </label>

        <label className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] cursor-pointer">
          <div>
            <p className="font-medium text-[var(--text-primary)]">Instant Alerts</p>
            <p className="text-sm text-[var(--text-muted)]">Real-time email when a followed company files a new patent (coming soon).</p>
          </div>
          <button
            role="switch"
            aria-checked={data.instant_alerts_enabled}
            disabled={true}
            className="relative w-11 h-6 rounded-full bg-[var(--border-default)] opacity-50 cursor-not-allowed"
          >
            <span className="block w-5 h-5 rounded-full bg-white shadow translate-x-0.5" />
          </button>
        </label>
      </div>

      {saved && (
        <p className="mt-4 text-sm text-[var(--accent)]">Preferences saved.</p>
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
