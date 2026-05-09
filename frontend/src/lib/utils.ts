import { format } from "date-fns";

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return format(date, "MMM d, yyyy");
}

export function formatNumber(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString();
}

export function pluralize(
  count: number,
  singular: string,
  plural = `${singular}s`
): string {
  return count === 1 ? singular : plural;
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value || value.length <= maxLength) {
    return value ?? "";
  }

  return `${value.slice(0, maxLength).trimEnd()}...`;
}

export function humanizeTag(value: string | null | undefined): string {
  if (!value) {
    return "";
  }

  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function getScoreLabel(score: number): "low" | "medium" | "high" {
  if (score >= 0.75) {
    return "high";
  }
  if (score >= 0.5) {
    return "medium";
  }
  return "low";
}

export function getScoreBgClass(score: number): string {
  if (score >= 0.75) {
    return "bg-green-100 text-green-700";
  }
  if (score >= 0.5) {
    return "bg-yellow-100 text-yellow-700";
  }
  return "bg-gray-100 text-gray-700";
}

export function getOpportunityLabel(score: number): "low" | "medium" | "high" {
  if (score >= 75) {
    return "high";
  }
  if (score >= 50) {
    return "medium";
  }
  return "low";
}

export function getOpportunityBgClass(score: number): string {
  if (score >= 75) {
    return "bg-emerald-100 text-emerald-700";
  }
  if (score >= 50) {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-gray-100 text-gray-700";
}
