import type { Metadata } from "next";
import { BRAND, COPY } from "@/lib/brand";
import "./globals.css";
import { AuthProvider } from "@/lib/AuthContext";

export const metadata: Metadata = {
  title: {
    default: `${BRAND.name} — ${COPY.tagline}`,
    template: `%s — ${BRAND.name}`,
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
    <html lang="en">
      <body className="antialiased bg-white min-h-screen font-[system-ui,-apple-system,BlinkMacSystemFont,'Segoe_UI',Roboto,'Helvetica_Neue',Arial,sans-serif]">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
