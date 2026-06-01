import { BRAND } from "@/lib/brand";

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
        className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-white ml-0.5"
        style={{
          background: "linear-gradient(135deg, var(--signal-blue), var(--signal-violet))",
          boxShadow: "0 0 10px rgba(99,102,241,0.4), 0 0 18px rgba(139,92,246,0.2)",
        }}
      >
        8
      </span>
    </span>
  );
}
