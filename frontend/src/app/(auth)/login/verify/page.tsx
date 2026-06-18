"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";

// Prevent static prerendering — this page must read ?token= from the URL
export const dynamic = "force-dynamic";

function VerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"verifying" | "error" | "onboarding_error">("verifying");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("Missing token. Check your magic link and try again.");
      return;
    }

    let cancelled = false;
    (async () => {
      // Phase 1: Verify the token
      try {
        const res = await authApi.verify(token);
        const data = await res.json();
        if (!data.ok) {
          setStatus("error");
          setErrorMessage("This link is invalid or has expired. Request a new one.");
          return;
        }
      } catch {
        if (!cancelled) {
          setStatus("error");
          setErrorMessage("This link is invalid or has expired. Request a new one.");
        }
        return;
      }

      if (cancelled) return;

      // Brief delay to ensure Set-Cookie from verify is fully committed
      // before the middleware checks for it on the next navigation
      await new Promise((r) => setTimeout(r, 300));

      // Phase 2: Check onboarding status (requires the cookie from phase 1)
      try {
        const statusRes = await fetch("/api/v1/onboarding/status", { credentials: "include" });
        if (!statusRes.ok) throw new Error("Onboarding check failed");
        const statusData = await statusRes.json();
        // Use window.location for a full navigation — ensures the HttpOnly
        // cookie is sent in the request headers
        window.location.href = statusData.onboarded ? "/today" : "/onboarding";
      } catch {
        if (!cancelled) {
          setStatus("onboarding_error");
          setErrorMessage("Sign-in succeeded but we couldn't load your preferences. Please try refreshing the page.");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token]);

  if (status === "verifying") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
        <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-8 max-w-md w-full text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto" />
          <p className="text-[var(--text-secondary)]">Verifying your magic link…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
      <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-8 max-w-md w-full text-center space-y-4">
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">
          {status === "onboarding_error" ? "Almost there" : "Sign-in failed"}
        </h1>
        <p className="text-[var(--text-secondary)]">{errorMessage}</p>
        <a href="/login" className="text-sm text-[var(--accent)] hover:underline">
          Try again
        </a>
      </div>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-[var(--text-muted)]">Loading…</p>
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
