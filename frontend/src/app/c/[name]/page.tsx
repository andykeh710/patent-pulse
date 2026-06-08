import { Metadata } from "next";
import Link from "next/link";

// ── types ────────────────────────────────────────────────────────────

interface CompanyProfile {
  supplier_name: string;
  patent_count: number;
  active_patent_count: number;
  expiring_soon_count: number;
  technology_area_count: number;
  average_signal_score: number | null;
  supplier_score: number;
  top_cpc: { cpc: string; count: number }[];
  recent_patents: { doc_id: string; title: string; publication_date: string; score: number | null }[];
}

// ── data fetching ────────────────────────────────────────────────────

async function getCompany(name: string): Promise<CompanyProfile | null> {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    const res = await fetch(`${apiBase}/api/v1/suppliers/profile/${encodeURIComponent(name)}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── metadata ─────────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: Promise<{ name: string }>;
}): Promise<Metadata> {
  const { name } = await params;
  const profile = await getCompany(name);
  const displayName = name.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  if (!profile) {
    return {
      title: `${displayName} — Company not found | Invention Index 8`,
      description: "Company not found in our patent database.",
    };
  }

    return {
      title: `${displayName} — patent activity, filing trends, key inventions | Invention Index 8`,
      description: `${displayName} has ${profile.patent_count} patents with ${profile.active_patent_count} active. Explore filing trends, top CPC areas, and key inventions on Invention Index 8.`,
      openGraph: {
        title: `${displayName} — ${profile.patent_count} patents`,
        description: `Explore ${displayName}'s patent portfolio — top CPC areas, filing trends, and key inventions.`,
        images: [`/api/v1/share/company/${name}.png`],
        url: `https://inventionindex8.com/c/${name}`,
        type: "website",
      },
      twitter: {
        card: "summary_large_image",
        title: `${displayName} — ${profile.patent_count} patents`,
        description: `Explore ${displayName}'s patent portfolio on Invention Index 8.`,
        images: [`/api/v1/share/company/${name}.png`],
      },
      alternates: {
        canonical: `/c/${name}`,
      },
    };
}

// ── page ─────────────────────────────────────────────────────────────

export default async function PublicCompanyPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const profile = await getCompany(name);
  const displayName = name.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  if (!profile) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="text-center px-4">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Company not found</h1>
          <p className="text-[var(--text-muted)]">
            We couldn&apos;t find patent data for &quot;{displayName}&quot;.
          </p>
          <Link href="/" className="text-[var(--accent)] hover:underline mt-4 inline-block">
            ← Back to Invention Index 8
          </Link>
        </div>
      </div>
    );
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: displayName,
    url: `https://inventionindex8.com/c/${name}`,
    description: `${displayName} patent portfolio — ${profile.patent_count} patents on Invention Index 8. Explore top CPC areas, filing trends, and key inventions.`,
    identifier: name,
    sameAs: [],
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      {/* JSON-LD */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Header bar */}
      <div className="border-b border-[var(--border-subtle)] px-6 py-3">
        <Link href="/" className="text-sm text-[var(--accent)] hover:underline">
          ← Invention Index 8
        </Link>
      </div>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">
            {displayName}
          </h1>
          <p className="text-lg text-[var(--text-secondary)]">
            {profile.patent_count.toLocaleString()} patents
            {" · "}
            {profile.active_patent_count.toLocaleString()} active
            {profile.expiring_soon_count > 0 &&
              ` · ${profile.expiring_soon_count} expiring within 5 years`}
          </p>
        </div>

        {/* Stat tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <StatTile label="Total Patents" value={profile.patent_count.toLocaleString()} />
          <StatTile label="Active" value={profile.active_patent_count.toLocaleString()} />
          <StatTile label="Tech Areas" value={String(profile.technology_area_count)} />
          <StatTile
            label="Avg Signal Score"
            value={profile.average_signal_score != null ? profile.average_signal_score.toFixed(1) : "—"}
          />
        </div>

        {/* Top CPC areas */}
        {profile.top_cpc.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">Top CPC Areas</h2>
            <div className="flex flex-wrap gap-2">
              {profile.top_cpc.slice(0, 10).map((cpc) => (
                <span
                  key={cpc.cpc}
                  className="px-3 py-1 rounded-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)]"
                >
                  {cpc.cpc} ({cpc.count})
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Recent patents */}
        {profile.recent_patents.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">
              Recent Patents
            </h2>
            <div className="space-y-2">
              {profile.recent_patents.slice(0, 10).map((p) => (
                <div
                  key={p.doc_id}
                  className="p-3 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex justify-between items-start gap-4"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {p.title || p.doc_id}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{p.doc_id}</p>
                  </div>
                  <span className="text-xs text-[var(--text-muted)] shrink-0">
                    {p.publication_date}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Footer CTA */}
        <div className="border-t border-[var(--border-subtle)] pt-8 mt-8 text-center">
          <p className="text-[var(--text-secondary)] mb-3">
            Track {displayName}&apos;s patent activity with a free account.
          </p>
          <Link
            href="/login"
            className="inline-flex px-6 py-3 rounded-lg bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] transition-colors"
          >
            Get started free
          </Link>
        </div>
      </main>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
      <p className="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
