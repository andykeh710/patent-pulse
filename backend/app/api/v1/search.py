from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, func, select, text

from app.ai.embedder import EmbeddingError, PatentEmbedder
from app.api.deps import DbSession
from app.core.models import PatentPublication
from app.core.schemas import PaginatedResponse, PatentListItem

router = APIRouter()

# ── Hybrid search weights (per Phase 1 audit Section 6) ──────────
VECTOR_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.2
RECENCY_WEIGHT = 0.2
# Maximum patent age for recency scoring (20 years in seconds).
MAX_AGE_SECONDS = 365.25 * 24 * 3600 * 20

# ── Filter builder ────────────────────────────────────────────────


def _filter_clauses(cpc: str | None, assignee: str | None,
                    date_from: date | None, date_to: date | None) -> list[str]:
    """Build SQL WHERE clause fragments for optional filters."""
    clauses: list[str] = []
    if cpc:
        clauses.append("p.cpc @> ARRAY[:cpc]::text[]")
    if assignee:
        clauses.append("p.assignees @> ARRAY[:assignee]::text[]")
    if date_from:
        clauses.append("p.publication_date >= :date_from")
    if date_to:
        clauses.append("p.publication_date <= :date_to")
    return clauses


# ── Paged query helper ────────────────────────────────────────────


async def _paged_raw_query(db, select_sql: str, count_sql: str, params: dict,
                           page: int, page_size: int):
    """Execute a raw-SQL search with pagination.

    Returns (items, total) where items are lists of dicts (row._mapping).
    """
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    wrapped_count = f"SELECT COUNT(*) FROM ({count_sql}) AS _cnt"
    total_result = await db.execute(text(wrapped_count), params)
    total = total_result.scalar() or 0

    result = await db.execute(
        text(f"{select_sql} LIMIT :limit OFFSET :offset"),
        params,
    )
    rows = result.fetchall()
    return rows, total


# ── Mode-specific queries ─────────────────────────────────────────


_SEMANTIC_SELECT = """
    SELECT p.*, 1 - (p.embedding <=> CAST(:emb AS vector)) AS similarity
    FROM patent_publications p
    WHERE p.embedding IS NOT NULL
      AND {filters}
      AND 1 - (p.embedding <=> CAST(:emb AS vector)) >= :min_sim
    ORDER BY p.embedding <=> CAST(:emb AS vector) ASC
"""

_HYBRID_SELECT = """
    SELECT
        p.*,
        1 - (p.embedding <=> CAST(:emb AS vector)) AS vector_score,
        LEAST(ts_rank(p.search_vector, plainto_tsquery('english', :q)), 1.0)
          AS keyword_score,
        1 - LEAST(
          EXTRACT(EPOCH FROM (NOW() - p.publication_date)) / :max_age,
          1
        ) AS recency_score,
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
"""

# ── Endpoint ──────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[PatentListItem])
async def search_patents(
    db: DbSession,
    q: str = Query(..., min_length=0, description="Search query"),
    mode: str = Query(default="fulltext", description="Search mode: fulltext, semantic, or hybrid"),
    min_similarity: float = Query(default=0.0, ge=0, le=1),
    cpc: str | None = None,
    assignee: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[PatentListItem]:
    """Search patents by keyword (fulltext), semantic similarity, or hybrid.

    - **fulltext** (default): PostgreSQL full-text search via ts_rank.
      Backward-compatible with existing callers.
    - **semantic**: Pure vector search via HNSW cosine similarity.
    - **hybrid**: Weighted combination of vector (0.6), keyword (0.2),
      and recency (0.2) scores.
    """
    # ── Validate mode ──────────────────────────────────────────
    if mode not in ("fulltext", "semantic", "hybrid"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: '{mode}'. Use fulltext, semantic, or hybrid.",
        )

    # ── Fulltext mode (unchanged legacy path) ───────────────────
    if mode == "fulltext":
        if len(q) < 3:
            raise HTTPException(
                status_code=422,
                detail="Query must be at least 3 characters for fulltext search.",
            )
        search_query = func.plainto_tsquery("english", q)
        conditions = [PatentPublication.search_vector.op("@@")(search_query)]

        if cpc:
            conditions.append(PatentPublication.cpc.contains([cpc]))
        if assignee:
            conditions.append(PatentPublication.assignees.contains([assignee]))
        if date_from:
            conditions.append(PatentPublication.publication_date >= date_from)
        if date_to:
            conditions.append(PatentPublication.publication_date <= date_to)

        base_query = select(PatentPublication).where(and_(*conditions))

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        rank = func.ts_rank(PatentPublication.search_vector, search_query)
        offset = (page - 1) * page_size
        result = await db.execute(
            base_query.order_by(rank.desc()).offset(offset).limit(page_size)
        )
        patents = result.scalars().all()

        items = [PatentListItem.from_patent(p) for p in patents]
        pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ── Semantic / Hybrid mode ──────────────────────────────────
    if not q or not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Semantic and hybrid search require a non-empty query string.",
        )

    # Generate query embedding
    try:
        with PatentEmbedder() as embedder:
            query_embedding = embedder.generate_embedding(q)
    except EmbeddingError as exc:
        raise HTTPException(
            status_code=503,
            detail="Embedding generation failed. "
                   "Try mode=fulltext for keyword search.",
        ) from exc

    emb_str = f"[{','.join(str(x) for x in query_embedding)}]"

    # Build filter clauses
    filter_clauses = _filter_clauses(cpc, assignee, date_from, date_to)
    filter_sql = " AND ".join(filter_clauses) if filter_clauses else "TRUE"

    params: dict = {
        "emb": emb_str,
        "q": q,
        "min_sim": min_similarity,
        "cpc": cpc,
        "assignee": assignee,
        "date_from": date_from,
        "date_to": date_to,
        "max_age": MAX_AGE_SECONDS,
        "vw": VECTOR_WEIGHT,
        "kw": KEYWORD_WEIGHT,
        "rw": RECENCY_WEIGHT,
    }

    # Set HNSW search-time recall
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))

    if mode == "semantic":
        select_sql = _SEMANTIC_SELECT.format(filters=filter_sql)
        count_sql = _SEMANTIC_SELECT.format(filters=filter_sql)
    else:  # hybrid
        select_sql = _HYBRID_SELECT.format(filters=filter_sql)
        count_sql = _HYBRID_SELECT.format(filters=filter_sql)

    rows, total = await _paged_raw_query(
        db, select_sql, count_sql, params, page, page_size,
    )

    items: list[PatentListItem] = []
    for row in rows:
        mapping = row._mapping
        # Exclude computed columns from ORM construction
        exclude = {"similarity", "vector_score", "keyword_score", "recency_score"}
        patent = PatentPublication(
            **{k: v for k, v in mapping.items() if k not in exclude}
        )
        item = PatentListItem.from_patent(patent)
        item.similarity = float(mapping["similarity"])
        items.append(item)

    pages = (total + page_size - 1) // page_size if total else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
