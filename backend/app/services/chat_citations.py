"""
Phase 3 PR 4 — Citation extraction and verification.

Extracts [PREFIX:DOC_ID] markers from Claude's response text and
verifies them against the known-doc-id pool (retrieved patents +
tool-call results). Unverified citations produce a soft warning
event in the SSE stream (rendered as a badge in the frontend in PR 7).
"""

from __future__ import annotations

import re

# ── Pattern ────────────────────────────────────────────────────────────

# Matches [USPTO:US12345], [EPO:EP1234567B1], [WIPO:WO2024/123456]
# Requires at least one character after the colon (rejects bare [USPTO]).
CITATION_PATTERN = re.compile(r"\[((?:USPTO|EPO|WIPO):[A-Z0-9_/-]+)\]")

# ── Citation normalisation ─────────────────────────────────────────────

_CITATION_PREFIXES = {
    "USPTO:": "USPTO",
    "EPO:": "EPO",
    "WIPO:": "WIPO",
}

_DOC_ID_OFFICE_PREFIXES = (
    ("US", "USPTO"),
    ("EP", "EPO"),
    ("WO", "WIPO"),
)


def _canonical_doc_id(doc_id: str) -> tuple[str | None, str]:
    """Return ``(office, document_id)`` for citation verification.

    ``USPTO:US12345`` and ``US12345`` both resolve to
    ``("USPTO", "US12345")``. Wrong-office citations such as
    ``EPO:US12345`` stay distinct from ``USPTO:US12345``.
    """
    normalized = doc_id.strip()
    for prefix, office in _CITATION_PREFIXES.items():
        if normalized.startswith(prefix):
            return office, normalized[len(prefix) :]

    for doc_prefix, office in _DOC_ID_OFFICE_PREFIXES:
        if normalized.startswith(doc_prefix):
            return office, normalized

    return None, normalized


# ── Public API ─────────────────────────────────────────────────────────


def extract_citations(text: str) -> list[str]:
    """Pull all [PREFIX:DOC_ID] markers from a response.

    Returns deduplicated list, preserving order of first appearance.
    """
    matches = CITATION_PATTERN.findall(text)
    seen: set[str] = set()
    out: list[str] = []
    for m in matches:
        if m not in seen:
            out.append(m)
            seen.add(m)
    return out


def verify_citations(
    cited_doc_ids: list[str],
    known_doc_ids: set[str],
) -> dict[str, list[str]]:
    """Split cited doc_ids into verified vs unverified.

    Matching canonicalises office prefixes: ``USPTO:US12345`` matches
    ``US12345`` in the known set, but ``EPO:US12345`` does not. This
    handles the mismatch between database doc_ids (often no prefix) and
    model citations while preserving jurisdiction.

    Args:
        cited_doc_ids: Citations extracted from the response text.
        known_doc_ids: Set of doc_ids the model was authorised to cite
            (retrieved patents + open_patent/search_patents/compare_companies
            results).

    Returns:
        Dict with ``verified`` and ``unverified`` lists.
    """
    known: set[tuple[str | None, str]] = {_canonical_doc_id(d) for d in known_doc_ids}

    verified = [d for d in cited_doc_ids if _canonical_doc_id(d) in known]
    unverified = [d for d in cited_doc_ids if _canonical_doc_id(d) not in known]
    return {"verified": verified, "unverified": unverified}
