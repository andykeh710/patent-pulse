export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "\u2014";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "\u2014";
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function truncate(value: string | null | undefined, maxLength: number): string {
  if (!value) {
    return "";
  }

  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, Math.max(0, maxLength - 1))}\u2026`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return count === 1 ? singular : plural;
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
  const label = getScoreLabel(score);

  if (label === "high") {
    return "bg-green-100 text-green-700";
  }

  if (label === "medium") {
    return "bg-yellow-100 text-yellow-700";
  }

  return "bg-gray-100 text-gray-700";
}
