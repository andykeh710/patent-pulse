"""
Semantic Search API.

Uses pgvector for similarity search based on patent embeddings.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, text

from app.ai.embedder import PatentEmbedder
from app.api.deps import DbSession
from app.core.models import PatentPublication
from app.core.schemas import PatentListItem

router = APIRouter()


class SemanticSearchResult(BaseModel):
    patent: PatentListItem
    similarity: float
    distance: float


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult]
    total: int


class SimilarPatentsResponse(BaseModel):
    source_patent_id: str
    results: list[SemanticSearchResult]
    total: int


@router.post("/query", response_model=SemanticSearchResponse)
async def semantic_search(
    db: DbSession,
    query: str = Query(..., min_length=3, description="Natural language search query"),
    limit: int = Query(default=20, ge=1, le=100),
    min_similarity: float = Query(default=0.5, ge=0, le=1),
) -> SemanticSearchResponse:
    """
    Search patents using natural language.

    Converts the query to an embedding and finds similar patents using
    cosine similarity in pgvector.
    """
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    with PatentEmbedder() as embedder:
        query_embedding = embedder.generate_embedding(query)

    embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

    sql = text(
        """
        SELECT
            p.*,
            1 - (p.embedding <=> :embedding::vector) as similarity,
            p.embedding <=> :embedding::vector as distance
        FROM patent_publications p
        WHERE p.embedding IS NOT NULL
          AND 1 - (p.embedding <=> :embedding::vector) >= :min_similarity
        ORDER BY distance ASC
        LIMIT :limit
        """
    )

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "min_similarity": min_similarity,
            "limit": limit,
        },
    )
    rows = result.fetchall()

    results = []
    for row in rows:
        patent = PatentPublication(
            **{k: v for k, v in row._mapping.items() if k not in ("similarity", "distance")}
        )
        results.append(
            SemanticSearchResult(
                patent=PatentListItem.from_patent(patent),
                similarity=float(row.similarity),
                distance=float(row.distance),
            )
        )

    return SemanticSearchResponse(
        query=query,
        results=results,
        total=len(results),
    )


@router.get("/similar/{patent_id}", response_model=SimilarPatentsResponse)
async def find_similar_patents(
    db: DbSession,
    patent_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    min_similarity: float = Query(default=0.6, ge=0, le=1),
) -> SimilarPatentsResponse:
    """
    Find patents similar to a given patent.

    Uses the patent's embedding to find other patents with similar content.
    """
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    source_result = await db.execute(
        select(PatentPublication.embedding, PatentPublication.doc_id).where(
            PatentPublication.id == patent_id
        )
    )
    source_row = source_result.first()

    if not source_row:
        raise HTTPException(status_code=404, detail="Patent not found")

    embedding, doc_id = source_row

    if embedding is None:
        raise HTTPException(
            status_code=400,
            detail="Patent has no embedding. Generate embeddings first.",
        )

    embedding_list = list(embedding)
    embedding_str = f"[{','.join(str(x) for x in embedding_list)}]"

    sql = text(
        """
        SELECT
            p.*,
            1 - (p.embedding <=> :embedding::vector) as similarity,
            p.embedding <=> :embedding::vector as distance
        FROM patent_publications p
        WHERE p.embedding IS NOT NULL
          AND p.id != :patent_id
          AND 1 - (p.embedding <=> :embedding::vector) >= :min_similarity
        ORDER BY distance ASC
        LIMIT :limit
        """
    )

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "patent_id": patent_id,
            "min_similarity": min_similarity,
            "limit": limit,
        },
    )
    rows = result.fetchall()

    results = []
    for row in rows:
        patent = PatentPublication(
            **{k: v for k, v in row._mapping.items() if k not in ("similarity", "distance")}
        )
        results.append(
            SemanticSearchResult(
                patent=PatentListItem.from_patent(patent),
                similarity=float(row.similarity),
                distance=float(row.distance),
            )
        )

    return SimilarPatentsResponse(
        source_patent_id=str(patent_id),
        results=results,
        total=len(results),
    )


@router.get("/novelty/{patent_id}")
async def compute_novelty_score(
    db: DbSession,
    patent_id: UUID,
    compare_count: int = Query(default=20, ge=5, le=100),
) -> dict:
    """
    Compute novelty score for a patent.

    Novelty is measured as average distance from the most similar existing patents.
    Higher distance = more novel.
    """
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    source_result = await db.execute(
        select(
            PatentPublication.embedding,
            PatentPublication.cpc,
            PatentPublication.publication_date,
        ).where(PatentPublication.id == patent_id)
    )
    source_row = source_result.first()

    if not source_row:
        raise HTTPException(status_code=404, detail="Patent not found")

    embedding, cpc_codes, pub_date = source_row

    if embedding is None:
        raise HTTPException(status_code=400, detail="Patent has no embedding")

    embedding_list = list(embedding)
    embedding_str = f"[{','.join(str(x) for x in embedding_list)}]"

    sql = text(
        """
        SELECT
            p.embedding <=> :embedding::vector as distance
        FROM patent_publications p
        WHERE p.embedding IS NOT NULL
          AND p.id != :patent_id
          AND p.publication_date < :pub_date
        ORDER BY distance ASC
        LIMIT :limit
        """
    )

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "patent_id": patent_id,
            "pub_date": pub_date,
            "limit": compare_count,
        },
    )
    distances = [float(row[0]) for row in result.fetchall()]

    if not distances:
        return {
            "patent_id": str(patent_id),
            "novelty_score": 1.0,
            "average_distance": 1.0,
            "min_distance": 1.0,
            "compared_patents": 0,
            "note": "No prior patents found for comparison",
        }

    avg_distance = sum(distances) / len(distances)
    min_distance = min(distances)

    novelty_score = min(avg_distance * 1.5, 1.0)

    return {
        "patent_id": str(patent_id),
        "novelty_score": round(novelty_score, 4),
        "average_distance": round(avg_distance, 4),
        "min_distance": round(min_distance, 4),
        "compared_patents": len(distances),
    }
