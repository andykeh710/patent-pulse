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
      className={`relative bg-white border rounded-xl p-6 flex flex-col ${
        highlighted
          ? "border-primary-500 ring-2 ring-primary-500 shadow-lg"
          : "border-gray-200"
      }`}
    >
      {badge && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-xs font-semibold bg-primary-600 text-white">
          {badge}
        </span>
      )}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
        <div className="mt-2">
          <span className="text-3xl font-bold text-gray-900">{price}</span>
          {period && <span className="text-sm text-gray-500">{period}</span>}
        </div>
      </div>
      <ul className="space-y-2 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
            <CheckIcon />
            {f}
          </li>
        ))}
      </ul>
      <Link
        href={href}
        className={`inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
          highlighted
            ? "bg-primary-600 text-white hover:bg-primary-700"
            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
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
      className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0"
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
