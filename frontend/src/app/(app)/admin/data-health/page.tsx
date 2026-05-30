"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface OfficeHealth {
  office: string;
  total: number;
  abstract_pct: number;
  claims_pct: number;
  figure_url_pct: number;
  embedding_pct: number;
  tags_pct: number;
  summary_pct: number;
}

interface DataHealth {
  total_patents: number;
  by_office: OfficeHealth[];
  citations: { total: number; forward_pct: number; backward_pct: number };
  family: { with_family_id: number; with_family_members: number };
  recent_failures: {
    id: string;
    provider: string;
    target_type: string;
    target_id: string | null;
    error_message: string | null;
    created_at: string | null;
  }[];
  latest_success_by_provider: Record<string, string | null>;
}

const PCT_BAR = (pct: number) => {
  const color = pct > 80 ? "bg-green-500" : pct > 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 w-10 text-right">{pct}%</span>
    </div>
  );
};

export default function DataHealthPage() {
  const [data, setData] = useState<DataHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/v1/admin/data-health");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setData(await res.json());
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <p className="text-gray-500">Loading data health...</p>;
  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!data) return <p className="text-gray-500">No data available.</p>;

  return (
    <div className="max-w-6xl">
      <div className="flex items-center gap-4 mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Data Health</h1>
        <Link
          href="/admin"
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Admin
        </Link>
      </div>

      {/* Total */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Patents" value={data.total_patents.toLocaleString()} />
        <StatCard
          label="With Citations (fwd)"
          value={`${data.citations.forward_pct}%`}
        />
        <StatCard
          label="With Family ID"
          value={data.family.with_family_id.toLocaleString()}
        />
        <StatCard
          label="Recent Failures"
          value={data.recent_failures.length.toString()}
          warn={data.recent_failures.length > 0}
        />
      </div>

      {/* By office */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">By Office</h2>
      <div className="space-y-4 mb-8">
        {data.by_office.map((o) => (
          <div
            key={o.office}
            className="bg-white border border-gray-200 rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-semibold text-gray-900">{o.office}</span>
              <span className="text-sm text-gray-500">
                {o.total.toLocaleString()} patents
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <Metric label="Abstract" pct={o.abstract_pct} />
              <Metric label="Claims" pct={o.claims_pct} />
              <Metric label="Figures" pct={o.figure_url_pct} />
              <Metric label="Embeddings" pct={o.embedding_pct} />
              <Metric label="Tags" pct={o.tags_pct} />
              <Metric label="Summaries" pct={o.summary_pct} />
            </div>
          </div>
        ))}
      </div>

      {/* Provider last success */}
      {Object.keys(data.latest_success_by_provider).length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Last Successful Fetch
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            {Object.entries(data.latest_success_by_provider).map(
              ([provider, ts]) => (
                <div
                  key={provider}
                  className="bg-white border border-gray-200 rounded-lg p-3"
                >
                  <p className="text-xs text-gray-500">{provider}</p>
                  <p className="text-sm font-mono text-gray-700">
                    {ts ? new Date(ts).toLocaleString() : "never"}
                  </p>
                </div>
              )
            )}
          </div>
        </>
      )}

      {/* Recent failures */}
      {data.recent_failures.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-red-700 mb-4">
            Recent Failures
          </h2>
          <div className="space-y-2 mb-8">
            {data.recent_failures.map((f) => (
              <div
                key={f.id}
                className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm"
              >
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-mono font-semibold text-red-800">
                    {f.provider}
                  </span>
                  <span className="text-red-600">{f.target_type}</span>
                  {f.target_id && (
                    <span className="text-red-500 font-mono">{f.target_id}</span>
                  )}
                  <span className="text-red-400 text-xs">
                    {f.created_at ? new Date(f.created_at).toLocaleString() : ""}
                  </span>
                </div>
                {f.error_message && (
                  <p className="text-red-700 text-xs truncate">
                    {f.error_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  warn,
}: {
  label: string;
  value: string;
  warn?: boolean;
}) {
  return (
    <div
      className={`bg-white border rounded-lg p-4 ${
        warn ? "border-amber-300 bg-amber-50" : "border-gray-200"
      }`}
    >
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${warn ? "text-amber-700" : "text-gray-900"}`}>
        {value}
      </p>
    </div>
  );
}

function Metric({ label, pct }: { label: string; pct: number }) {
  return (
    <div>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      {PCT_BAR(pct)}
    </div>
  );
}
