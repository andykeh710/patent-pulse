"use client";

import type { PatentTags, TimeHorizon } from "@/lib/types";
import { humanizeTag } from "@/lib/utils";
import { RiskFlagsBadge } from "./RiskFlagsBadge";

interface TagsPanelProps {
  tags: PatentTags | null | undefined;
  /** "compact" = used inline on cards; "full" = used on detail pages. */
  variant?: "compact" | "full";
}

const HORIZON_COPY: Record<TimeHorizon, { label: string; tone: string }> = {
  now: { label: "Now (0–1 yr)", tone: "bg-emerald-100 text-emerald-700" },
  near_term: { label: "Near term (1–3 yr)", tone: "bg-blue-100 text-blue-700" },
  long_term: { label: "Long term (3–5+ yr)", tone: "bg-indigo-100 text-indigo-700" },
  unknown: { label: "Unknown horizon", tone: "bg-gray-100 text-gray-600" },
};

export function TagsPanel({ tags, variant = "full" }: TagsPanelProps) {
  if (!tags) {
    return (
      <div className="rounded-md border border-dashed border-gray-200 px-3 py-2 text-xs text-gray-500">
        Tags not yet computed for this patent.
      </div>
    );
  }

  const compact = variant === "compact";
  const horizon = HORIZON_COPY[tags.time_horizon] ?? HORIZON_COPY.unknown;

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-1.5">
        <span
          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${horizon.tone}`}
        >
          {horizon.label}
        </span>
        {tags.opportunity_tags.slice(0, 2).map((t) => (
          <span
            key={t}
            className="inline-flex items-center rounded-md bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800"
          >
            {humanizeTag(t)}
          </span>
        ))}
        {tags.industries.slice(0, 2).map((i) => (
          <span
            key={i}
            className="inline-flex items-center rounded-md bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-700"
          >
            {humanizeTag(i)}
          </span>
        ))}
        <RiskFlagsBadge flags={tags.risk_flags} collapse />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-medium ${horizon.tone}`}
        >
          {horizon.label}
        </span>
      </div>

      {tags.problem_solved && (
        <p className="text-sm text-gray-700">
          <span className="font-semibold text-gray-900">Problem solved: </span>
          {tags.problem_solved}
        </p>
      )}

      <TagRow label="Industries" values={tags.industries} tone="sky" />
      <TagRow label="Technology / Method" values={tags.technology_method} tone="violet" />
      {tags.materials.length > 0 && (
        <TagRow label="Materials" values={tags.materials} tone="emerald" />
      )}
      {tags.novel_application_categories.length > 0 && (
        <TagRow
          label="Novel applications"
          values={tags.novel_application_categories}
          tone="amber"
        />
      )}
      <TagRow label="Opportunity tags" values={tags.opportunity_tags} tone="purple" />
      {tags.trend_tags.length > 0 && (
        <TagRow label="Trend tags" values={tags.trend_tags} tone="rose" />
      )}

      {tags.risk_flags.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Risk flags
          </div>
          <RiskFlagsBadge flags={tags.risk_flags} />
        </div>
      )}
    </div>
  );
}

const TONE_CLASSES: Record<string, string> = {
  sky: "bg-sky-50 text-sky-700",
  violet: "bg-violet-50 text-violet-700",
  emerald: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-800",
  purple: "bg-purple-100 text-purple-800",
  rose: "bg-rose-50 text-rose-700",
};

function TagRow({
  label,
  values,
  tone,
}: {
  label: string;
  values: string[];
  tone: string;
}) {
  if (!values.length) return null;
  const cls = TONE_CLASSES[tone] || "bg-gray-100 text-gray-700";
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span
            key={v}
            className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${cls}`}
          >
            {humanizeTag(v)}
          </span>
        ))}
      </div>
    </div>
  );
}
