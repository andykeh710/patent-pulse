"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { suppliersApi } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import type { CompanyProfile } from "@/lib/types";

function fetcher(url: string) {
  return fetch(url, { credentials: "include" }).then((r) => {
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  });
}

export default function CompanyProfilePage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = use(params);
  const decodedName = decodeURIComponent(name);

  const { data: profile, isLoading, error } = useSWR<CompanyProfile>(
    ["company-profile", decodedName],
    () => suppliersApi.profile(decodedName),
    { revalidateOnFocus: false }
  );

  // Follow state
  const { data: followStatus, mutate: mutateFollow } = useSWR(
    ["company-follow", decodedName],
    () => fetcher(`/api/v1/suppliers/follow/${encodeURIComponent(decodedName)}`),
    { revalidateOnFocus: false }
  );
  const [followLoading, setFollowLoading] = useState(false);

  const handleToggleFollow = async () => {
    setFollowLoading(true);
    try {
      if (followStatus?.is_following) {
        await fetcher(`/api/v1/suppliers/follow/${encodeURIComponent(decodedName)}`, );
        // DELETE
        await fetch(`/api/v1/suppliers/follow/${encodeURIComponent(decodedName)}`, {
          method: "DELETE",
          credentials: "include",
        });
      } else {
        await fetch(`/api/v1/suppliers/follow/${encodeURIComponent(decodedName)}`, {
          method: "POST",
          credentials: "include",
        });
      }
      mutateFollow();
    } finally {
      setFollowLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Company" description="Loading..." />
        <LoadingState variant="detail" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div>
        <PageHeader title="Company not found" />
        <ErrorState
          title="Company not found"
          message={`Could not load data for "${decodedName}".`}
          detail="The company name may not match the assignee records in the patent corpus."
        />
        <Link href="/companies" className="text-sm text-[var(--accent)] hover:underline mt-4 inline-block">
          ← Back to companies
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link href="/companies" className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] mb-2 inline-flex items-center gap-1">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to companies
      </Link>

      {/* Header + follow */}
      <div className="mt-2 mb-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{profile.name}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-sm">
            {profile.country && <Badge variant="default">{profile.country}</Badge>}
            {profile.entity_type && <Badge variant="default">{profile.entity_type}</Badge>}
            <span className="text-[var(--text-muted)]">
              Score: <strong className={profile.supplier_score >= 60 ? "text-[var(--score-high)]" : profile.supplier_score >= 35 ? "text-[var(--warning)]" : "text-[var(--text-muted)]"}>{profile.supplier_score}</strong>
            </span>
          </div>
        </div>
        <button
          onClick={handleToggleFollow}
          disabled={followLoading}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0 ${
            followStatus?.is_following
              ? "bg-[var(--accent-muted)] text-[var(--accent)] border border-[var(--accent)]/30"
              : "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"
          } disabled:opacity-50`}
        >
          {followLoading ? "..." : followStatus?.is_following ? "Following" : "Follow company"}
        </button>
      </div>

      {/* Portfolio summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Patents" value={profile.patent_count} />
        <StatCard label="Active (Granted)" value={profile.active_patent_count} />
        <StatCard label="Expiring Soon" value={profile.expiring_soon_count} highlight={profile.expiring_soon_count > 0} />
        <StatCard label="Tech Areas" value={profile.technology_area_count} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Recent patents */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-4">Recent Patents</h2>
            {profile.recent_patents.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">No recent patents found.</p>
            ) : (
              <div className="space-y-3">
                {profile.recent_patents.map((p) => (
                  <Link
                    key={p.id}
                    href={`/patents/${p.id}`}
                    className="block p-3 rounded-lg hover:bg-[var(--bg-glass-strong)] transition-colors"
                  >
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {p.title || p.doc_id}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-[var(--text-muted)]">
                      <span>{p.doc_id}</span>
                      {p.publication_date && <span>{p.publication_date}</span>}
                      {p.opportunity_score !== null && (
                        <span className="text-[var(--accent)] font-medium">
                          Opp: {p.opportunity_score.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Tech concentration */}
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-4">Technology Focus</h2>
            {profile.top_cpc.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">No CPC data available.</p>
            ) : (
              <div className="space-y-2">
                {profile.top_cpc.map((item) => (
                  <div key={item.cpc} className="flex items-center justify-between">
                    <Badge variant="default" size="sm">{item.cpc}</Badge>
                    <span className="text-xs text-[var(--text-muted)]">{item.count} patents</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top inventors */}
          {profile.top_inventors && profile.top_inventors.length > 0 && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
              <h2 className="font-semibold text-[var(--text-primary)] mb-4">Top Inventors</h2>
              <div className="space-y-2">
                {profile.top_inventors.map((inv) => (
                  <div key={inv.name} className="flex items-center justify-between text-sm">
                    <span className="text-[var(--text-secondary)] truncate">{inv.name}</span>
                    <span className="text-xs text-[var(--text-muted)]">{inv.patent_count} patents</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Signal score */}
          {profile.average_signal_score !== null && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
              <h2 className="font-semibold text-[var(--text-primary)] mb-2">Avg. Signal Score</h2>
              <p className="text-3xl font-bold text-[var(--text-primary)]">{profile.average_signal_score.toFixed(1)}</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Average of opportunity and interest scores across all patents
              </p>
            </div>
          )}

          {/* Expiry exposure */}
          {profile.expiring_soon_count > 0 && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--warning)]/30 p-6">
              <h2 className="font-semibold text-[var(--text-primary)] mb-2">Expiry Exposure</h2>
              <p className="text-2xl font-bold text-[var(--warning)]">{profile.expiring_soon_count}</p>
              <p className="text-sm text-[var(--text-muted)] mt-1">
                Active granted patents estimated to expire within 5 years.
              </p>
              <Link
                href={`/expiry?assignee=${encodeURIComponent(profile.name)}`}
                className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block"
              >
                View in Expiry Radar →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4">
      <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${highlight ? "text-[var(--warning)]" : "text-[var(--text-primary)]"}`}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}
