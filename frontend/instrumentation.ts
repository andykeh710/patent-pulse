// PR8: Sentry instrumentation hook (server-side + edge).
// Replaces sentry.server.config.ts and sentry.edge.config.ts per
// @sentry/nextjs v8 best practices for Next.js 15.

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (dsn) {
      const Sentry = await import("@sentry/nextjs");
      Sentry.init({
        dsn,
        environment: process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
        tracesSampleRate: 0.1,
      });
    }
  }
}
