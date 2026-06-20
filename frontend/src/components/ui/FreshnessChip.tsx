"use client";

/**
 * FreshnessChip — always-on data freshness indicator for the page header.
 *
 * Replaces the stacked FreshnessBanner as the primary freshness indicator.
 * The FreshnessBanner is reworked in S1 to become the Tier-3 hard-banner
 * (full outage only, dismissible, once per session).
 *
 * Three states:
 *   fresh    → green dot + "Updated 2h ago"
 *   stale    → amber dot + "Updated 8d ago"
 *   degraded → red dot + "Sources unavailable"
 *
 * Click opens a popover with full detail.
 */

import { useState, useRef, useEffect } from "react";

export type FreshnessState = "fresh" | "stale" | "degraded";

export interface FreshnessSource {
  label: string;
  status: "up" | "down" | "stale";
  lastRun?: string;
  detail?: string;
  newRecords?: number;
}

interface FreshnessChipProps {
  state: FreshnessState;
  /** Human-readable relative time, e.g. "Updated 2h ago" */
  label: string;
  /** Sources for the popover detail */
  sources?: FreshnessSource[];
  /** When true, disables the popover */
  simple?: boolean;
  className?: string;
}

const STATE_STYLES: Record<FreshnessState, { dot: string; text: string }> = {
  fresh: { dot: "var(--ok)", text: "var(--text-muted)" },
  stale: { dot: "var(--warn)", text: "var(--warn)" },
  degraded: { dot: "var(--danger)", text: "var(--danger)" },
};

export function FreshnessChip({
  state,
  label,
  sources,
  simple = false,
  className = "",
}: FreshnessChipProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", keyHandler);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", keyHandler);
    };
  }, [open]);

  const styles = STATE_STYLES[state];

  return (
    <div ref={ref} className={`relative inline-flex ${className}`}>
      <button
        type="button"
        onClick={() => {
          if (!simple && sources && sources.length > 0) setOpen(!open);
        }}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius-sm)] text-[11px] font-medium transition-colors ${
          simple ? "cursor-default" : "cursor-pointer hover:bg-[var(--bg-glass)]"
        }`}
        aria-label={`Data freshness: ${label}`}
      >
        <span
          className="inline-block rounded-full shrink-0"
          style={{
            width: 6,
            height: 6,
            backgroundColor: styles.dot,
          }}
          aria-hidden="true"
        />
        <span style={{ color: styles.text }}>{label}</span>
        {!simple && sources && sources.length > 0 && (
          <svg
            className="w-3 h-3"
            style={{ color: "var(--text-muted)" }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        )}
      </button>

      {/* Popover */}
      {open && sources && sources.length > 0 && (
        <div className="absolute right-0 top-full mt-1 w-80 bg-[var(--elevated)] border border-[var(--border-strong)] rounded-[var(--radius-md)] shadow-[var(--shadow-lg)] z-[var(--z-dropdown)] p-3 space-y-2">
          <p className="text-[11px] font-semibold text-[var(--text)]">
            Data Freshness
          </p>
          {sources.map((src) => (
            <div
              key={src.label}
              className="flex items-start gap-2 text-[11px]"
            >
              <span
                className="inline-block rounded-full shrink-0 mt-0.5"
                style={{
                  width: 6,
                  height: 6,
                  backgroundColor:
                    src.status === "up"
                      ? "var(--ok)"
                      : src.status === "stale"
                        ? "var(--warn)"
                        : "var(--danger)",
                }}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <span className="text-[var(--text-2)]">{src.label}</span>
                {src.lastRun && (
                  <span className="text-[var(--text-muted)]">
                    {" "}
                    — {src.lastRun}
                  </span>
                )}
                {src.newRecords !== undefined && src.newRecords > 0 && (
                  <span className="text-[var(--ok)]">
                    {" "}
                    ({src.newRecords} new)
                  </span>
                )}
                {src.detail && (
                  <p className="text-[var(--text-muted)] mt-0.5">{src.detail}</p>
                )}
              </div>
            </div>
          ))}
          <p className="text-[10px] text-[var(--text-muted)] pt-1 border-t border-[var(--border)]">
            Verify against official patent registers before any commercial
            decision.
          </p>
        </div>
      )}
    </div>
  );
}
