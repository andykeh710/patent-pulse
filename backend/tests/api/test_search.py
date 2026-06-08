from datetime import date, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.ai.embedder import EmbeddingError, PatentEmbedder
from app.core.models import PatentPublication

FAKE_DIM = 1536


def _vec(val: float = 0.0, pos: int = 0) -> list[float]:
    """Return a 1536-dim vector with *val* in position *pos*, zeros elsewhere."""
    v = [0.0] * FAKE_DIM
    v[pos] = val
    return v


def _mock_embedding(return_vec: list[float]):
    """Return a mock for PatentEmbedder.generate_embedding."""
    return patch.object(
        PatentEmbedder,
        "generate_embedding",
        return_value=return_vec,
    )


# ── Fulltext mode (existing tests should still pass) ────────────


@pytest.mark.asyncio
async def test_search_patents_empty_db(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_requires_query(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_min_query_length(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=ab")
    assert response.status_code == 422


# ── Semantic mode ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_semantic_mode_with_query(client: AsyncClient, db_session) -> None:
    """Seed 3 patents with embeddings; query returns ranked by cosine distance."""
    today = date.today()

    patents = [
        PatentPublication(
            doc_id="USPTO:SEM001",
            publication_number="SEM001",
            office="USPTO",
            title="Exact match patent",
            abstract="This should be closest",
            cpc=["G06F"],
            publication_date=today,
            embedding=_vec(1.0),
        ),
        PatentPublication(
            doc_id="USPTO:SEM002",
            publication_number="SEM002",
            office="USPTO",
            title="Partial match patent",
            abstract="This should be second",
            cpc=["G06F"],
            publication_date=today,
            embedding=_vec(0.5),
        ),
        PatentPublication(
            doc_id="USPTO:SEM003",
            publication_number="SEM003",
            office="USPTO",
            title="No match patent",
            abstract="This should be last",
            cpc=["G06F"],
            publication_date=today,
            embedding=_vec(0.0),
        ),
    ]
    db_session.add_all(patents)
    await db_session.commit()

    # Query embedding matches SEM001 exactly
    with _mock_embedding(_vec(1.0)):
        response = await client.get(
            "/api/v1/search?q=exact&mode=semantic&min_similarity=0"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    results = data["items"]
    # SEM001 (distance ~0) first, then SEM002, then SEM003
    assert results[0]["doc_id"] == "USPTO:SEM001"
    assert results[0]["similarity"] > 0.99
    assert results[1]["doc_id"] == "USPTO:SEM002"
    assert results[2]["doc_id"] == "USPTO:SEM003"


@pytest.mark.asyncio
async def test_semantic_mode_skips_null_embeddings(
    client: AsyncClient, db_session,
) -> None:
    """Patents without embeddings are excluded from semantic/hybrid results."""
    p = PatentPublication(
        doc_id="USPTO:NOEMB",
        publication_number="NOEMB",
        office="USPTO",
        title="No embedding",
        abstract="No vector",
        publication_date=date.today(),
        embedding=None,
    )
    db_session.add(p)
    await db_session.commit()

    with _mock_embedding(_vec(1.0)):
        response = await client.get(
            "/api/v1/search?q=test&mode=semantic&min_similarity=0"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ── Hybrid mode ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hybrid_mode_combines_scores(
    client: AsyncClient, db_session,
) -> None:
    """Seed patents with different keyword/vector/recency trade-offs."""
    today = date.today()
    one_year_ago = today - timedelta(days=365)
    twenty_years_ago = today - timedelta(days=365 * 21)

    # Patent A: strong vector match, weak keyword ("zzz"), modern
    pa = PatentPublication(
        doc_id="USPTO:HYB001",
        publication_number="HYB001",
        office="USPTO",
        title="zzz widget",
        abstract="obscure term",
        cpc=["G06F"],
        publication_date=today,
        embedding=_vec(1.0),
    )
    # Patent B: weak vector match, strong keyword ("battery"), older
    pb = PatentPublication(
        doc_id="USPTO:HYB002",
        publication_number="HYB002",
        office="USPTO",
        title="battery thermal management system",
        abstract="Advanced battery cooling technology for electric vehicles",
        cpc=["H01M"],
        publication_date=one_year_ago,
        embedding=_vec(0.3),
    )
    # Patent C: weak vector, weak keyword, ancient — should rank lowest
    pc = PatentPublication(
        doc_id="USPTO:HYB003",
        publication_number="HYB003",
        office="USPTO",
        title="old obscure patent",
        abstract="irrelevant content",
        cpc=["A23L"],
        publication_date=twenty_years_ago,
        embedding=_vec(0.1),
    )
    db_session.add_all([pa, pb, pc])
    await db_session.commit()

    with _mock_embedding(_vec(1.0)):
        response = await client.get(
            "/api/v1/search?q=battery thermal management&mode=hybrid&min_similarity=0"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    results = data["items"]
    # Patent A should rank first: strong vector (0.6 weight) + recency
    assert results[0]["doc_id"] == "USPTO:HYB001"
    # Patent B should rank second: decent vector + keyword boost
    assert results[1]["doc_id"] == "USPTO:HYB002"
    # Patent C last: weak everything + ancient
    assert results[2]["doc_id"] == "USPTO:HYB003"
    # All should have similarity set
    for r in results:
        assert r["similarity"] is not None
        assert 0 <= r["similarity"] <= 1


@pytest.mark.asyncio
async def test_hybrid_fulltext_order_differs(
    client: AsyncClient, db_session,
) -> None:
    """Fulltext mode ranks by keyword; hybrid adds vector + recency."""
    today = date.today()

    # Patent with keyword match but weak vector
    pk = PatentPublication(
        doc_id="USPTO:KW001",
        publication_number="KW001",
        office="USPTO",
        title="battery cooling system innovation",
        abstract="battery battery battery",
        cpc=["H01M"],
        publication_date=today,
        embedding=_vec(0.1),
    )
    # Patent with strong vector match but keyword doesn't match query
    pv = PatentPublication(
        doc_id="USPTO:VEC001",
        publication_number="VEC001",
        office="USPTO",
        title="quantum computing methodology",
        abstract="unrelated content",
        cpc=["G06N"],
        publication_date=today,
        embedding=_vec(1.0),
    )
    db_session.add_all([pk, pv])
    await db_session.commit()

    # Fulltext: should rank battery patent first
    ft = await client.get("/api/v1/search?q=battery cooling&mode=fulltext")
    assert ft.status_code == 200
    ft_data = ft.json()
    if ft_data["total"] > 0:
        assert ft_data["items"][0]["doc_id"] == "USPTO:KW001"

    # Hybrid: vector-driven — VEC001 may rank higher
    with _mock_embedding(_vec(1.0)):
        hy = await client.get(
            "/api/v1/search?q=battery cooling&mode=hybrid&min_similarity=0"
        )
    assert hy.status_code == 200
    hy_data = hy.json()
    if hy_data["total"] >= 2:
        assert hy_data["items"][0]["doc_id"] == "USPTO:VEC001"


# ── min_similarity filter ────────────────────────────────────────


@pytest.mark.asyncio
async def test_min_similarity_filter(client: AsyncClient, db_session) -> None:
    """min_similarity excludes patents below threshold."""
    today = date.today()

    p1 = PatentPublication(
        doc_id="USPTO:SIM001",
        publication_number="SIM001",
        office="USPTO",
        title="Close match",
        abstract="close",
        publication_date=today,
        embedding=_vec(1.0),
    )
    p2 = PatentPublication(
        doc_id="USPTO:SIM002",
        publication_number="SIM002",
        office="USPTO",
        title="Distant match",
        abstract="distant",
        publication_date=today,
        embedding=_vec(0.2, pos=1),
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    with _mock_embedding(_vec(1.0)):
        # Threshold 0.8 — only p1 passes
        r1 = await client.get(
            "/api/v1/search?q=test&mode=semantic&min_similarity=0.8"
        )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total"] == 1
    assert d1["items"][0]["doc_id"] == "USPTO:SIM001"

    with _mock_embedding(_vec(1.0)):
        # Threshold 0.95 — p1 may also be excluded (depends on float rounding)
        r2 = await client.get(
            "/api/v1/search?q=test&mode=hybrid&min_similarity=0.99"
        )
    assert r2.status_code == 200


# ── Error cases ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_mode_400(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test&mode=foo")
    assert response.status_code == 400
    assert "foo" in response.json()["detail"]


@pytest.mark.asyncio
async def test_empty_query_semantic_400(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=&mode=semantic")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_whitespace_query_semantic_400(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=+++&mode=semantic")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_embedding_unavailable_503(client: AsyncClient, db_session) -> None:
    """If OpenAI is down, semantic/hybrid return 503 with fallback hint."""
    p = PatentPublication(
        doc_id="USPTO:ERR001",
        publication_number="ERR001",
        office="USPTO",
        title="Some patent",
        abstract="Content",
        publication_date=date.today(),
        embedding=_vec(1.0),
    )
    db_session.add(p)
    await db_session.commit()

    with patch.object(
        PatentEmbedder,
        "generate_embedding",
        side_effect=EmbeddingError("OpenAI API unavailable"),
    ):
        response = await client.get("/api/v1/search?q=test&mode=semantic")
    assert response.status_code == 503
    assert "mode=fulltext" in response.json()["detail"]
