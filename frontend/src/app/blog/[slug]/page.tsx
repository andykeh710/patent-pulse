import { Metadata } from "next";
import Link from "next/link";

interface BlogPost {
  slug: string;
  title: string;
  subtitle: string | null;
  excerpt: string | null;
  content_markdown: string;
  hero_image_url: string | null;
  author_name: string;
  author_role: string | null;
  tags: string[];
  related_patent_doc_ids: string[];
  related_theme_slugs: string[];
  related_company_names: string[];
  published_at: string | null;
}

async function getPost(slug: string): Promise<BlogPost | null> {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";
    const res = await fetch(`${apiBase}/api/v1/blog/${slug}`, { next: { revalidate: 300 } });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return { title: "Post not found | Invention Index 8" };

  return {
    title: `${post.title} | Invention Index 8`,
    description: post.excerpt || post.subtitle || `Read ${post.title} on Invention Index 8.`,
    openGraph: {
      title: post.title,
      description: post.excerpt || post.subtitle || "",
      type: "article",
      images: post.hero_image_url ? [post.hero_image_url] : [],
      authors: [post.author_name],
      publishedTime: post.published_at || undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.excerpt || "",
      images: post.hero_image_url ? [post.hero_image_url] : [],
    },
    alternates: { canonical: `/blog/${slug}` },
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPost(slug);

  if (!post) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="text-center px-4">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Post not found</h1>
          <Link href="/blog" className="text-[var(--accent)] hover:underline">
            ← Back to blog
          </Link>
        </div>
      </div>
    );
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.excerpt || post.subtitle || "",
    author: { "@type": "Person", name: post.author_name },
    datePublished: post.published_at,
    publisher: { "@type": "Organization", name: "Invention Index 8" },
    url: `https://inventionindex8.com/blog/${slug}`,
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <div className="border-b border-[var(--border-subtle)] px-6 py-3">
        <Link href="/blog" className="text-sm text-[var(--accent)] hover:underline">
          ← Blog
        </Link>
      </div>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="lg:grid lg:grid-cols-[1fr_240px] lg:gap-12">
          {/* Article */}
          <article>
            <header className="mb-8">
              <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">{post.title}</h1>
              {post.subtitle && (
                <p className="text-lg text-[var(--text-secondary)]">{post.subtitle}</p>
              )}
              <div className="flex items-center gap-2 mt-4 text-sm text-[var(--text-muted)]">
                <span>{post.author_name}</span>
                {post.author_role && <span>· {post.author_role}</span>}
                {post.published_at && (
                  <span>· {new Date(post.published_at).toLocaleDateString("en-US", {
                    year: "numeric", month: "long", day: "numeric",
                  })}</span>
                )}
              </div>
              {post.tags.length > 0 && (
                <div className="flex gap-1.5 mt-3">
                  {post.tags.map((t) => (
                    <span key={t} className="px-2 py-0.5 rounded bg-[var(--bg-glass)] text-xs text-[var(--text-muted)]">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </header>

            {post.hero_image_url && (
              <img
                src={post.hero_image_url}
                alt={post.title}
                className="w-full rounded-lg mb-8"
              />
            )}

            {/* Markdown content */}
            <div
              className="prose prose-invert max-w-none
                prose-headings:text-[var(--text-primary)]
                prose-p:text-[var(--text-secondary)]
                prose-a:text-[var(--accent)]
                prose-strong:text-[var(--text-primary)]
                prose-code:text-[var(--accent)]
                prose-code:bg-[var(--bg-surface)]
                prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                prose-pre:bg-[var(--bg-surface)]
                prose-pre:border prose-pre:border-[var(--border-subtle)]
                prose-li:text-[var(--text-secondary)]"
              dangerouslySetInnerHTML={{ __html: mdToHtml(post.content_markdown) }}
            />

            {/* End CTA */}
            <div className="border-t border-[var(--border-subtle)] pt-8 mt-12 text-center">
              <p className="text-[var(--text-secondary)] mb-3">
                Track patent activity yourself.
              </p>
              <Link
                href="/login"
                className="inline-flex px-6 py-3 rounded-lg bg-[var(--accent)] text-white font-semibold hover:bg-[var(--accent-hover)] transition-colors"
              >
                Free signup →
              </Link>
            </div>
          </article>

          {/* Sidebar: related */}
          <aside className="mt-8 lg:mt-0 space-y-6">
            {(post.related_patent_doc_ids.length > 0 ||
              post.related_theme_slugs.length > 0 ||
              post.related_company_names.length > 0) && (
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3 uppercase tracking-wide">
                  Related on II8
                </h3>

                {post.related_patent_doc_ids.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-[var(--text-muted)] mb-2">Patents</p>
                    {post.related_patent_doc_ids.map((docId) => (
                      <Link
                        key={docId}
                        href={`/patents/${docId}`}
                        className="block text-sm text-[var(--accent)] hover:underline mb-1"
                      >
                        {docId}
                      </Link>
                    ))}
                  </div>
                )}

                {post.related_theme_slugs.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-[var(--text-muted)] mb-2">Themes</p>
                    {post.related_theme_slugs.map((s) => (
                      <Link
                        key={s}
                        href={`/t/${s}`}
                        className="block text-sm text-[var(--accent)] hover:underline mb-1"
                      >
                        {s.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </Link>
                    ))}
                  </div>
                )}

                {post.related_company_names.length > 0 && (
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-2">Companies</p>
                    {post.related_company_names.map((name) => {
                      const cSlug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
                      return (
                        <Link
                          key={name}
                          href={`/c/${cSlug}`}
                          className="block text-sm text-[var(--accent)] hover:underline mb-1"
                        >
                          {name}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}

// Simple markdown→HTML for basic formatting (headings, paragraphs, links, bold, code)
function mdToHtml(md: string): string {
  let html = md
    // Headings
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    // Bold + italic
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    // Paragraphs (blank-line separated)
    .replace(/\n\n/g, "</p><p>")
    // Unordered lists
    .replace(/^- (.+)$/gm, "<li>$1</li>");
  return `<p>${html}</p>`;
}
