"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { useAuth } from "@/lib/AuthContext";
import { preferencesApi } from "@/lib/api";
import type { UserPreferences } from "@/lib/types";

const ROLES = [
  { value: "founder", label: "Founder" },
  { value: "vc", label: "VC / Investor" },
  { value: "engineer", label: "Engineer" },
  { value: "researcher", label: "Researcher" },
  { value: "patent_legal", label: "Patent / Legal" },
  { value: "operator", label: "Operator" },
  { value: "other", label: "Other" },
];

const USE_CASES = [
  { value: "startup_ideas", label: "Startup ideas" },
  { value: "rd_monitoring", label: "R&D monitoring" },
  { value: "competitive_intel", label: "Competitive intelligence" },
  { value: "investment_research", label: "Investment research" },
  { value: "expiry_freedom", label: "Expiry / design freedom" },
  { value: "licensing", label: "Licensing" },
  { value: "academic", label: "Academic research" },
  { value: "general", label: "General discovery" },
];

const DIGEST_OPTIONS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "off", label: "Off" },
];

export default function PreferencesPage() {
  const { user } = useAuth();
  const { data, error, isLoading, mutate } = useSWR("preferences", preferencesApi.get);
  const [form, setForm] = useState<Partial<UserPreferences>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const update = (field: string, value: string | boolean | number | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setSaveError("");
    try {
      const updated = await preferencesApi.update(form);
      mutate(updated, false);
      setSaved(true);
    } catch {
      setSaveError("Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-[var(--bg-surface)] rounded" />
          <div className="h-64 bg-[var(--bg-surface)] rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-center">
          <p className="text-red-600 dark:text-red-400 font-medium">Could not load preferences</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">Try refreshing the page.</p>
        </div>
      </div>
    );
  }

  const formIsDirty = JSON.stringify(form) !== JSON.stringify(data);

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6 space-y-8 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">Preferences</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">These settings personalize your Today briefing and alerts.</p>
        </div>
        <button
          onClick={save}
          disabled={saving || !formIsDirty}
          className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--accent)] text-white disabled:opacity-40 transition-opacity"
        >
          {saving ? "Saving…" : saved ? "✓ Saved" : "Save"}
        </button>
      </div>

      {saveError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
          {saveError}
        </div>
      )}

      {/* 1. Profile */}
      <Section title="Profile">
        <p className="text-xs text-[var(--text-muted)]">
          Signed in as <strong>{user?.email || "Unknown"}</strong>.
          Your preferences personalize what appears in Today, Watchlist, and future digests.
        </p>
      </Section>

      {/* 2. Role / Persona */}
      <Section title="Role">
        <p className="text-xs text-[var(--text-muted)] mb-3">What best describes you? This helps prioritize the signals you care about.</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {ROLES.map((role) => (
            <button
              key={role.value}
              onClick={() => update("persona", role.value)}
              className={`rounded-lg border px-3 py-2 text-sm text-left transition-colors ${
                form.persona === role.value
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] font-medium"
                  : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--text-muted)]"
              }`}
            >
              {role.label}
            </button>
          ))}
        </div>
      </Section>

      {/* 3. Use Case */}
      <Section title="Use Case">
        <p className="text-xs text-[var(--text-muted)] mb-3">What are you trying to use patent intelligence for?</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {USE_CASES.map((uc) => (
            <button
              key={uc.value}
              onClick={() => update("use_case", uc.value)}
              className={`rounded-lg border px-3 py-2 text-sm text-left transition-colors ${
                form.use_case === uc.value
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] font-medium"
                  : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--text-muted)]"
              }`}
            >
              {uc.label}
            </button>
          ))}
        </div>
      </Section>

      {/* 4. Industries */}
      <Section title="Industry Focus">
        <p className="text-xs text-[var(--text-muted)] mb-2">Primary industry or technology domain.</p>
        <input
          type="text"
          value={form.industry_focus || ""}
          onChange={(e) => update("industry_focus", e.target.value || null)}
          placeholder="e.g. Semiconductors, Biotech, Clean Energy"
          className="w-full rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]"
        />
      </Section>

      {/* 5. Technology Interests */}
      <Section title="Technology Interests">
        <p className="text-xs text-[var(--text-muted)] mb-2">Technologies, methods, or areas you track. Free text.</p>
        <textarea
          value={form.interests_freetext || ""}
          onChange={(e) => update("interests_freetext", e.target.value || null)}
          placeholder="e.g. LLM agents, battery thermal management, surgical robotics, spatial computing"
          rows={3}
          className="w-full rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] resize-none"
        />
      </Section>

      {/* 6. Followed Topics */}
      <Section title="Followed Topics">
        <p className="text-xs text-[var(--text-muted)] mb-2">
          {form.followed_topic_count ?? 0} topic{form.followed_topic_count !== 1 ? "s" : ""} followed.
        </p>
        <a href="/themes" className="text-sm text-[var(--accent)] hover:underline">
          Manage topics →
        </a>
      </Section>

      {/* 7. Followed Companies */}
      <Section title="Followed Companies">
        <p className="text-xs text-[var(--text-muted)] mb-2">
          {form.followed_company_count ?? 0} compan{form.followed_company_count !== 1 ? "ies" : "y"} followed.
        </p>
        <a href="/companies" className="text-sm text-[var(--accent)] hover:underline">
          Browse companies →
        </a>
      </Section>

      {/* 8. Saved Patents / Searches */}
      <Section title="Watchlist & Searches">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <div className="text-2xl font-semibold text-[var(--text-primary)]">{form.saved_patent_count ?? 0}</div>
            <div className="text-[var(--text-muted)] text-xs mt-1">Saved patents</div>
            <a href="/watchlist" className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block">Open watchlist →</a>
          </div>
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <div className="text-2xl font-semibold text-[var(--text-primary)]">{form.saved_search_count ?? 0}</div>
            <div className="text-[var(--text-muted)] text-xs mt-1">Saved searches</div>
            <a href="/search" className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block">Open search →</a>
          </div>
        </div>
      </Section>

      {/* 9. Digest Settings */}
      <Section title="Digest & Alerts">
        <div className="space-y-4">
          <Field label="Email digest frequency">
            <select
              value={form.digest_frequency || "weekly"}
              onChange={(e) => update("digest_frequency", e.target.value)}
              className="w-full rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-primary)]"
            >
              {DIGEST_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </Field>
          <p className="text-xs text-[var(--text-muted)]">Email delivery requires Resend to be configured in production. Coming soon.</p>
        </div>
      </Section>

      {/* Save bar (sticky at bottom) */}
      {formIsDirty && (
        <div className="fixed bottom-0 left-0 right-0 bg-[var(--bg-surface)] border-t border-[var(--border-subtle)] p-4 flex justify-center z-10">
          <button
            onClick={save}
            disabled={saving}
            className="px-6 py-2 rounded-lg text-sm font-medium bg-[var(--accent)] text-white disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Helpers ──

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
      <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-3">{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">{label}</label>
      {children}
    </div>
  );
}
