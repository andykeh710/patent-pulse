"use client";

const OPTIONS = [
  { value: "startup_ideas", label: "Startup ideas", emoji: "💡" },
  { value: "rd_monitoring", label: "R&D monitoring", emoji: "🔬" },
  { value: "competitive_intel", label: "Competitive intelligence", emoji: "🏢" },
  { value: "investment_research", label: "Investment research", emoji: "📈" },
  { value: "expiry_freedom", label: "Expiry / design freedom", emoji: "📋" },
  { value: "licensing", label: "Licensing", emoji: "🤝" },
  { value: "academic", label: "Academic research", emoji: "📚" },
  { value: "general", label: "General discovery", emoji: "🔍" },
];

interface Props {
  selected: string;
  onSelect: (value: string) => void;
}

export function StepUseCase({ selected, onSelect }: Props) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">
          What are you trying to do with patent intelligence?
        </h2>
        <p className="text-sm text-[var(--text-muted)] mt-1">
          This helps us prioritize the signals and opportunities you care about.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onSelect(opt.value)}
            className={`rounded-lg border px-4 py-3 text-sm text-left transition-colors ${
              selected === opt.value
                ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] font-medium"
                : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--text-muted)]"
            }`}
          >
            <span className="mr-2">{opt.emoji}</span>
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
