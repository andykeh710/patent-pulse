import uuid
from datetime import date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication


@pytest.mark.asyncio
async def test_patent_publication_create(db_session: AsyncSession) -> None:
    patent = PatentPublication(
        doc_id="USPTO:TEST001",
        office="USPTO",
        publication_number="TEST001",
        title="Test Patent",
        abstract="Test abstract",
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    assert patent.id is not None
    assert isinstance(patent.id, uuid.UUID)
    assert patent.doc_id == "USPTO:TEST001"
    assert patent.created_at is not None


@pytest.mark.asyncio
async def test_patent_publication_json_fields(db_session: AsyncSession) -> None:
    patent = PatentPublication(
        doc_id="USPTO:TEST002",
        office="USPTO",
        publication_number="TEST002",
        assignees=["Company A", "Company B"],
        inventors=["Inventor 1"],
        cpc=["G06F 21/00", "H04L 9/32"],
        ipc=["G06F 21/00"],
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    assert patent.assignees == ["Company A", "Company B"]
    assert patent.inventors == ["Inventor 1"]
    assert len(patent.cpc) == 2
    assert "G06F 21/00" in patent.cpc


@pytest.mark.asyncio
async def test_patent_publication_dates(db_session: AsyncSession) -> None:
    patent = PatentPublication(
        doc_id="USPTO:TEST003",
        office="USPTO",
        publication_number="TEST003",
        filing_date=date(2022, 1, 15),
        grant_date=date(2024, 3, 15),
        estimated_expiry_date=date(2042, 1, 15),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    assert patent.filing_date == date(2022, 1, 15)
    assert patent.grant_date == date(2024, 3, 15)
    assert patent.estimated_expiry_date == date(2042, 1, 15)


@pytest.mark.asyncio
async def test_patent_publication_summary(db_session: AsyncSession) -> None:
    summary = {
        "what_it_is": "A secure authentication system",
        "problem_solved": "User authentication security",
        "how_it_works": "Uses biometric data",
        "commercial_significance": "Improves security",
        "who_should_care": ["Security teams", "IT departments"],
        "novel_applications": [{"application": "Mobile auth", "label": "SPECULATIVE"}],
        "confidence_note": "High confidence",
        "source_spans": [],
    }

    patent = PatentPublication(
        doc_id="USPTO:TEST004",
        office="USPTO",
        publication_number="TEST004",
        summary=summary,
        summarized_at=datetime.utcnow(),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    assert patent.summary is not None
    assert patent.summary["what_it_is"] == "A secure authentication system"
    assert patent.summarized_at is not None


@pytest.mark.asyncio
async def test_patent_publication_unique_doc_id(db_session: AsyncSession) -> None:
    patent1 = PatentPublication(
        doc_id="USPTO:UNIQUE001",
        office="USPTO",
        publication_number="UNIQUE001",
    )
    db_session.add(patent1)
    await db_session.commit()

    patent2 = PatentPublication(
        doc_id="USPTO:UNIQUE001",
        office="USPTO",
        publication_number="UNIQUE001",
    )
    db_session.add(patent2)

    with pytest.raises(Exception):
        await db_session.commit()
