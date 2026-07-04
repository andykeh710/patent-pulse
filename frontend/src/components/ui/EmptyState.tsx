"use client";

import Link from "next/link";

// -- Types ----------------------------------------------------------------

interface EmptyStateAction {
  label: string;
  href?: string;
  onClick?: () => void;
  /** If true, renders as primary accent style */
  primary?: boolean;
}

interface EmptyStateProps {
  /** Icon preset */
  icon?: "search" | "list" | "alert" | "patent" | "calendar" | "bookmark";
  /** Main heading */
  title: string;
  /** Explanation of what happened / why */
  message: string;
  /** Optional: additional detail about why data is missing or what to expect */
  detail?: string;
  /** One or more suggested next actions */
  actions?: EmptyStateAction[];
  className?: string;
}

// -- Icons -----------------------------------------------------------------

const ICONS: Record<string, string> = {
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  list: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  alert: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
  patent: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  calendar: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
  bookmark: "M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z",
};

// -- Component -------------------------------------------------------------

export function EmptyState({
  icon = "list",
  title,
  message,
  detail,
  actions,
  className = "",
}: EmptyStateProps) {
  const pathData = ICONS[icon] || ICONS.list;

  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-6 bg-[var(--bg-glass)] rounded-lg border border-[var(--border-subtle)] ${className}`}
    >
      <svg
        className="w-10 h-10 text-[var(--text-disabled)] mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d={pathData}
        />
      </svg>

      <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-1">
        {title}
      </h3>

      <p className="text-sm text-[var(--text-secondary)] text-center max-w-md mb-2">
        {message}
      </p>

      {detail && (
        <p className="text-xs text-[var(--text-muted)] text-center max-w-md mb-4 italic">
          {detail}
        </p>
      )}

      {actions && actions.length > 0 && (
        <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
          {actions.map((action, i) =>
            action.href ? (
              <Link
                key={i}
                href={action.href}
                className={
                  action.primary
                    ? "px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] transition-colors"
                    : "text-sm text-[var(--accent)] hover:text-[var(--accent-hover)] font-medium transition-colors"
                }
              >
                {action.label} →
              </Link>
            ) : (
              <button
                key={i}
                onClick={action.onClick}
                className={
                  action.primary
                    ? "px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] transition-colors"
                    : "text-sm text-[var(--accent)] hover:text-[var(--accent-hover)] font-medium transition-colors"
                }
              >
                {action.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
