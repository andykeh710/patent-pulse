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

# ── Prefix normalisation ───────────────────────────────────────────────

_CITATION_PREFIXES = ("USPTO:", "EPO:", "WIPO:")


def _strip_prefix(doc_id: str) -> str:
    """Remove a known citation prefix if present.

    ``USPTO:US12345`` → ``US12345``
    ``EP4567890B1``    → ``EP4567890B1`` (no prefix, pass through)
    """
    for p in _CITATION_PREFIXES:
        if doc_id.startswith(p):
            return doc_id[len(p):]
    return doc_id


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

    Matching is prefix-agnostic: ``USPTO:US12345`` matches ``US12345``
    in the known set and vice versa. This handles the mismatch between
    database doc_ids (no prefix) and model citations (with prefix).

    Args:
        cited_doc_ids: Citations extracted from the response text.
        known_doc_ids: Set of doc_ids the model was authorised to cite
            (retrieved patents + open_patent/search_patents/compare_companies
            results).

    Returns:
        Dict with ``verified`` and ``unverified`` lists.
    """
    # Build a normalised known set (prefixes stripped) for matching.
    normalised_known: set[str] = {_strip_prefix(d) for d in known_doc_ids}

    verified = [
        d for d in cited_doc_ids
        if _strip_prefix(d) in normalised_known
    ]
    unverified = [
        d for d in cited_doc_ids
        if _strip_prefix(d) not in normalised_known
    ]
    return {"verified": verified, "unverified": unverified}
