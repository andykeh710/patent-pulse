import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { BRAND, COPY } from "@/lib/brand";
import "@/styles/tokens.css";
import "./globals.css";
import { AuthProvider } from "@/lib/AuthContext";
import { ThemeProvider } from "@/lib/ThemeProvider";

export const metadata: Metadata = {
  title: {
    default: `${BRAND.name}: ${COPY.tagline}`,
    template: `%s: ${BRAND.name}`,
  },
  description: COPY.description,
  metadataBase: new URL(BRAND.url),
  openGraph: {
    title: BRAND.name,
    description: COPY.description,
    siteName: BRAND.name,
    images: [{ url: "/og-image.svg", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: BRAND.name,
    description: COPY.description,
    images: ["/og-image.svg"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                var t = localStorage.getItem('theme');
                if (t === 'light') document.documentElement.setAttribute('data-theme', 'light');
                else if (t === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
              })();
            `,
          }}
        />
      </head>
      <body className="antialiased bg-[var(--bg-base)] min-h-screen text-[var(--text-primary)]">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[var(--z-tooltip)] focus:px-4 focus:py-2 focus:bg-[var(--accent)] focus:text-white focus:rounded-[var(--radius-md)]">
          Skip to content
        </a>
        <ThemeProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
