type ClassValue = string | false | null | undefined;

export function cn(...classes: ClassValue[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "-";

  if (typeof value === "string") {
    const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnly) {
      const [, year, month, day] = dateOnly;
      return `${month}/${day}/${year}`;
    }
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  return new Intl.DateTimeFormat("en-US", {
    month: "2-digit",
    day: "2-digit",
    year: "numeric",
  }).format(date);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function pluralize(
  count: number,
  singular: string,
  plural = `${singular}s`
): string {
  return Math.abs(count) === 1 ? singular : plural;
}

export function humanizeTag(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value || value.length <= maxLength) return value ?? "";
  return `${value.slice(0, Math.max(0, maxLength - 3))}...`;
}

export function getScoreLabel(score: number): string {
  if (score >= 0.75) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

export function getScoreBgClass(score: number): string {
  if (score >= 0.75) return "bg-green-100 text-green-700";
  if (score >= 0.5) return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-600";
}

export function getOpportunityLabel(score: number): string {
  if (score >= 80) return "strong";
  if (score >= 60) return "good";
  if (score >= 40) return "moderate";
  return "low";
}

export function getOpportunityBgClass(score: number): string {
  if (score >= 80) return "bg-emerald-100 text-emerald-800";
  if (score >= 60) return "bg-blue-100 text-blue-800";
  if (score >= 40) return "bg-yellow-100 text-yellow-800";
  return "bg-gray-100 text-gray-600";
}
