"""
Phase 3 PR 3 — Anthropic tool definitions and handlers.

Three tools for the chatbot:
  - search_patents : hybrid search via pgvector + FTS + recency
  - open_patent    : full patent detail lookup by doc_id
  - compare_companies : aggregate portfolio comparison (2–5 companies)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import PatentEmbedder

logger = logging.getLogger(__name__)

# ── Anthropic tool definitions (JSON Schema format) ─────────────────

SEARCH_PATENTS_TOOL: dict[str, Any] = {
    "name": "search_patents",
    "description": (
        "Search for patents matching a query string. Use this when the user "
        "asks about a technical area, technology, or specific concept that "
        "wasn't covered by the initial patent retrieval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language search query (e.g. 'solid-state battery thermal management').",
            },
            "cpc_prefix": {
                "type": "string",
                "description": "Optional CPC class prefix to narrow results (e.g. 'G06N' for AI/ML, 'H01M' for batteries).",
            },
            "assignee": {
                "type": "string",
                "description": "Optional assignee/company name to filter by.",
            },
            "min_similarity": {
                "type": "number",
                "description": "Minimum similarity threshold (0-1). Default 0.3.",
            },
            "limit": {
                "type": "integer",
                "description": "Max patents to return (default 10, max 20).",
            },
        },
        "required": ["query"],
    },
}

OPEN_PATENT_TOOL: dict[str, Any] = {
    "name": "open_patent",
    "description": (
        "Get full details of a specific patent by its doc_id (e.g. "
        "'USPTO:US12345678'). Use this when the user asks for details "
        "about a patent that came up in search or earlier conversation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "doc_id": {
                "type": "string",
                "description": "The patent's document ID (e.g. 'USPTO:US12345678', 'EP:EP4567890B1').",
            },
        },
        "required": ["doc_id"],
    },
}

COMPARE_COMPANIES_TOOL: dict[str, Any] = {
    "name": "compare_companies",
    "description": (
        "Compare patent portfolios of 2–5 companies. Use this when the user "
        "asks about competitive landscape, who else is working in a space, "
        "or M&A target evaluation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "names": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 5,
                "description": "Company/assignee names to compare (2–5 items).",
            },
        },
        "required": ["names"],
    },
}

# Aggregate list for passing to Anthropic's ``tools`` parameter.
TOOLS: list[dict[str, Any]] = [
    SEARCH_PATENTS_TOOL,
    OPEN_PATENT_TOOL,
    COMPARE_COMPANIES_TOOL,
]

# ── Tool-handler dispatch ──────────────────────────────────────────

TOOL_HANDLERS: dict[str, Any] = {}  # populated at bottom of module


async def execute_tool(name: str, input: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    """Dispatch a tool call to its async handler.

    Returns a JSON-serialisable dict. Unknown tool names return an error dict.
    """
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler(db, **input)
    except Exception:
        logger.exception("Tool handler %s failed", name)
        return {"error": f"Tool '{name}' encountered an internal error."}


# ── Handler: search_patents ────────────────────────────────────────

# Weights copied from search.py to keep the tool self-contained.
_VW = 0.6
_KW = 0.2
_RW = 0.2
_MAX_AGE = 365.25 * 24 * 3600 * 20

_HYBRID_SQL_TEMPLATE = """\
SELECT
    p.doc_id,
    p.title,
    p.abstract,
    p.assignees,
    p.publication_date,
    :vw * (1 - (p.embedding <=> CAST(:emb AS vector)))
    + :kw * LEAST(
        ts_rank(p.search_vector, plainto_tsquery('english', :q)), 1.0
    )
    + :rw * (1 - LEAST(
        EXTRACT(EPOCH FROM (NOW() - p.publication_date)) / :max_age,
        1
    )) AS similarity
FROM patent_publications p
WHERE p.embedding IS NOT NULL
  AND {filters}
  AND 1 - (p.embedding <=> CAST(:emb AS vector)) >= :min_sim
ORDER BY similarity DESC
LIMIT :limit
"""


async def _search_patents(
    db: AsyncSession,
    query: str,
    cpc_prefix: str | None = None,
    assignee: str | None = None,
    min_similarity: float = 0.3,
    limit: int = 10,
) -> dict[str, Any]:
    """Hybrid search — embed query, then rank by vector+keyword+recency.

    Reuses the same weighted-scoring approach as the hybrid search endpoint
    without pagination (returns a flat list).
    """
    # Clamp parameters
    min_similarity = max(0.0, min(1.0, float(min_similarity)))
    limit = max(1, min(20, int(limit)))

    # 1. Embed query
    try:
        with PatentEmbedder() as embedder:
            query_embedding = embedder.generate_embedding(query)
    except Exception:
        logger.exception("search_patents: embedding failed")
        return {"results": [], "count": 0, "error": "Embedding generation failed."}

    if not query_embedding:
        return {"results": [], "count": 0}

    emb_str = f"[{','.join(str(x) for x in query_embedding)}]"

    # 2. Build filter clause
    filter_clauses: list[str] = ["TRUE"]
    if cpc_prefix:
        filter_clauses.append(
            "EXISTS (SELECT 1 FROM jsonb_array_elements_text(p.cpc) AS c WHERE c LIKE :cpc_prefix || '%')"
        )
    if assignee:
        # Partial match — any assignee containing the search string
        filter_clauses.append(
            "EXISTS (SELECT 1 FROM jsonb_array_elements_text(p.assignees) a WHERE a ILIKE '%' || :assignee || '%')"
        )

    filter_sql = " AND ".join(filter_clauses)

    # 3. Set HNSW recall
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))

    params = {
        "emb": emb_str,
        "q": query,
        "min_sim": min_similarity,
        "vw": _VW,
        "kw": _KW,
        "rw": _RW,
        "max_age": _MAX_AGE,
        "cpc_prefix": cpc_prefix,
        "assignee": assignee,
        "limit": limit,
    }

    raw_sql = text(_HYBRID_SQL_TEMPLATE.format(filters=filter_sql))
    result = await db.execute(raw_sql, params)
    rows = result.fetchall()

    # 4. Format results
    results: list[dict[str, Any]] = []
    for row in rows:
        abstract = row[2] or ""
        abstract_excerpt = abstract[:200]
        if len(abstract) > 200:
            abstract_excerpt = abstract_excerpt.rsplit(" ", 1)[0] + "…"

        assignees = row[3] or []
        similarity = float(row[5]) if row[5] is not None else 0.0

        results.append({
            "doc_id": row[0],
            "title": row[1] or "Untitled",
            "abstract_excerpt": abstract_excerpt,
            "similarity": round(similarity, 3),
            "assignees": assignees[:3],
            "publication_date": str(row[4]) if row[4] else "unknown",
        })

    logger.info(
        "search_patents tool: q='%s' → %d results (limit=%d, min_sim=%.2f)",
        query[:80], len(results), limit, min_similarity,
    )
    return {"results": results, "count": len(results)}


# ── Handler: open_patent ───────────────────────────────────────────

_OPEN_PATENT_SQL = text("""\
SELECT
    doc_id, title, abstract, claims_text,
    assignees, inventors, cpc,
    publication_date, estimated_expiry_date,
    legal_status, opportunity_score
FROM patent_publications
WHERE doc_id = :doc_id
LIMIT 1
""")


async def _open_patent(
    db: AsyncSession,
    doc_id: str,
) -> dict[str, Any]:
    """Look up a single patent by its doc_id."""
    result = await db.execute(_OPEN_PATENT_SQL, {"doc_id": doc_id})
    row = result.fetchone()

    if row is None:
        return {"error": "Patent not found", "doc_id": doc_id}

    # Truncate claims to first 3 independent claims
    claims_text = row[3] or ""
    claims_preview = claims_text
    if claims_text:
        # Split on numbered claim markers
        claim_parts = claims_text.split("\n")
        first_three = []
        claim_count = 0
        for part in claim_parts:
            stripped = part.strip()
            if stripped and (stripped[0].isdigit() or "claim" in stripped.lower()[:10]):
                claim_count += 1
                if claim_count <= 3:
                    first_three.append(stripped)
                else:
                    break
        if first_three:
            claims_preview = "\n".join(first_three)
            if claim_count > 3:
                claims_preview += f"\n… ({claim_count - 3} more claims)"

    abstract = row[2] or ""

    return {
        "doc_id": row[0],
        "title": row[1] or "Untitled",
        "abstract": abstract,
        "abstract_excerpt": abstract[:500] if len(abstract) > 500 else abstract,
        "claims_preview": claims_preview,
        "assignees": row[4] or [],
        "inventors": row[5] or [],
        "cpc": row[6] or [],
        "publication_date": str(row[7]) if row[7] else "unknown",
        "estimated_expiry": str(row[8]) if row[8] else None,
        "legal_status": row[9],
        "opportunity_score": float(row[10]) if row[10] is not None else None,
    }


# ── Handler: compare_companies ─────────────────────────────────────

_COMPARE_SQL = text("""\
WITH company_patents AS (
    SELECT
        jsonb_array_elements_text(p.assignees) AS company_name,
        p.doc_id,
        p.title,
        p.opportunity_score,
        p.publication_date,
        p.cpc
    FROM patent_publications p
    WHERE EXISTS (
        SELECT 1 FROM jsonb_array_elements_text(p.assignees) a
        WHERE EXISTS (
            SELECT 1 FROM unnest(CAST(:names AS text[])) AS n(name)
            WHERE a ILIKE '%' || n.name || '%'
        )
    )
),
aggregated AS (
    SELECT
        company_name,
        COUNT(*) AS total_patents,
        COUNT(*) FILTER (WHERE publication_date >= :three_years_ago) AS recent_patents,
        AVG(opportunity_score) AS avg_opportunity_score,
        MAX(opportunity_score) AS top_opportunity_score
    FROM company_patents
    GROUP BY company_name
),
top_patents AS (
    SELECT DISTINCT ON (company_name)
        company_name,
        doc_id,
        title,
        opportunity_score
    FROM company_patents
    WHERE opportunity_score IS NOT NULL
    ORDER BY company_name, opportunity_score DESC
)
SELECT
    a.company_name,
    a.total_patents,
    a.recent_patents,
    ROUND(COALESCE(a.avg_opportunity_score, 0)::numeric, 1) AS avg_opportunity,
    ROUND(COALESCE(a.top_opportunity_score, 0)::numeric, 1) AS top_opportunity,
    t.doc_id AS top_patent_id,
    t.title AS top_patent_title
FROM aggregated a
LEFT JOIN top_patents t ON a.company_name = t.company_name
ORDER BY a.total_patents DESC
""")


async def _compare_companies(
    db: AsyncSession,
    names: list[str],
) -> dict[str, Any]:
    """Compare patent portfolios for a list of company names.

    Matches assignees via ILIKE substring (permissive — 'Toyota' matches
    'Toyota Motor Corp' but also 'NotAToyotaClone LLC'). Acceptable for
    a chatbot tool; the model can filter false positives in its response.
    """
    if not isinstance(names, list) or len(names) < 2:
        return {"error": "Provide at least 2 company names to compare."}

    # Clamp to 5
    names = names[:5]

    from datetime import date, timedelta

    three_years_ago = date.today() - timedelta(days=3 * 365)

    result = await db.execute(
        _COMPARE_SQL,
        {"names": names, "three_years_ago": three_years_ago},
    )
    rows = result.fetchall()

    companies: list[dict[str, Any]] = []
    seen = set()
    for row in rows:
        name = row[0]
        if not name or name in seen:
            continue
        seen.add(name)
        companies.append({
            "company": name,
            "total_patents": int(row[1]) if row[1] else 0,
            "recent_patents_3y": int(row[2]) if row[2] else 0,
            "avg_opportunity_score": float(row[3]) if row[3] is not None else 0.0,
            "top_opportunity_score": float(row[4]) if row[4] is not None else 0.0,
            "top_patent_id": row[5],
            "top_patent_title": row[6] or "Untitled",
        })

    # If any requested names weren't found, include them with zeros
    for name in names:
        if name not in seen:
            companies.append({
                "company": name,
                "total_patents": 0,
                "recent_patents_3y": 0,
                "avg_opportunity_score": 0.0,
                "top_opportunity_score": 0.0,
                "top_patent_id": None,
                "top_patent_title": None,
            })

    logger.info(
        "compare_companies tool: %d names → %d matched",
        len(names), len([c for c in companies if c["total_patents"] > 0]),
    )
    return {"companies": companies, "compared": len(names)}


# ── Register handlers ──────────────────────────────────────────────

TOOL_HANDLERS.update({
    "search_patents": _search_patents,
    "open_patent": _open_patent,
    "compare_companies": _compare_companies,
})
