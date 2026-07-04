"use client";

/**
 * DisclosureWarning — warns users before they publish anything public.
 *
 * V4-ready: build now, render later when community surfaces land.
 * Content per AGENTS.md: "Do not share confidential invention details,
 * trade secrets, unpublished patent applications, or privileged legal
 * information. Your contribution will be public."
 */

interface DisclosureWarningProps {
  /** The action the user is about to take */
  action?: string;
  className?: string;
}

export function DisclosureWarning({
  action = "publish",
  className = "",
}: DisclosureWarningProps) {
  const displayAction = action || "publish";
  return (
    <div
      className={`rounded-[var(--radius-md)] border border-[var(--warn)]/30 bg-[var(--warn-bg)] px-4 py-3 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-2">
        <svg
          className="w-4 h-4 mt-0.5 shrink-0"
          style={{ color: "var(--warn)" }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div className="text-xs text-[var(--text-2)]">
          <p className="font-medium text-[var(--warn)] mb-1">
            Before you {displayAction}:
          </p>
          <p>
            Do not share confidential invention details, trade secrets,
            unpublished patent applications, or privileged legal information.
            Your contribution will be <strong>public</strong>.
          </p>
        </div>
      </div>
    </div>
  );
}
