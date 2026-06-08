"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { BRAND } from "@/lib/brand";
import { StepRole } from "@/components/onboarding/StepRole";
import { StepIndustry } from "@/components/onboarding/StepIndustry";
import { StepInterests } from "@/components/onboarding/StepInterests";
import { StepConfirm, type Suggestion } from "@/components/onboarding/StepConfirm";

type Step = "role" | "industry" | "interests" | "confirm";

const STEP_LABELS: Record<Step, string> = {
  role: "Your role",
  industry: "Your industry",
  interests: "Your interests",
  confirm: "Confirm",
};

export default function OnboardingPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [step, setStep] = useState<Step>("role");
  const [role, setRole] = useState("");
  const [industry, setIndustry] = useState("");
  const [interests, setInterests] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  if (authLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
        <p className="text-[var(--text-muted)]">Loading…</p>
      </div>
    );
  }

  const totalSteps = 4;
  const stepIndex = ["role", "industry", "interests", "confirm"].indexOf(step) + 1;
  const steps: Step[] = ["role", "industry", "interests", "confirm"];

  const handleNext = async () => {
    if (step === "role" && !role) return;
    if (step === "industry" && !industry) return;
    if (step === "interests") {
      setLoading(true);
      setError("");
      try {
        const res = await fetch("/api/v1/onboarding/complete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ persona: role, industry_focus: industry, interests_freetext: interests }),
        });
        if (!res.ok) throw new Error("Failed to get suggestions");
        const data = await res.json();
        setSuggestions({
          companies: data.suggested_companies || [],
          themes: data.suggested_themes || [],
        });
        setStep("confirm");
      } catch {
        setError("Something went wrong. Please try again.");
      } finally {
        setLoading(false);
      }
      return;
    }
    if (step === "confirm") {
      setLoading(true);
      setError("");
      try {
        const companyIds = suggestions?.companies.map((c) => c.normalized_name) || [];
        const themeIds = suggestions?.themes.map((t) => t.id) || [];
        const res = await fetch("/api/v1/onboarding/confirm", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ company_ids: companyIds, theme_ids: themeIds }),
        });
        if (!res.ok) throw new Error("Failed to confirm");
        router.push("/today?tour=1");
      } catch {
        setError("Something went wrong. Please try again.");
      } finally {
        setLoading(false);
      }
      return;
    }
    const idx = steps.indexOf(step);
    if (idx < steps.length - 1) setStep(steps[idx + 1]);
  };

  const handleBack = () => {
    const idx = steps.indexOf(step);
    if (idx > 0) setStep(steps[idx - 1]);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)] px-4">
      <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border-subtle)] p-8 max-w-lg w-full">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-[var(--text-muted)]">
              Step {stepIndex} of {totalSteps}
            </span>
            <span className="text-sm font-medium text-[var(--text-primary)]">
              {STEP_LABELS[step]}
            </span>
          </div>
          <div className="h-1 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--accent)] rounded-full transition-all duration-300"
              style={{ width: `${(stepIndex / totalSteps) * 100}%` }}
            />
          </div>
        </div>

        {step === "role" && <StepRole selected={role} onSelect={setRole} />}
        {step === "industry" && <StepIndustry selected={industry} onSelect={setIndustry} />}
        {step === "interests" && <StepInterests value={interests} onChange={setInterests} />}
        {step === "confirm" && (
          <StepConfirm
            suggestions={suggestions}
            onRemoveCompany={(name) =>
              setSuggestions((prev) =>
                prev ? { ...prev, companies: prev.companies.filter((c) => c.normalized_name !== name) } : null
              )
            }
            onRemoveTheme={(id) =>
              setSuggestions((prev) =>
                prev ? { ...prev, themes: prev.themes.filter((t) => t.id !== id) } : null
              )
            }
          />
        )}

        {error && <p className="text-red-400 text-sm mb-4 mt-4">{error}</p>}

        <div className="mt-6 flex items-center justify-between">
          {step !== "role" ? (
            <button type="button" onClick={handleBack} className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]">
              Back
            </button>
          ) : <div />}
          <button
            type="button"
            onClick={handleNext}
            disabled={loading}
            className="px-6 py-2.5 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-50 transition-colors"
          >
            {loading ? "Loading…" : step === "confirm" ? "Looks good — start my briefing" : "Next"}
          </button>
        </div>

        {step === "role" && (
          <p className="mt-4 text-xs text-[var(--text-muted)] text-center">
            Built for founders, investors, engineers, and researchers tracking frontier innovation.
          </p>
        )}
      </div>
    </div>
  );
}
