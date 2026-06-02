"use client";

interface EmptyStateProps {
  icon?: "search" | "list" | "alert" | "patent";
  title: string;
  message: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
}

const ICONS: Record<string, string> = {
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  list: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  alert: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
  patent: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
};

export function EmptyState({
  icon = "list",
  title,
  message,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 bg-[var(--bg-glass)] backdrop-blur-md rounded-lg border border-[var(--border-subtle)]">
      <svg
        className="w-10 h-10 text-[var(--text-disabled)] mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d={ICONS[icon] || ICONS.list}
        />
      </svg>
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-1">{title}</h3>
      <p className="text-xs text-[var(--text-muted)] text-center max-w-sm">{message}</p>
      {action && (
        action.href ? (
          <a
            href={action.href}
            className="mt-4 text-sm text-[var(--accent)] hover:text-[var(--accent)] font-medium transition-colors"
          >
            {action.label}
          </a>
        ) : action.onClick ? (
          <button
            onClick={action.onClick}
            className="mt-4 text-sm text-[var(--accent)] hover:text-[var(--accent)] font-medium transition-colors"
          >
            {action.label}
          </button>
        ) : null
      )}
    </div>
  );
}

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  message = "Something went wrong loading this data.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 bg-red-500/5 rounded-lg border border-red-500/20">
      <svg
        className="w-10 h-10 text-red-400/60 mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h3 className="text-sm font-medium text-red-400 mb-1">Error</h3>
      <p className="text-xs text-red-400/60 text-center max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 text-sm text-red-400 hover:text-red-300 font-medium transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
