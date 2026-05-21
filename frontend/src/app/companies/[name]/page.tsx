"use client";

import { use } from "react";
import Link from "next/link";
import useSWR from "swr";
import { suppliersApi } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { CompanyProfile } from "@/lib/types";

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

  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-64 mb-4" />
        <Skeleton className="h-6 w-96 mb-8" />
        <div className="grid md:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Company not found: {decodedName}</p>
        <Link href="/suppliers" className="text-primary-600 mt-2 inline-block">
          Back to companies
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link href="/suppliers" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-flex items-center gap-1">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to companies
      </Link>

      <div className="mt-2 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{profile.name}</h1>
        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500">
          {profile.country && <Badge variant="default">{profile.country}</Badge>}
          {profile.entity_type && <Badge variant="default">{profile.entity_type}</Badge>}
          <span>Score: <strong className={profile.supplier_score >= 60 ? "text-green-600" : profile.supplier_score >= 35 ? "text-yellow-600" : "text-gray-600"}>{profile.supplier_score}</strong></span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Patents" value={profile.patent_count} />
        <StatCard label="Active (Granted)" value={profile.active_patent_count} />
        <StatCard label="Expiring Soon" value={profile.expiring_soon_count} highlight={profile.expiring_soon_count > 0} />
        <StatCard label="Tech Areas" value={profile.technology_area_count} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent Patents */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Recent Patents</h2>
            {profile.recent_patents.length === 0 ? (
              <p className="text-sm text-gray-500">No recent patents found.</p>
            ) : (
              <div className="space-y-3">
                {profile.recent_patents.map((p) => (
                  <Link
                    key={p.id}
                    href={`/patents/${p.id}`}
                    className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {p.title || p.doc_id}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{p.doc_id}</span>
                      {p.publication_date && <span>{p.publication_date}</span>}
                      {p.opportunity_score !== null && (
                        <span className="text-primary-600 font-medium">
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
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Top Technology Areas</h2>
            {profile.top_cpc.length === 0 ? (
              <p className="text-sm text-gray-500">No CPC data available.</p>
            ) : (
              <div className="space-y-2">
                {profile.top_cpc.map((item) => (
                  <div key={item.cpc} className="flex items-center justify-between">
                    <Badge variant="default" size="sm">{item.cpc}</Badge>
                    <span className="text-xs text-gray-500">{item.count} patents</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {profile.average_signal_score !== null && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-2">Avg. Signal Score</h2>
              <p className="text-3xl font-bold text-gray-900">{profile.average_signal_score.toFixed(1)}</p>
              <p className="text-xs text-gray-500 mt-1">
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
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${highlight ? "text-amber-600" : "text-gray-900"}`}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}
