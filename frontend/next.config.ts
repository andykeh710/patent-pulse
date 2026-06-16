import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: "font-src 'self' data:; default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;",
          },
        ],
      },
    ];
  },
  async redirects() {
    return [
      {
        source: "/suppliers",
        destination: "/companies",
        permanent: true,
      },
    ];
  },
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

// PR8: Sentry wrapper — source maps disabled for V1.
// The SDK initialisation itself is gated by NEXT_PUBLIC_SENTRY_DSN
// in sentry.*.config.ts; when the DSN is unset the SDK silently noops.
export default withSentryConfig(nextConfig, {
  silent: true,
  sourcemaps: {
    disable: true,
  },
});
