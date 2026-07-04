"""Tests for embedding backfill task."""

from unittest.mock import patch

import pytest

from app.core.models import PatentPublication

# Matches the Vector(1536) column type
FAKE_DIM = 1536


def _fake_embedding(idx: int = 0) -> list[float]:
    """Return a deterministic 1536-dim vector."""
    return [float((idx + i) % 100) / 100.0 for i in range(FAKE_DIM)]


@pytest.mark.asyncio(loop_scope="function")
async def test_batch_generates_embeddings_in_chunks(db_session):
    """25 patents → 2 batch API calls (ceil(25/20)) → all get embeddings."""
    patents = []
    for i in range(25):
        p = PatentPublication(
            doc_id=f"USPTO:EMB{i:04d}",
            publication_number=f"EMB{i:04d}",
            office="USPTO",
            title=f"Patent {i}",
            abstract=f"Abstract for patent {i}",
            cpc=["G06F"],
            opportunity_score=50.0,
        )
        patents.append(p)
    db_session.add_all(patents)
    await db_session.commit()

    def _fake_embeddings(texts):
        return [_fake_embedding(i) for i in range(len(texts))]

    from app.tasks.embeddings import _batch_generate_embeddings_for_session

    with patch(
        "app.tasks.embeddings.PatentEmbedder.generate_batch_embeddings",
        side_effect=_fake_embeddings,
    ) as mock_batch:
        stats = await _batch_generate_embeddings_for_session(db_session, limit=30)

    assert stats["processed"] == 25
    assert stats["succeeded"] == 25
    assert stats["failed"] == 0
    assert stats["skipped"] == 0
    assert mock_batch.call_count == 2  # ceil(25/20)

    for p in patents:
        await db_session.refresh(p)
        assert p.embedding is not None
        assert len(list(p.embedding)) == FAKE_DIM


@pytest.mark.asyncio(loop_scope="function")
async def test_batch_skips_already_embedded(db_session):
    """Patents with existing embeddings are not re-processed."""
    existing = _fake_embedding(0)
    p1 = PatentPublication(
        doc_id="USPTO:EMB100",
        publication_number="EMB100",
        office="USPTO",
        title="Already Embedded",
        abstract="Has embedding",
        cpc=["G06F"],
        embedding=existing,
    )
    p2 = PatentPublication(
        doc_id="USPTO:EMB101",
        publication_number="EMB101",
        office="USPTO",
        title="Needs Embedding",
        abstract="No embedding yet",
        cpc=["G06F"],
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    new_emb = _fake_embedding(99)

    from app.tasks.embeddings import _batch_generate_embeddings_for_session

    with patch(
        "app.tasks.embeddings.PatentEmbedder.generate_batch_embeddings",
        return_value=[new_emb],
    ):
        stats = await _batch_generate_embeddings_for_session(db_session, limit=10)

    assert stats["processed"] == 1
    assert stats["succeeded"] == 1

    await db_session.refresh(p1)
    await db_session.refresh(p2)
    assert list(p1.embedding) == existing  # unchanged
    assert list(p2.embedding) == new_emb  # newly embedded


@pytest.mark.asyncio(loop_scope="function")
async def test_batch_skips_no_content_patents(db_session):
    """Patents with no embeddable text are skipped."""
    p = PatentPublication(
        doc_id="USPTO:EMB200",
        publication_number="EMB200",
        office="USPTO",
        title="",
        abstract=None,
        cpc=None,
    )
    db_session.add(p)
    await db_session.commit()

    from app.tasks.embeddings import _batch_generate_embeddings_for_session

    with patch(
        "app.tasks.embeddings.PatentEmbedder.generate_batch_embeddings",
    ) as mock_batch:
        stats = await _batch_generate_embeddings_for_session(db_session, limit=10)

    assert stats["processed"] == 0
    assert stats["skipped"] == 1
    mock_batch.assert_not_called()
