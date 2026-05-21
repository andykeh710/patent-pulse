from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication
from app.ingestion import dedup
from app.ingestion.dedup import (
    bulk_upsert_patents,
    get_patent_by_doc_id,
    get_unsummarized_patents,
    upsert_patent,
)


def test_build_update_values_preserves_authoritative_fields_on_sparse_reingest() -> None:
    update_values = dedup._build_update_values(
        {
            "doc_id": "USPTO:12345678",
            "family_id": None,
            "priority_date": None,
            "estimated_expiry_date": date(2042, 1, 15),
        }
    )

    assert "doc_id" not in update_values
    assert "family_id" not in update_values
    assert "priority_date" not in update_values
    assert "estimated_expiry_date" not in update_values


@pytest.mark.asyncio
async def test_upsert_creates_new_patent(
    db_session: AsyncSession, sample_patent_data: dict
) -> None:
    record, was_created = await upsert_patent(db_session, sample_patent_data)

    assert was_created is True
    assert record.doc_id == sample_patent_data["doc_id"]
    assert record.title == sample_patent_data["title"]


@pytest.mark.asyncio
async def test_upsert_updates_existing_patent(
    db_session: AsyncSession, sample_patent_data: dict
) -> None:
    record1, created1 = await upsert_patent(db_session, sample_patent_data)
    assert created1 is True

    updated_data = {**sample_patent_data, "title": "Updated Title"}
    record2, created2 = await upsert_patent(db_session, updated_data)

    assert created2 is False
    assert record2.id == record1.id
    assert record2.title == "Updated Title"


@pytest.mark.asyncio
async def test_upsert_preserves_existing_authoritative_fields_on_sparse_reingest(
    db_session: AsyncSession, sample_patent_data: dict
) -> None:
    original_data = {
        **sample_patent_data,
        "family_id": "INPADOC-FAMILY-1",
        "priority_date": date(2020, 1, 15),
        "estimated_expiry_date": date(2040, 1, 15),
    }
    await upsert_patent(db_session, original_data)

    sparse_reingest = {
        **sample_patent_data,
        "family_id": None,
        "priority_date": None,
        "estimated_expiry_date": date(2042, 1, 15),
    }
    record, created = await upsert_patent(db_session, sparse_reingest)

    assert created is False
    assert record.family_id == "INPADOC-FAMILY-1"
    assert record.priority_date == date(2020, 1, 15)
    assert record.estimated_expiry_date == date(2040, 1, 15)


@pytest.mark.asyncio
async def test_upsert_is_idempotent(
    db_session: AsyncSession, sample_patent_data: dict
) -> None:
    await upsert_patent(db_session, sample_patent_data)
    await upsert_patent(db_session, sample_patent_data)
    record, _ = await upsert_patent(db_session, sample_patent_data)

    all_patents = await db_session.execute(
        PatentPublication.__table__.select().where(
            PatentPublication.doc_id == sample_patent_data["doc_id"]
        )
    )
    assert len(all_patents.fetchall()) == 1


@pytest.mark.asyncio
async def test_upsert_missing_doc_id_raises(db_session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="must include doc_id"):
        await upsert_patent(db_session, {"title": "No doc_id"})


@pytest.mark.asyncio
async def test_get_patent_by_doc_id(
    db_session: AsyncSession, sample_patent_data: dict
) -> None:
    await upsert_patent(db_session, sample_patent_data)

    result = await get_patent_by_doc_id(db_session, sample_patent_data["doc_id"])
    assert result is not None
    assert result.doc_id == sample_patent_data["doc_id"]


@pytest.mark.asyncio
async def test_get_patent_by_doc_id_not_found(db_session: AsyncSession) -> None:
    result = await get_patent_by_doc_id(db_session, "NONEXISTENT:123")
    assert result is None


@pytest.mark.asyncio
async def test_bulk_upsert_patents(db_session: AsyncSession) -> None:
    patents = [
        {
            "doc_id": "USPTO:BULK001",
            "office": "USPTO",
            "publication_number": "BULK001",
            "title": "Patent 1",
        },
        {
            "doc_id": "USPTO:BULK002",
            "office": "USPTO",
            "publication_number": "BULK002",
            "title": "Patent 2",
        },
    ]

    stats = await bulk_upsert_patents(db_session, patents)

    assert stats["created"] == 2
    assert stats["updated"] == 0
    assert stats["failed"] == 0

    stats2 = await bulk_upsert_patents(db_session, patents)
    assert stats2["created"] == 0
    assert stats2["updated"] == 2


@pytest.mark.asyncio
async def test_get_unsummarized_patents(db_session: AsyncSession) -> None:
    patents = [
        {
            "doc_id": "USPTO:UNSUM001",
            "office": "USPTO",
            "publication_number": "UNSUM001",
            "title": "Unsummarized Patent",
        },
        {
            "doc_id": "USPTO:UNSUM002",
            "office": "USPTO",
            "publication_number": "UNSUM002",
            "title": None,
        },
    ]

    for p in patents:
        await upsert_patent(db_session, p)

    result = await get_unsummarized_patents(db_session, limit=10)

    assert len(result) == 1
    assert result[0].doc_id == "USPTO:UNSUM001"
