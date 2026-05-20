const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const NUMBER_FORMATTER = new Intl.NumberFormat("en-US");

type ClassValue = string | false | null | undefined;

export function cn(...classes: ClassValue[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(date: string | null | undefined): string {
  if (!date) {
    return "—";
  }

  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return DATE_FORMATTER.format(parsed);
}

export function formatNumber(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

export function humanizeTag(tag: string): string {
  return tag
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
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
    return value || "";
  }

  if (maxLength <= 3) {
    return value.slice(0, maxLength);
  }

  return `${value.slice(0, maxLength - 3)}...`;
}

export function getScoreLabel(score: number): "high" | "medium" | "low" {
  if (score >= 0.7) {
    return "high";
  }
  if (score >= 0.4) {
    return "medium";
  }
  return "low";
}

export function getScoreBgClass(score: number): string {
  if (score >= 0.7) {
    return "bg-green-100 text-green-700";
  }
  if (score >= 0.4) {
    return "bg-yellow-100 text-yellow-700";
  }
  return "bg-gray-100 text-gray-600";
}

export function getOpportunityLabel(score: number): "high" | "medium" | "low" {
  if (score >= 70) {
    return "high";
  }
  if (score >= 45) {
    return "medium";
  }
  return "low";
}

export function getOpportunityBgClass(score: number): string {
  if (score >= 70) {
    return "bg-green-100 text-green-700";
  }
  if (score >= 45) {
    return "bg-yellow-100 text-yellow-700";
  }
  return "bg-gray-100 text-gray-600";
}
