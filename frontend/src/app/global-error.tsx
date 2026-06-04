"use client";

/* eslint-disable react/no-unescaped-entities */

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body
        style={{
          fontFamily: "Helvetica, Arial, sans-serif",
          background: "#0B0E14",
          color: "#E5E7EB",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          margin: 0,
          padding: 24,
        }}
      >
        <div style={{ maxWidth: 480, textAlign: "center" }}>
          <h1 style={{ fontSize: 20, color: "#F9FAFB", marginBottom: 12 }}>
            Something went wrong
          </h1>
          <p style={{ fontSize: 14, color: "#9CA3AF", lineHeight: 1.6, marginBottom: 24 }}>
            An unexpected error occurred. We&apos;ll look into it.
          </p>
          <button
            onClick={reset}
            style={{
              background: "#1E2433",
              color: "#6B8CFF",
              border: "none",
              padding: "10px 24px",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
