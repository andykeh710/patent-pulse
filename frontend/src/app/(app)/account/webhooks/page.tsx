"use client";

import { useState } from "react";
import useSWR from "swr";

// ── types ────────────────────────────────────────────────────────────

interface WebhookConfig {
  webhook_url: string | null;
  enabled: boolean;
  last_success_at: string | null;
  last_failure_at: string | null;
}

interface AlertItem {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  status: string;
  delivery_method: string | null;
  created_at: string;
  sent_at: string | null;
}

const fetcher = (url: string, options?: RequestInit) =>
  fetch(url, options).then((r) => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });

const ALERT_LABELS: Record<string, string> = {
  assignee_filed: "Company filed",
  patent_expiring: "Expiring patent",
  trend_spike: "Trend spike",
  high_opportunity: "High opportunity",
  test: "Test",
};

// ── component ────────────────────────────────────────────────────────

export default function WebhooksPage() {
  const { data: config, mutate: mutateConfig } = useSWR<WebhookConfig>(
    "/api/v1/account/webhook-config",
    fetcher
  );
  const { data: alerts } = useSWR<AlertItem[]>(
    "/api/v1/account/alerts?limit=50",
    fetcher,
    { refreshInterval: 30_000 }
  );

  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);

  // Sync form with fetched config
  useState(() => {
    if (config) {
      setUrl(config.webhook_url || "");
      setEnabled(config.enabled);
    }
  });

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      await fetcher("/api/v1/account/webhook-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ webhook_url: url || null, secret_key: secret || null, enabled }),
      });
      setMessage("Saved.");
      mutateConfig();
      // Clear secret after save (don't re-display)
      setSecret("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed to save");
    }
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await fetcher("/api/v1/account/webhook-config/test", { method: "POST" });
      setTestResult(r.success ? "Test webhook delivered successfully" : "Test webhook failed — check URL and network");
    } catch (e) {
      setTestResult(e instanceof Error ? e.message : "Test failed");
    }
    setTesting(false);
  };

  if (!config) {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <p className="text-[var(--text-muted)]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Webhook Alerts</h1>
      <p className="text-[var(--text-secondary)] mb-8">
        Configure real-time webhook notifications for patent alerts. Lifetime and Enterprise tiers only.
      </p>

      {message && (
        <div className="mb-6 p-3 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)]">
          {message}
        </div>
      )}

      {/* ── Config form ── */}
      <div className="p-6 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] mb-8 space-y-4">
        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
            Webhook URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://your-server.com/webhook"
            className="w-full px-3 py-2 rounded-lg bg-[var(--bg-base)] border border-[var(--border-default)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
            Secret Key (HMAC signing)
          </label>
          <input
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder="Generate a random string"
            className="w-full px-3 py-2 rounded-lg bg-[var(--bg-base)] border border-[var(--border-default)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] outline-none"
          />
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Used to sign webhook payloads with HMAC-SHA256. Keep this secret.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-[var(--bg-glass)] peer-checked:bg-[var(--accent)] rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all" />
          </label>
          <span className="text-sm text-[var(--text-primary)]">Enable webhook alerts</span>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          {config.enabled && config.webhook_url && (
            <button
              onClick={handleTest}
              disabled={testing}
              className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-sm text-[var(--text-primary)] hover:bg-[var(--bg-glass)] transition-colors disabled:opacity-50"
            >
              {testing ? "Sending..." : "Send Test"}
            </button>
          )}
        </div>

        {testResult && (
          <div
            className={`p-3 rounded text-sm ${
              testResult.includes("success")
                ? "bg-[var(--score-high)]/10 text-[var(--score-high)]"
                : "bg-[var(--expiry-lapsed-confirmed)]/10 text-[var(--expiry-lapsed-confirmed)]"
            }`}
          >
            {testResult}
          </div>
        )}
      </div>

      {/* ── Delivery log ── */}
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Recent Delivery Log</h2>
      {!alerts || alerts.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">No alerts yet.</p>
      ) : (
        <div className="space-y-2">
          {alerts.slice(0, 50).map((alert) => (
            <div
              key={alert.id}
              className="p-3 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-[var(--text-primary)]">
                    {ALERT_LABELS[alert.type] || alert.type}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      alert.status === "sent"
                        ? "bg-[var(--score-high)]/10 text-[var(--score-high)]"
                        : alert.status === "failed"
                          ? "bg-[var(--expiry-lapsed-confirmed)]/10 text-[var(--expiry-lapsed-confirmed)]"
                          : "bg-[var(--bg-glass)] text-[var(--text-muted)]"
                    }`}
                  >
                    {alert.status}
                  </span>
                </div>
                <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">
                  {String(alert.payload.title || alert.payload.message || "")}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-[10px] text-[var(--text-muted)]">
                  {new Date(alert.created_at).toLocaleDateString()}
                </p>
                {alert.delivery_method && (
                  <p className="text-[10px] text-[var(--text-muted)]">{alert.delivery_method}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
