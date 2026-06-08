"use client";

const ROLES = ["Founder", "VC", "Engineer", "Researcher", "Operator", "Other"];

export function StepRole({ selected, onSelect }: { selected: string; onSelect: (v: string) => void }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">What best describes you?</h2>
      <p className="text-sm text-[var(--text-muted)] mb-4">We&apos;ll tailor your briefing to your role.</p>
      <div className="space-y-2">
        {ROLES.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => onSelect(r)}
            className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${selected === r ? "border-[var(--accent)] bg-[var(--accent-muted)] text-[var(--accent)]" : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-default)]"}`}
          >
            {r}
          </button>
        ))}
      </div>
    </div>
  );
}
