export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value) return "";
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 3))}...`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "-";

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("en").format(value);
}

export function pluralize(
  count: number | null | undefined,
  singular: string,
  plural?: string
): string {
  return count === 1 ? singular : plural || `${singular}s`;
}

export function humanizeTag(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getScoreLabel(score: number): "low" | "medium" | "high" {
  if (score >= 0.75) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

export function getScoreBgClass(score: number): string {
  const label = getScoreLabel(score);
  if (label === "high") return "bg-green-100 text-green-700";
  if (label === "medium") return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-700";
}

export function getOpportunityLabel(score: number): "low" | "medium" | "high" {
  if (score >= 75) return "high";
  if (score >= 50) return "medium";
  return "low";
}

export function getOpportunityBgClass(score: number): string {
  const label = getOpportunityLabel(score);
  if (label === "high") return "bg-emerald-100 text-emerald-700";
  if (label === "medium") return "bg-amber-100 text-amber-800";
  return "bg-gray-100 text-gray-700";
}
