import Link from "next/link";

export function PricingCard({
  name,
  price,
  period = "",
  features,
  cta,
  href,
  highlighted = false,
  badge,
}: {
  name: string;
  price: string;
  period?: string;
  features: string[];
  cta: string;
  href: string;
  highlighted?: boolean;
  badge?: string;
}) {
  return (
    <div
      className={`relative surface-card p-6 flex flex-col ${
        highlighted
          ? "border-[var(--accent)] ring-1 ring-[var(--accent)]"
          : ""
      }`}
    >
      {badge && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-[var(--radius-full)] text-xs font-semibold bg-[var(--accent)] text-white">
          {badge}
        </span>
      )}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-[var(--text-primary)]">{name}</h3>
        <div className="mt-2">
          <span className="text-3xl font-bold text-[var(--text-primary)]">{price}</span>
          {period && <span className="text-sm text-[var(--text-muted)]">{period}</span>}
        </div>
      </div>
      <ul className="space-y-2 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
            <CheckIcon />
            {f}
          </li>
        ))}
      </ul>
      <Link
        href={href}
        className={`inline-flex items-center justify-center px-4 py-2 rounded-[var(--radius-md)] text-sm font-semibold transition-colors ${
          highlighted
            ? "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"
            : "bg-[var(--bg-glass)] text-[var(--text-secondary)] hover:bg-[var(--bg-glass-strong)]"
        }`}
      >
        {cta}
      </Link>
    </div>
  );
}

export function CheckIcon() {
  return (
    <svg
      className="w-4 h-4 text-[var(--score-high)] mt-0.5 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}
