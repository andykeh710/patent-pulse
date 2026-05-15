import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(value: Date | string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

export function truncate(value: string | null | undefined, maxLength: number) {
  if (!value || value.length <= maxLength) {
    return value ?? "";
  }

  return `${value.slice(0, Math.max(maxLength - 1, 0))}...`;
}

export function pluralize(count: number, singular: string, plural?: string) {
  return count === 1 ? singular : plural ?? `${singular}s`;
}

export function humanizeTag(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getScoreLabel(score: number) {
  if (score >= 0.75) {
    return "high";
  }
  if (score >= 0.4) {
    return "medium";
  }
  return "low";
}

export function getScoreBgClass(score: number) {
  if (score >= 0.75) {
    return "bg-emerald-100 text-emerald-700";
  }
  if (score >= 0.4) {
    return "bg-yellow-100 text-yellow-700";
  }
  return "bg-gray-100 text-gray-600";
}

export function getOpportunityLabel(score: number) {
  if (score >= 75) {
    return "high";
  }
  if (score >= 40) {
    return "medium";
  }
  return "low";
}

export function getOpportunityBgClass(score: number) {
  if (score >= 75) {
    return "bg-emerald-100 text-emerald-700";
  }
  if (score >= 40) {
    return "bg-yellow-100 text-yellow-700";
  }
  return "bg-gray-100 text-gray-600";
}
