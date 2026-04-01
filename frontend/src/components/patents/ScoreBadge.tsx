"use client";

import { getScoreBgClass, getScoreLabel } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number | null;
  showLabel?: boolean;
}

export function ScoreBadge({ score, showLabel = true }: ScoreBadgeProps) {
  if (score === null) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
        —
      </span>
    );
  }

  const label = getScoreLabel(score);
  const bgClass = getScoreBgClass(score);
  const percentage = Math.round(score * 100);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bgClass}`}
      title={`Interest score: ${percentage}%`}
    >
      {percentage}%
      {showLabel && <span className="ml-1 opacity-75">({label})</span>}
    </span>
  );
}
