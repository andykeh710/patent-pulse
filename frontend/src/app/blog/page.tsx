import { Metadata } from "next";
import Link from "next/link";

interface BlogPost {
  slug: string;
  title: string;
  subtitle: string | null;
  excerpt: string | null;
  hero_image_url: string | null;
  author_name: string;
  tags: string[];
  published_at: string | null;
}

async function getPosts(): Promise<BlogPost[]> {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    const res = await fetch(`${apiBase}/api/v1/blog`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export const metadata: Metadata = {
  title: "Blog — patent intelligence, filing trends, invention analysis | Invention Index 8",
  description: "Articles on patent intelligence, filing trends, and invention analysis from the team at Invention Index 8.",
  openGraph: {
    title: "Blog — Invention Index 8",
    description: "Patent intelligence, filing trends, and invention analysis.",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

export default async function BlogListPage() {
  const posts = await getPosts();

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <div className="border-b border-[var(--border-subtle)] px-6 py-3">
        <Link href="/" className="text-sm text-[var(--accent)] hover:underline">
          ← Invention Index 8
        </Link>
      </div>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Blog</h1>
        <p className="text-[var(--text-secondary)] mb-10">
          Patent intelligence, filing trends, and invention analysis.
        </p>

        {posts.length === 0 ? (
          <p className="text-[var(--text-muted)]">No posts yet. Check back soon.</p>
        ) : (
          <div className="space-y-8">
            {posts.map((post) => (
              <article
                key={post.slug}
                className="p-6 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] hover:border-[var(--accent)] transition-colors"
              >
                <Link href={`/blog/${post.slug}`}>
                  <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-1 hover:text-[var(--accent)]">
                    {post.title}
                  </h2>
                </Link>
                {post.subtitle && (
                  <p className="text-sm text-[var(--text-secondary)] mb-3">{post.subtitle}</p>
                )}
                {post.excerpt && (
                  <p className="text-sm text-[var(--text-muted)] mb-3 line-clamp-2">
                    {post.excerpt}
                  </p>
                )}
                <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                  <span>{post.author_name}</span>
                  {post.published_at && (
                    <>
                      <span>·</span>
                      <span>{new Date(post.published_at).toLocaleDateString("en-US", {
                        year: "numeric", month: "long", day: "numeric",
                      })}</span>
                    </>
                  )}
                  {post.tags.length > 0 && (
                    <div className="flex gap-1.5">
                      {post.tags.slice(0, 3).map((t) => (
                        <span key={t} className="px-1.5 py-0.5 rounded bg-[var(--bg-glass)] text-[10px]">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
