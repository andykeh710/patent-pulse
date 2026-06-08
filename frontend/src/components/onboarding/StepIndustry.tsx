"use client";

const INDUSTRIES = [
  "AI/ML", "Biotech/Pharma", "Semiconductors", "Robotics", "Energy/Climate",
  "Fintech/Web3", "Consumer/Retail", "Aerospace/Defense",
  "Materials/Manufacturing", "Medical Devices", "Automotive/Mobility", "Telecom",
];

export function StepIndustry({ selected, onSelect }: { selected: string; onSelect: (v: string) => void }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">What industry interests you most?</h2>
      <p className="text-sm text-[var(--text-muted)] mb-4">We&apos;ll suggest companies and themes based on your choice.</p>
      <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
        {INDUSTRIES.map((ind) => (
          <button
            key={ind}
            type="button"
            onClick={() => onSelect(ind)}
            className={`text-left px-3 py-2 rounded-lg border text-sm transition-colors ${selected === ind ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]" : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-default)]"}`}
          >
            {ind}
          </button>
        ))}
      </div>
    </div>
  );
}
