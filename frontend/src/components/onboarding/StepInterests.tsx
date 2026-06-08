"use client";

export function StepInterests({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Anything specific you&apos;re tracking?</h2>
      <p className="text-sm text-[var(--text-muted)] mb-4">
        A company, patent number, inventor, keyword, or technology area. Optional — skip if you&apos;re just exploring.
      </p>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder='e.g. "NVIDIA", "battery recycling", "US1234567", "computer vision", "CRISPR"'
        className="w-full bg-[var(--bg-glass)] border border-[var(--border-default)] rounded-lg px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        autoFocus
      />
    </div>
  );
}
