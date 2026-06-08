"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { BRAND } from "@/lib/brand";

type Step = "role" | "industry" | "interests" | "confirm";

const ROLES = ["Founder", "VC", "Engineer", "Researcher", "Operator", "Other"];
const INDUSTRIES = [
  "AI/ML", "Biotech/Pharma", "Semiconductors", "Robotics", "Energy/Climate",
  "Fintech/Web3", "Consumer/Retail", "Aerospace/Defense",
  "Materials/Manufacturing", "Medical Devices", "Automotive/Mobility", "Telecom",
];

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
  const [suggestions, setSuggestions] = useState<{
    suggested_companies: { normalized_name: string; display_name: string; patent_count: number }[];
    suggested_themes: { id: string; name: string; description: string | null }[];
  } | null>(null);
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
        setSuggestions(data);
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
        const companyIds = suggestions?.suggested_companies.map((c) => c.normalized_name) || [];
        const themeIds = suggestions?.suggested_themes.map((t) => t.id) || [];
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
    // Move to next step
    const steps: Step[] = ["role", "industry", "interests", "confirm"];
    const idx = steps.indexOf(step);
    if (idx < steps.length - 1) setStep(steps[idx + 1]);
  };

  const handleBack = () => {
    const steps: Step[] = ["role", "industry", "interests", "confirm"];
    const idx = steps.indexOf(step);
    if (idx > 0) setStep(steps[idx - 1]);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)] px-4">
      <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border-subtle)] p-8 max-w-lg w-full">
        {/* Progress */}
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

        {/* Step content */}
        {step === "role" && (
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">What best describes you?</h2>
            <p className="text-sm text-[var(--text-muted)] mb-4">We&apos;ll tailor your briefing to your role.</p>
            <div className="space-y-2">
              {ROLES.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRole(r)}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${role === r ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]" : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-default)]"}`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === "industry" && (
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">What industry interests you most?</h2>
            <p className="text-sm text-[var(--text-muted)] mb-4">We&apos;ll suggest companies and themes based on your choice.</p>
            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
              {INDUSTRIES.map((ind) => (
                <button
                  key={ind}
                  type="button"
                  onClick={() => setIndustry(ind)}
                  className={`text-left px-3 py-2 rounded-lg border text-sm transition-colors ${industry === ind ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]" : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-default)]"}`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === "interests" && (
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Anything specific you&apos;re tracking?</h2>
            <p className="text-sm text-[var(--text-muted)] mb-4">
              A company, patent number, inventor, keyword, or technology area. Optional — skip if you&apos;re just exploring.
            </p>
            <input
              type="text"
              value={interests}
              onChange={(e) => setInterests(e.target.value)}
              placeholder='e.g. "NVIDIA", "battery recycling", "CRISPR"'
              className="w-full bg-[var(--bg-glass)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              autoFocus
            />
          </div>
        )}

        {step === "confirm" && suggestions && (
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">We built a starter feed for you</h2>
            <p className="text-sm text-[var(--text-muted)] mb-4">Edit anything before continuing.</p>

            {suggestions.suggested_companies.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Followed companies</h3>
                <div className="space-y-1">
                  {suggestions.suggested_companies.map((c) => (
                    <div key={c.normalized_name} className="flex items-center justify-between px-3 py-1.5 rounded bg-[var(--bg-elevated)] text-sm">
                      <span className="text-[var(--text-primary)]">{c.display_name}</span>
                      <span className="text-xs text-[var(--text-muted)]">{c.patent_count} patents</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {suggestions.suggested_themes.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">Suggested themes</h3>
                <div className="space-y-1">
                  {suggestions.suggested_themes.map((t) => (
                    <div key={t.id} className="px-3 py-1.5 rounded bg-[var(--bg-elevated)] text-sm">
                      <span className="text-[var(--text-primary)]">{t.name}</span>
                      {t.description && <span className="text-xs text-[var(--text-muted)] ml-2">{t.description}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {suggestions.suggested_companies.length === 0 && suggestions.suggested_themes.length === 0 && (
              <p className="text-sm text-[var(--text-muted)] mb-4">
                No specific suggestions available yet. You can browse companies and themes after setup.
              </p>
            )}
          </div>
        )}

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

        {/* Navigation */}
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
            {loading ? "Loading…" : step === "confirm" ? "Start my briefing" : "Next"}
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
