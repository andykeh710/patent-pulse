"use client";

// -- Types ----------------------------------------------------------------

interface FilterChip {
  key: string;
  label: string;
  onRemove: () => void;
}

interface FilterChipsProps {
  chips: FilterChip[];
  /** Text shown when there are no active filters */
  emptyLabel?: string;
  /** Callback to clear all filters */
  onClearAll?: () => void;
  className?: string;
}

// -- Component -------------------------------------------------------------

export function FilterChips({
  chips,
  emptyLabel = "No active filters",
  onClearAll,
  className = "",
}: FilterChipsProps) {
  if (chips.length === 0) {
    return (
      <div className={`text-xs text-[var(--text-muted)] ${className}`}>
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {chips.map((chip) => (
        <span
          key={chip.key}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--accent-muted)] text-[var(--accent)]"
        >
          {chip.label}
          <button
            onClick={chip.onRemove}
            className="ml-0.5 hover:text-[var(--text-primary)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-full"
            aria-label={`Remove filter: ${chip.label}`}
          >
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </span>
      ))}
      {onClearAll && chips.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
