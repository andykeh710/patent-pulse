"use client";

import { useState } from "react";

interface TourStep {
  title: string;
  body: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    title: "Today",
    body: "Your daily patent briefing. We surface the most relevant filings, company moves, expiring opportunities, and emerging technology themes based on your interests.",
  },
  {
    title: "Trends",
    body: "Track where innovation is accelerating. Trends highlight CPC areas, themes, and filing spikes that may indicate new market movement.",
  },
  {
    title: "Companies",
    body: "Follow companies to monitor their patent activity, strategic direction, and emerging technical bets.",
  },
  {
    title: "Opportunities",
    body: "Find patents and technology areas that may be commercially interesting, underserved, expiring, or strategically valuable.",
  },
  {
    title: "Watchlist",
    body: "Save patents, companies, and themes you want to track over time.",
  },
];

export function Tour({ onDismiss }: { onDismiss: () => void }) {
  const [step, setStep] = useState(0);

  const handleNext = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1);
    } else {
      if (typeof window !== "undefined") {
        localStorage.setItem("tourCompleted", "true");
      }
      onDismiss();
    }
  };

  const handleSkip = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("tourCompleted", "true");
    }
    onDismiss();
  };

  const current = TOUR_STEPS[step];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Dimmed background */}
      <div className="absolute inset-0 bg-black/60" onClick={handleSkip} />

      {/* Tour card */}
      <div className="relative z-10 bg-[var(--bg-surface)] rounded-xl border border-[var(--border-subtle)] p-8 max-w-md w-full mx-4 shadow-2xl">
        {/* Step indicator */}
        <div className="flex gap-1 mb-4">
          {TOUR_STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full ${i <= step ? "bg-[var(--accent)]" : "bg-[var(--bg-elevated)]"}`}
            />
          ))}
        </div>

        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
          {current.title}
        </h2>
        <p className="text-sm text-[var(--text-secondary)] leading-relaxed mb-6">
          {current.body}
        </p>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handleSkip}
            className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Skip tour
          </button>

          <div className="flex items-center gap-3">
            <span className="text-xs text-[var(--text-muted)]">
              {step + 1} of {TOUR_STEPS.length}
            </span>
            <button
              type="button"
              onClick={handleNext}
              className="px-5 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] transition-colors"
            >
              {step < TOUR_STEPS.length - 1 ? "Next" : "Start my briefing"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
