"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { useAuth } from "@/lib/AuthContext";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
// import { FreshnessChip } from "@/components/ui/FreshnessChip";

// ── Types ────────────────────────────────────────────────────────────────

interface ProviderHealth {
  provider: string;
  latest_status: string;
  latest_target_type: string | null;
  latest_target_id: string | null;
  latest_http_status: number | null;
  latest_records_found: number | null;
  latest_error: string | null;
  latest_started_at: string | null;
  latest_success_at: string | null;
  latest_failure_at: string | null;
  latest_source_url: string | null;
}

interface SourceHealth {
  total_patents: number;
  latest_publication_date: string | null;
  latest_ingested_at: string | null;
  source_lag_days: number | null;
  providers: ProviderHealth[];
}

interface SourceFetchRow {
  id: string;
  provider: string;
  office: string | null;
  target_type: string;
  target_id: string | null;
  source_url: string | null;
  status: string;
  http_status: number | null;
  error_message: string | null;
  records_found: number | null;
  duration_ms: number | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case "success":
      return "var(--ok)";
    case "failed":
    case "blocked":
    case "unavailable":
      return "var(--danger)";
    case "empty":
    case "partial":
      return "var(--warn)";
    default:
      return "var(--text-muted)";
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function SourceHealthPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const { data: health, error: healthError, isLoading: healthLoading } =
    useSWR<SourceHealth>(
      isAuthenticated ? "/api/v1/admin/source-health" : null,
      (url) =>
        fetch(url, { credentials: "include" }).then((r) => {
          if (!r.ok) throw r.status;
          return r.json();
        }),
      { refreshInterval: 30_000 }
    );

  const { data: fetches, isLoading: fetchesLoading } = useSWR<SourceFetchRow[]>(
    isAuthenticated ? "/api/v1/admin/source-fetches?limit=50" : null,
    (url) =>
      fetch(url, { credentials: "include" }).then((r) => {
        if (!r.ok) throw r.status;
        return r.json();
      }),
    { refreshInterval: 30_000 }
  );

  // Retry state
  const [retrying, setRetrying] = useState<string | null>(null);
  const [retryResult, setRetryResult] = useState<string | null>(null);
  const [grantDate, setGrantDate] = useState("");
  const [appDate, setAppDate] = useState("");
  const [catchStart, setCatchStart] = useState("");
  const [catchEnd, setCatchEnd] = useState("");

  if (authLoading) return <div className="p-8 text-[var(--text-muted)]">Loading...</div>;
  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  const dispatchRetry = async (
    endpoint: string,
    body: Record<string, string | null>
  ) => {
    setRetrying(endpoint);
    setRetryResult(null);
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setRetryResult(`Task dispatched: ${data.task_id}`);
      } else {
        setRetryResult(`Error: ${data.detail || res.status}`);
      }
    } catch {
      setRetryResult("Network error");
    } finally {
      setRetrying(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="Source Health"
        description="Ingestion pipeline observability — provider status, fetch history, and manual retry controls."
      />

      {healthError && (
        <ErrorState
          title="Unable to load source health"
          message="The admin source health endpoint returned an error. You may not have admin access."
          detail={String(healthError)}
        />
      )}

      {/* ── Overall Freshness ── */}
      {healthLoading ? (
        <LoadingState variant="card" count={3} />
      ) : health ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label="Total Patents"
              value={health.total_patents?.toLocaleString() || "—"}
            />
            <StatCard
              label="Latest Publication"
              value={
                health.latest_publication_date
                  ? new Date(health.latest_publication_date).toLocaleDateString(
                      "en-US",
                      { month: "short", day: "numeric", year: "numeric" }
                    )
                  : "—"
              }
            />
            <StatCard
              label="Source Lag"
              value={
                health.source_lag_days !== null
                  ? `${health.source_lag_days}d`
                  : "—"
              }
              highlight={
                health.source_lag_days !== null && health.source_lag_days > 10
              }
            />
            <StatCard
              label="Last Ingested"
              value={formatDate(health.latest_ingested_at)}
            />
          </div>

          {/* ── Provider Status Table ── */}
          <section>
            <h2 className="text-sm font-semibold text-[var(--text)] mb-3">
              Provider Status
            </h2>
            <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)]">
              <table className="min-w-full text-xs">
                <thead className="bg-[var(--bg)]">
                  <tr>
                    <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                      Provider
                    </th>
                    <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                      Latest Status
                    </th>
                    <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                      Target
                    </th>
                    <th className="px-3 py-2 text-right text-[var(--text-muted)] font-medium">
                      HTTP
                    </th>
                    <th className="px-3 py-2 text-right text-[var(--text-muted)] font-medium">
                      Records
                    </th>
                    <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                      Error
                    </th>
                    <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                      Last Run
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {health.providers.length === 0 ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-3 py-8 text-center text-[var(--text-muted)]"
                      >
                        No provider data available yet. Source fetches are
                        logged during ingestion runs.
                      </td>
                    </tr>
                  ) : (
                    health.providers.map((p) => (
                      <tr
                        key={p.provider}
                        className="hover:bg-[var(--bg-glass)] transition-colors"
                      >
                        <td className="px-3 py-2 font-mono text-[var(--text)]">
                          {p.provider}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className="inline-flex items-center gap-1"
                            style={{ color: statusColor(p.latest_status) }}
                          >
                            <span
                              className="inline-block rounded-full"
                              style={{
                                width: 6,
                                height: 6,
                                backgroundColor: statusColor(p.latest_status),
                              }}
                            />
                            {p.latest_status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-[var(--text-2)]">
                          {p.latest_target_type || "—"}
                          {p.latest_target_id && (
                            <span className="text-[var(--text-muted)] ml-1">
                              {p.latest_target_id}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          {p.latest_http_status || "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          {p.latest_records_found !== null
                            ? p.latest_records_found
                            : "—"}
                        </td>
                        <td className="px-3 py-2 max-w-[200px] truncate text-[var(--text-muted)]">
                          {p.latest_error || "—"}
                        </td>
                        <td className="px-3 py-2 text-[var(--text-muted)] whitespace-nowrap">
                          {formatDate(
                            p.latest_started_at ||
                              p.latest_success_at ||
                              p.latest_failure_at
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── Manual Retry Controls ── */}
          <section>
            <h2 className="text-sm font-semibold text-[var(--text)] mb-3">
              Manual Retry
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Retry Grant Week */}
              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4">
                <h3 className="text-xs font-semibold text-[var(--text)] mb-2">
                  Retry Grant Week
                </h3>
                <p className="text-[11px] text-[var(--text-muted)] mb-3">
                  Re-ingest USPTO grants for a Tuesday issue date.
                </p>
                <input
                  type="date"
                  value={grantDate}
                  onChange={(e) => setGrantDate(e.target.value)}
                  className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-xs text-[var(--text)] mb-2 focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                />
                <button
                  onClick={() =>
                    dispatchRetry("/api/v1/admin/ingestion/retry-grant-week", {
                      issue_date: grantDate,
                    })
                  }
                  disabled={!grantDate || retrying !== null}
                  className="w-full rounded-[var(--radius-sm)] bg-[var(--accent)] text-white text-xs font-medium py-1.5 hover:bg-[var(--accent-hover)] disabled:opacity-50 transition-colors"
                >
                  {retrying ===
                  "/api/v1/admin/ingestion/retry-grant-week"
                    ? "Dispatching..."
                    : "Retry Grant Week"}
                </button>
              </div>

              {/* Retry Application Week */}
              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4">
                <h3 className="text-xs font-semibold text-[var(--text)] mb-2">
                  Retry Application Week
                </h3>
                <p className="text-[11px] text-[var(--text-muted)] mb-3">
                  Re-ingest USPTO applications for a Thursday publication date.
                </p>
                <input
                  type="date"
                  value={appDate}
                  onChange={(e) => setAppDate(e.target.value)}
                  className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-xs text-[var(--text)] mb-2 focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                />
                <button
                  onClick={() =>
                    dispatchRetry(
                      "/api/v1/admin/ingestion/retry-application-week",
                      { publication_date: appDate }
                    )
                  }
                  disabled={!appDate || retrying !== null}
                  className="w-full rounded-[var(--radius-sm)] bg-[var(--accent)] text-white text-xs font-medium py-1.5 hover:bg-[var(--accent-hover)] disabled:opacity-50 transition-colors"
                >
                  {retrying ===
                  "/api/v1/admin/ingestion/retry-application-week"
                    ? "Dispatching..."
                    : "Retry App Week"}
                </button>
              </div>

              {/* Catch Up */}
              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4">
                <h3 className="text-xs font-semibold text-[var(--text)] mb-2">
                  Catch Up Weeks
                </h3>
                <p className="text-[11px] text-[var(--text-muted)] mb-3">
                  Ingest all grant + application weeks in a date range.
                </p>
                <div className="flex gap-2 mb-2">
                  <input
                    type="date"
                    value={catchStart}
                    onChange={(e) => setCatchStart(e.target.value)}
                    placeholder="Start"
                    className="flex-1 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-xs text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                  />
                  <input
                    type="date"
                    value={catchEnd}
                    onChange={(e) => setCatchEnd(e.target.value)}
                    placeholder="End (opt)"
                    className="flex-1 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-xs text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                  />
                </div>
                <button
                  onClick={() =>
                    dispatchRetry("/api/v1/admin/ingestion/catch-up", {
                      start_date: catchStart,
                      end_date: catchEnd || null,
                    })
                  }
                  disabled={!catchStart || retrying !== null}
                  className="w-full rounded-[var(--radius-sm)] bg-[var(--warn)] text-black text-xs font-medium py-1.5 hover:opacity-90 disabled:opacity-50 transition-colors"
                >
                  {retrying === "/api/v1/admin/ingestion/catch-up"
                    ? "Dispatching..."
                    : "Run Catch Up"}
                </button>
              </div>
            </div>
            {retryResult && (
              <div className="mt-3 rounded-[var(--radius-sm)] border border-[var(--accent)]/30 bg-[var(--accent-muted)] px-3 py-2 text-xs text-[var(--accent)]">
                {retryResult}
              </div>
            )}
          </section>

          {/* ── Source Fetch History ── */}
          <section>
            <h2 className="text-sm font-semibold text-[var(--text)] mb-3">
              Recent Source Fetches
            </h2>
            {fetchesLoading ? (
              <LoadingState variant="table" count={5} />
            ) : !fetches || fetches.length === 0 ? (
              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-8 text-center text-xs text-[var(--text-muted)]">
                No source fetch records yet. Fetches are logged during ingestion
                runs.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)]">
                <table className="min-w-full text-xs">
                  <thead className="bg-[var(--bg)]">
                    <tr>
                      <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                        Provider
                      </th>
                      <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                        Target
                      </th>
                      <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                        Status
                      </th>
                      <th className="px-3 py-2 text-right text-[var(--text-muted)] font-medium">
                        Records
                      </th>
                      <th className="px-3 py-2 text-right text-[var(--text-muted)] font-medium">
                        Duration
                      </th>
                      <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                        Error
                      </th>
                      <th className="px-3 py-2 text-left text-[var(--text-muted)] font-medium">
                        Time
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {fetches.map((f) => (
                      <tr
                        key={f.id}
                        className="hover:bg-[var(--bg-glass)] transition-colors"
                      >
                        <td className="px-3 py-2 font-mono text-[var(--text)]">
                          {f.provider}
                        </td>
                        <td className="px-3 py-2 text-[var(--text-2)]">
                          {f.target_type}
                          {f.target_id && (
                            <span className="text-[var(--text-muted)] ml-1">
                              {f.target_id.slice(0, 20)}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className="inline-flex items-center gap-1"
                            style={{ color: statusColor(f.status) }}
                          >
                            <span
                              className="inline-block rounded-full"
                              style={{
                                width: 5,
                                height: 5,
                                backgroundColor: statusColor(f.status),
                              }}
                            />
                            {f.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          {f.records_found !== null ? f.records_found : "—"}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-[var(--text-muted)]">
                          {formatDuration(f.duration_ms)}
                        </td>
                        <td className="px-3 py-2 max-w-[180px] truncate text-[var(--text-muted)]">
                          {f.error_message || "—"}
                        </td>
                        <td className="px-3 py-2 text-[var(--text-muted)] whitespace-nowrap">
                          {formatDate(f.started_at || f.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-[var(--radius-md)] border p-3 ${
        highlight
          ? "bg-[var(--warn-bg)] border-[var(--warn)]/30"
          : "bg-[var(--surface)] border-[var(--border)]"
      }`}
    >
      <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
        {label}
      </p>
      <p
        className={`text-lg font-bold mt-0.5 ${
          highlight ? "text-[var(--warn)]" : "text-[var(--text)]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
