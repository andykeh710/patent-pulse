"use client";

import { use } from "react";
import Link from "next/link";
import useSWR from "swr";
import { suppliersApi } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import type { CompanyProfile } from "@/lib/types";

export default function CompanyProfilePage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = use(params);
  const decodedName = decodeURIComponent(name);

  const { data: profile, isLoading, error } = useSWR<CompanyProfile>(
    typeof window === "undefined" ? null : ["company-profile", decodedName],
    typeof window === "undefined" ? null : () => suppliersApi.profile(decodedName),
    { revalidateOnFocus: false }
  );

  if (typeof window === "undefined") {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 bg-[var(--bg-surface)] animate-pulse rounded" />
        <div className="h-6 w-96 bg-[var(--bg-surface)] animate-pulse rounded" />
        <div className="grid md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-[var(--bg-surface)] animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 bg-[var(--bg-surface)] animate-pulse rounded" />
        <div className="h-6 w-96 bg-[var(--bg-surface)] animate-pulse rounded" />
        <div className="grid md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-[var(--bg-surface)] animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="text-center py-12">
        <p className="text-[var(--text-muted)]">Company not found: {decodedName}</p>
        <Link href="/companies" className="text-[var(--accent)] mt-2 inline-block hover:underline">
          Back to companies
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

      <div className="mt-2 mb-6">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{profile.name}</h1>
        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-[var(--text-muted)]">
          {profile.country && <Badge variant="default">{profile.country}</Badge>}
          {profile.entity_type && <Badge variant="default">{profile.entity_type}</Badge>}
          <span>Score: <strong className={profile.supplier_score >= 60 ? "text-[var(--score-high)]" : profile.supplier_score >= 35 ? "text-[var(--warning)]" : "text-[var(--text-muted)]"}>{profile.supplier_score}</strong></span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Patents" value={profile.patent_count} />
        <StatCard label="Active (Granted)" value={profile.active_patent_count} />
        <StatCard label="Expiring Soon" value={profile.expiring_soon_count} highlight={profile.expiring_soon_count > 0} />
        <StatCard label="Tech Areas" value={profile.technology_area_count} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
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
                    className="block p-3 bg-[var(--bg-surface)] rounded-lg hover:bg-[var(--bg-glass-strong)] transition-colors"
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

        <div className="space-y-6">
          <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
            <h2 className="font-semibold text-[var(--text-primary)] mb-4">Top Technology Areas</h2>
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

          {profile.average_signal_score !== null && (
            <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-6">
              <h2 className="font-semibold text-[var(--text-primary)] mb-2">Avg. Signal Score</h2>
              <p className="text-3xl font-bold text-[var(--text-primary)]">{profile.average_signal_score.toFixed(1)}</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Average of opportunity and interest scores across all patents
              </p>
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
