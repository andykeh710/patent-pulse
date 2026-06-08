"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { authApi } from "@/lib/api";

function VerifyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"verifying" | "error">("verifying");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("Missing token. Check your magic link and try again.");
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const res = await authApi.verify(token);
        const data = await res.json();
        if (!data.ok) {
          throw new Error("Verify did not return ok");
        }
        if (!cancelled) {
          // Check onboarding status
          const statusRes = await fetch("/api/v1/onboarding/status", { credentials: "include" });
          const statusData = await statusRes.json();
          router.push(statusData.onboarded ? "/today" : "/onboarding");
        }
      } catch {
        if (!cancelled) {
          setStatus("error");
          setErrorMessage(
            "This link is invalid or has expired. Request a new one."
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token, router]);

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
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Sign-in failed</h1>
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
