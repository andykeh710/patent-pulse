export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US").format(value);
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : plural ?? `${singular}s`;
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value) return "";
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(maxLength - 1, 0))}…`;
}

export function humanizeTag(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function getScoreLabel(score: number): string {
  if (score >= 0.8) return "High";
  if (score >= 0.5) return "Medium";
  return "Low";
}

export function getScoreBgClass(score: number): string {
  if (score >= 0.8) return "bg-green-100 text-green-700";
  if (score >= 0.5) return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-600";
}

export function getOpportunityLabel(score: number): string {
  if (score >= 75) return "High";
  if (score >= 50) return "Medium";
  return "Low";
}

export function getOpportunityBgClass(score: number): string {
  if (score >= 75) return "bg-emerald-100 text-emerald-700";
  if (score >= 50) return "bg-amber-100 text-amber-700";
  return "bg-gray-100 text-gray-600";
}
