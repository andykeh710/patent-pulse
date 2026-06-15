"use client";

import { ReactNode } from "react";
import { FreshnessBanner } from "./FreshnessBanner";

interface PageHeaderProps {
  /** Page title (h1) */
  title: string;
  /** Subtitle / description line */
  description?: string;
  /** Primary CTA button or action node */
  primaryAction?: ReactNode;
  /** Secondary action node */
  secondaryAction?: ReactNode;
  /** Show data freshness banner for these sources */
  freshnessSources?: ("patents" | "summaries" | "trends" | "ai_runs")[];
  /** Optional badge/label above the title */
  label?: string;
  /** Optional metadata below description */
  meta?: string;
  className?: string;
}

export function PageHeader({
  title,
  description,
  primaryAction,
  secondaryAction,
  freshnessSources,
  label,
  meta,
  className = "",
}: PageHeaderProps) {
  return (
    <div className={`mb-6 ${className}`}>
      {label && (
        <span className="text-[10px] uppercase tracking-[0.12em] text-[var(--text-muted)] block mb-1">
          {label}
        </span>
      )}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {title}
          </h1>
          {description && (
            <p className="text-[var(--text-secondary)] mt-1">{description}</p>
          )}
          {meta && (
            <p className="text-xs text-[var(--text-muted)] mt-1">{meta}</p>
          )}
        </div>
        {(primaryAction || secondaryAction) && (
          <div className="flex items-center gap-2 shrink-0">
            {secondaryAction}
            {primaryAction}
          </div>
        )}
      </div>
      {freshnessSources && freshnessSources.length > 0 && (
        <FreshnessBanner show={freshnessSources} className="mt-3" />
      )}
    </div>
  );
}
