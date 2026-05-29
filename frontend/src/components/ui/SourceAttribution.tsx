"use client";

/**
 * Source attribution for patent data (L5).
 *
 * Renders a small footer-style line indicating the originating patent
 * office so users know where the data comes from, as required by
 * AGENTS.md § Patent Data Rules.
 *
 * Props:
 *   office - office code (USPTO, EPO, WIPO) or doc_id prefix
 *   docId  - alternative: pass a doc_id like "USPTO:12345678"
 *            and the office will be extracted automatically
 */

interface SourceAttributionProps {
  office?: string | null;
  docId?: string | null;
}

const OFFICE_LABELS: Record<string, string> = {
  USPTO: "U.S. Patent and Trademark Office (uspto.gov)",
  EPO: "European Patent Office (epo.org)",
  WIPO: "World Intellectual Property Organization (wipo.int)",
};

const OFFICE_URLS: Record<string, string> = {
  USPTO: "https://www.uspto.gov",
  EPO: "https://www.epo.org",
  WIPO: "https://www.wipo.int",
};

function extractOffice(docId: string | null | undefined): string | null {
  if (!docId) return null;
  const parts = docId.split(":");
  return parts[0]?.toUpperCase() || null;
}

export function SourceAttribution({ office, docId }: SourceAttributionProps) {
  const resolved = office || extractOffice(docId);
  const label = resolved && OFFICE_LABELS[resolved]
    ? OFFICE_LABELS[resolved]
    : "Patent office data";
  const url = resolved ? OFFICE_URLS[resolved] : null;

  return (
    <p className="text-xs text-gray-400 mt-2">
      Source:{" "}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-gray-500"
        >
          {label}
        </a>
      ) : (
        <span>{label}</span>
      )}
    </p>
  );
}
