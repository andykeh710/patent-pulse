"use client";

/** Tiny filter primitives shared by the /opportunity page. */

interface SelectOption {
  value: string;
  label: string;
}

interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: SelectOption[];
}

export function FilterSelect({ label, value, onChange, options }: FilterSelectProps) {
  return (
    <div className="flex flex-col">
      <label className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-[var(--border-default)] px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

interface FilterTextProps {
  label: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
}

export function FilterText({ label, placeholder, value, onChange }: FilterTextProps) {
  return (
    <div className="flex flex-col">
      <label className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </label>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-32 rounded-lg border border-[var(--border-default)] px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      />
    </div>
  );
}

interface FilterNumberProps {
  label: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
}

export function FilterNumber({ label, placeholder, value, onChange }: FilterNumberProps) {
  return (
    <div className="flex flex-col">
      <label className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </label>
      <input
        type="number"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-24 rounded-lg border border-[var(--border-default)] px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      />
    </div>
  );
}
