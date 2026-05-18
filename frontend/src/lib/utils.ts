import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return count === 1 ? singular : plural;
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value) return "";
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 1))}…`;
}

export function humanizeTag(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getScoreLabel(score: number): "low" | "medium" | "high" {
  if (score >= 0.7) return "high";
  if (score >= 0.4) return "medium";
  return "low";
}

export function getScoreBgClass(score: number): string {
  const label = getScoreLabel(score);
  if (label === "high") return "bg-green-100 text-green-700";
  if (label === "medium") return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-600";
}

export function getOpportunityLabel(score: number): "low" | "medium" | "high" {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

export function getOpportunityBgClass(score: number): string {
  const label = getOpportunityLabel(score);
  if (label === "high") return "bg-emerald-100 text-emerald-700";
  if (label === "medium") return "bg-amber-100 text-amber-800";
  return "bg-gray-100 text-gray-600";
}
