"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { StepRole } from "@/components/onboarding/StepRole";
import { StepUseCase } from "@/components/onboarding/StepUseCase";
import { StepIndustry } from "@/components/onboarding/StepIndustry";
import { StepInterests } from "@/components/onboarding/StepInterests";
import { StepConfirm, type Suggestion } from "@/components/onboarding/StepConfirm";

type Step = "role" | "use_case" | "industry" | "interests" | "confirm";

const STEP_LABELS: Record<Step, string> = {
  role: "Your role",
  use_case: "Your goal",
  industry: "Your industry",
  interests: "Your interests",
  confirm: "Confirm",
};

export default function OnboardingPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [step, setStep] = useState<Step>("role");
  const [role, setRole] = useState("");
  const [useCase, setUseCase] = useState("");
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

  const totalSteps = 5;
  const steps: Step[] = ["role", "use_case", "industry", "interests", "confirm"];
  const stepIndex = steps.indexOf(step) + 1;

  const handleNext = async () => {
    if (step === "role" && !role) return;
    if (step === "use_case" && !useCase) return;
    if (step === "industry" && !industry) return;
    if (step === "interests") {
      setLoading(true);
      setError("");
      try {
        const res = await fetch("/api/v1/onboarding/complete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            persona: role,
            use_case: useCase || null,
            industry_focus: industry,
            interests_freetext: interests,
          }),
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
        router.push("/today");
      } catch {
        setError("Something went wrong. Please try again.");
      } finally {
        setLoading(false);
      }
      return;
    }
    // Move to next step
    const currentIdx = steps.indexOf(step);
    setStep(steps[currentIdx + 1]);
  };

  const handleBack = () => {
    const currentIdx = steps.indexOf(step);
    if (currentIdx > 0) setStep(steps[currentIdx - 1]);
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center p-4">
      <div className="bg-[var(--bg-surface)] rounded-xl shadow-sm border border-[var(--border-subtle)] p-6 sm:p-8 max-w-lg w-full space-y-6">
        {/* Progress */}
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <span>
            Step {stepIndex} of {totalSteps}
          </span>
          <span>·</span>
          <span>{STEP_LABELS[step]}</span>
        </div>

        {step === "role" && <StepRole selected={role} onSelect={setRole} />}
        {step === "use_case" && <StepUseCase selected={useCase} onSelect={setUseCase} />}
        {step === "industry" && <StepIndustry selected={industry} onSelect={setIndustry} />}
        {step === "interests" && (
          <StepInterests value={interests} onChange={setInterests} />
        )}
        {step === "confirm" && (
          <StepConfirm
            suggestions={suggestions}
            onRemoveCompany={(name) =>
              setSuggestions((prev) =>
                prev
                  ? { ...prev, companies: prev.companies.filter((c) => c.normalized_name !== name) }
                  : null
              )
            }
            onRemoveTheme={(id) =>
              setSuggestions((prev) =>
                prev
                  ? { ...prev, themes: prev.themes.filter((t) => t.id !== id) }
                  : null
              )
            }
          />
        )}

        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        <div className="flex justify-between pt-2">
          <button
            onClick={handleBack}
            disabled={stepIndex === 1}
            className="px-4 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-30 transition-opacity"
          >
            Back
          </button>
          <button
            onClick={handleNext}
            disabled={loading}
            className="px-6 py-2 rounded-lg text-sm font-medium bg-[var(--accent)] text-white disabled:opacity-40 transition-opacity"
          >
            {loading ? "Loading…" : step === "confirm" ? "Start using Invention Index 8" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
