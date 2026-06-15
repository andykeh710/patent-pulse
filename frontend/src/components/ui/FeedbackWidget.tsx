"use client";

import { useState } from "react";

interface FeedbackWidgetProps {
  /** Which screen this feedback is from */
  screen: string;
  /** Optional: what the user was doing */
  context?: string;
}

/**
 * Lightweight inline feedback widget.
 *
 * Renders a small "Was this useful?" prompt with thumbs up/down
 * on major screens.  Submits to the console (dev) or can be wired
 * to an analytics endpoint later.
 *
 * Non-blocking — failures don't affect UX.
 */
export function FeedbackWidget({ screen, context }: FeedbackWidgetProps) {
  const [submitted, setSubmitted] = useState(false);

  const handleFeedback = (useful: boolean) => {
    setSubmitted(true);
    // Log to console for dev; wire to POST /api/v1/feedback when ready
    console.debug("[feedback]", { screen, context, useful, ts: new Date().toISOString() });
  };

  if (submitted) {
    return (
      <div className="mt-8 pt-4 border-t border-[var(--border-subtle)]">
        <p className="text-xs text-[var(--text-muted)]">Thanks for your feedback.</p>
      </div>
    );
  }

  return (
    <div className="mt-8 pt-4 border-t border-[var(--border-subtle)]">
      <div className="flex items-center gap-3">
        <span className="text-xs text-[var(--text-muted)]">Was this useful?</span>
        <button
          onClick={() => handleFeedback(true)}
          className="p-1.5 rounded hover:bg-[var(--bg-glass)] transition-colors"
          title="Yes — helpful"
          aria-label="Yes, this was helpful"
        >
          <svg className="w-4 h-4 text-[var(--text-muted)] hover:text-[var(--score-high)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
          </svg>
        </button>
        <button
          onClick={() => handleFeedback(false)}
          className="p-1.5 rounded hover:bg-[var(--bg-glass)] transition-colors"
          title="No — not helpful"
          aria-label="No, this was not helpful"
        >
          <svg className="w-4 h-4 text-[var(--text-muted)] hover:text-[var(--expiry-lapsed-confirmed)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
          </svg>
        </button>
      </div>
      <p className="text-xs text-[var(--text-muted)] mt-1">
        What&rsquo;s missing?{" "}
        <a href="mailto:andy.keh@gmail.com" className="text-[var(--accent)] hover:underline">
          Tell us →
        </a>
      </p>
    </div>
  );
}
