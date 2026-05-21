"use client";

interface AISourceFooterProps {
  className?: string;
}

/**
 * Standard footer for AI-generated patent analysis panels.
 * Shows data source caveat and generation context.
 */
export function AISourceFooter({ className = "" }: AISourceFooterProps) {
  return (
    <div className={`mt-4 pt-3 border-t border-gray-100 flex items-start gap-2 ${className}`}>
      <svg className="w-3.5 h-3.5 mt-0.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p className="text-[11px] text-gray-400 leading-relaxed">
        AI-generated from patent metadata and claims. May contain inaccuracies.
        Not legal advice. Verify with official patent registers before acting.
      </p>
    </div>
  );
}
