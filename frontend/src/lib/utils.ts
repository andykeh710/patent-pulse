import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return dateString;
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return dateString;
  }
}

export function formatDateRelative(dateString: string | null): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Tomorrow";
    if (diffDays === -1) return "Yesterday";
    if (diffDays > 0 && diffDays < 7) return `In ${diffDays} days`;
    if (diffDays < 0 && diffDays > -7) return `${Math.abs(diffDays)} days ago`;

    return formatDate(dateString);
  } catch {
    return dateString;
  }
}

export function getScoreLabel(score: number | null): string {
  if (score === null) return "unknown";
  if (score >= 0.7) return "high";
  if (score >= 0.4) return "medium";
  return "low";
}

export function getScoreColor(score: number | null): string {
  if (score === null) return "#6b7280";
  if (score >= 0.7) return "#22c55e";
  if (score >= 0.4) return "#eab308";
  return "#6b7280";
}

export function getScoreBgClass(score: number | null): string {
  if (score === null) return "bg-gray-100 text-gray-600";
  if (score >= 0.7) return "bg-green-100 text-green-700";
  if (score >= 0.4) return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-600";
}

export function truncate(str: string | null, length: number): string {
  if (!str) return "";
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat("en-US").format(num);
}

export function pluralize(
  count: number,
  singular: string,
  plural?: string
): string {
  return count === 1 ? singular : plural || `${singular}s`;
}

// ---------------------------------------------------------------------------
// Opportunity score helpers (0..100 scale, distinct from interesting_score)
// ---------------------------------------------------------------------------

export function getOpportunityLabel(score: number | null): string {
  if (score === null) return "unknown";
  if (score >= 80) return "exceptional";
  if (score >= 65) return "strong";
  if (score >= 50) return "promising";
  if (score >= 35) return "modest";
  return "weak";
}

export function getOpportunityBgClass(score: number | null): string {
  if (score === null) return "bg-gray-100 text-gray-600";
  if (score >= 80) return "bg-emerald-100 text-emerald-800 border border-emerald-300";
  if (score >= 65) return "bg-green-100 text-green-700";
  if (score >= 50) return "bg-yellow-100 text-yellow-800";
  if (score >= 35) return "bg-orange-100 text-orange-700";
  return "bg-gray-100 text-gray-600";
}

/** Pretty-print a snake_case tag like "ai_revival_candidate" → "AI Revival Candidate". */
export function humanizeTag(tag: string): string {
  return tag
    .split("_")
    .map((w) => {
      const upper = w.toUpperCase();
      if (["AI", "ML", "NLP", "IOT", "VR", "AR", "API", "UI", "UX"].includes(upper)) {
        return upper;
      }
      return w.charAt(0).toUpperCase() + w.slice(1);
    })
    .join(" ");
}
