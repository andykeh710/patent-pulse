import { Metadata } from "next";
import Link from "next/link";

// ── types ────────────────────────────────────────────────────────────

interface ThemeData {
  id: string;
  name: string;
  description: string;
  cpc_prefixes: string[];
  keywords: string[];
  stats: {
    total_patents: number;
    recent_patents_30d: number;
    top_assignees: { name: string; count: number }[];
    top_cpc: { cpc: string; count: number }[];
  } | null;
}

// ── data fetching ────────────────────────────────────────────────────

async function getTheme(slug: string): Promise<ThemeData | null> {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    // First get theme by name (slug)
    const themesRes = await fetch(`${apiBase}/api/v1/themes`, {
      next: { revalidate: 3600 },
    });
    if (!themesRes.ok) return null;
    const themes: { id: string; name: string; description: string; cpc_prefixes: string[]; keywords: string[] }[] =
      await themesRes.json();

    const theme = themes.find(
      (t) => t.name.toLowerCase().replace(/[^a-z0-9]+/g, "-") === slug
    );
    if (!theme) return null;

    // Get stats
    const statsRes = await fetch(`${apiBase}/api/v1/themes/${theme.id}/stats`, {
      next: { revalidate: 3600 },
    });
    const stats = statsRes.ok ? await statsRes.json() : null;

    return { ...theme, stats };
  } catch {
    return null;
  }
}

// ── metadata ─────────────────────────────────────────────────────────

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const theme = await getTheme(slug);

  if (!theme) {
    return {
      title: "Theme not found | Invention Index 8",
    };
  }

  const desc = theme.description || `Explore ${theme.name} patent activity — ${theme.stats?.total_patents || 0} patents on Invention Index 8.`;

  return {
    title: `${theme.name} — patents, trends, top companies | Invention Index 8`,
    description: desc,
    openGraph: {
      title: `${theme.name} — patent trends`,
      description: desc,
      images: [`/api/v1/share/trend/${(theme.cpc_prefixes || ["G06N"])[0]}.png`],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${theme.name} — patent trends`,
      description: desc,
      images: [`/api/v1/share/trend/${(theme.cpc_prefixes || ["G06N"])[0]}.png`],
    },
    alternates: {
      canonical: `/t/${slug}`,
    },
  };
}

// ── page ─────────────────────────────────────────────────────────────

export default async function PublicThemePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const theme = await getTheme(slug);

  if (!theme) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="text-center px-4">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Theme not found</h1>
          <Link href="/" className="text-[var(--accent)] hover:underline mt-4 inline-block">
            ← Back to Invention Index 8
          </Link>
        </div>
      </div>
    );
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `${theme.name} — Patent Activity`,
    description: theme.description || `Patent trends in ${theme.name}`,
    url: `https://inventionindex8.com/t/${slug}`,
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="border-b border-[var(--border-subtle)] px-6 py-3">
        <Link href="/" className="text-sm text-[var(--accent)] hover:underline">
          ← Invention Index 8
        </Link>
      </div>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">{theme.name}</h1>
          {theme.description && (
            <p className="text-[var(--text-secondary)]">{theme.description}</p>
          )}
        </div>

        {/* Stats */}
        {theme.stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            <StatTile label="Total Patents" value={theme.stats.total_patents.toLocaleString()} />
            <StatTile label="Last 30 Days" value={theme.stats.recent_patents_30d.toLocaleString()} />
            <StatTile label="CPC Areas" value={String(theme.cpc_prefixes.length)} />
            <StatTile label="Keywords" value={String(theme.keywords.length)} />
          </div>
        )}

        {/* Top assignees */}
        {theme.stats?.top_assignees && theme.stats.top_assignees.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">
              Top Companies
            </h2>
            <div className="space-y-2">
              {theme.stats.top_assignees.slice(0, 10).map((a) => (
                <Link
                  key={a.name}
                  href={`/c/${a.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                  className="flex items-center justify-between p-3 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] hover:border-[var(--accent)] transition-colors"
                >
                  <span className="text-sm text-[var(--text-primary)]">{a.name}</span>
                  <span className="text-xs text-[var(--text-muted)]">{a.count} patents</span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* CPC areas */}
        {theme.cpc_prefixes.length > 0 && (
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">
              CPC Areas
            </h2>
            <div className="flex flex-wrap gap-2">
              {theme.cpc_prefixes.map((cpc) => (
                <span
                  key={cpc}
                  className="px-3 py-1 rounded-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-sm text-[var(--text-secondary)]"
                >
                  {cpc}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Footer CTA */}
        <div className="border-t border-[var(--border-subtle)] pt-8 mt-8 text-center">
          <p className="text-[var(--text-secondary)] mb-3">
            Track {theme.name} patents with a free account.
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
