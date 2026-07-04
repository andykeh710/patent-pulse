export function BrandMark() {
  return (
    <span className="inline-flex items-baseline gap-1 select-none">
      <span className="text-lg font-semibold text-[var(--text-primary)]">
        Invention
      </span>
      <span className="text-lg font-medium text-[var(--text-secondary)]">
        Index
      </span>
      <span
        className="inline-flex items-center justify-center w-6 h-6 rounded-[var(--radius-sm)] text-xs font-bold text-white ml-0.5"
        style={{ background: "var(--accent)" }}
      >
        8
      </span>
    </span>
  );
}
