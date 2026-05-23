"use client";

interface ExternalPatentLinksProps {
  publicationNumber: string;
  office: string;
  docId?: string;
}

/**
 * Build external URLs for patent office registries.
 *
 * Google Patents uses the doc_id format (e.g. US-12345678-B2) or a simplified
 * version. USPTO Patent Center uses the publication number.
 * Espacenet uses the publication number with office prefix.
 */
function buildLinks(pubNumber: string, office: string, docId?: string) {
  const links: { label: string; url: string; icon: string }[] = [];

  // Google Patents — works with doc_id or office+number
  const googleId = docId
    ? docId.replace(/-/g, "")
    : `${office}${pubNumber}`;
  links.push({
    label: "Google Patents",
    url: `https://patents.google.com/patent/${googleId}`,
    icon: "G",
  });

  // USPTO — only for US patents
  if (office === "USPTO" || office === "US") {
    // Patent Center uses the publication number
    const cleanNumber = pubNumber.replace(/[^0-9]/g, "");
    links.push({
      label: "USPTO",
      url: `https://patentcenter.uspto.gov/applications/${cleanNumber}`,
      icon: "U",
    });
  }

  // Espacenet
  const espacenetId = docId
    ? docId.replace(/-/g, "")
    : `${office === "USPTO" ? "US" : office}${pubNumber}`;
  links.push({
    label: "Espacenet",
    url: `https://worldwide.espacenet.com/patent/search?q=pn%3D${espacenetId}`,
    icon: "E",
  });

  // WIPO PATENTSCOPE
  const wipoQuery = encodeURIComponent(pubNumber);
  links.push({
    label: "WIPO",
    url: `https://patentscope.wipo.int/search/en/result.jsf?query=${wipoQuery}`,
    icon: "W",
  });

  return links;
}

export function ExternalPatentLinks({
  publicationNumber,
  office,
  docId,
}: ExternalPatentLinksProps) {
  const links = buildLinks(publicationNumber, office, docId);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-gray-400">View on:</span>
      {links.map((link) => (
        <a
          key={link.label}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-800 hover:underline transition-colors"
          title={`Open on ${link.label}`}
        >
          <span className="inline-flex items-center justify-center w-4 h-4 rounded bg-gray-100 text-gray-500 text-[10px] font-bold">
            {link.icon}
          </span>
          {link.label}
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      ))}
    </div>
  );
}
