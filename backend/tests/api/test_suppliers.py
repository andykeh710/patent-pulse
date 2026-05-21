from datetime import date

import pytest

from app.core.ai_models import Assignee
from app.core.models import PatentPublication


@pytest.mark.asyncio
async def test_supplier_summary_uses_patent_assignees(client, db_session):
    db_session.add_all(
        [
            PatentPublication(
                doc_id="USPTO:SUP001",
                office="USPTO",
                publication_number="SUP001",
                assignees=["Acme Corp"],
                cpc=["G06F", "H04L"],
                legal_status="GRANTED",
                estimated_expiry_date=date(2028, 1, 1),
                interesting_score=80.0,
            ),
            PatentPublication(
                doc_id="USPTO:SUP002",
                office="USPTO",
                publication_number="SUP002",
                assignees=["Beta LLC"],
                cpc=["A61B"],
                legal_status="PUBLISHED",
                opportunity_score=60.0,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/suppliers/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_suppliers"] == 2
    assert body["total_supplier_patents"] == 2
    assert body["average_patents_per_supplier"] == 1.0


@pytest.mark.asyncio
async def test_supplier_list_enriches_from_normalized_assignees(client, db_session):
    db_session.add(
        Assignee(
            normalized_name="acme corp",
            display_name="Acme Corp",
            country="US",
            entity_type="corporation",
            patent_count=1,
        )
    )
    db_session.add(
        PatentPublication(
            doc_id="USPTO:SUP003",
            office="USPTO",
            publication_number="SUP003",
            assignees=["Acme Corp"],
            cpc=["G06F"],
            legal_status="GRANTED",
            interesting_score=75.0,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/suppliers?country=US")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Acme Corp"
    assert body["items"][0]["country"] == "US"
    assert body["items"][0]["entity_type"] == "corporation"
    assert body["items"][0]["supplier_score"] > 0


@pytest.mark.asyncio
async def test_supplier_map_groups_by_country(client, db_session):
    db_session.add(
        Assignee(
            normalized_name="acme corp",
            display_name="Acme Corp",
            country="US",
            entity_type="corporation",
            patent_count=1,
        )
    )
    db_session.add(
        PatentPublication(
            doc_id="USPTO:SUP004",
            office="USPTO",
            publication_number="SUP004",
            assignees=["Acme Corp"],
            cpc=["G06F"],
            legal_status="GRANTED",
            opportunity_score=90.0,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/suppliers/map")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["country"] == "US"
    assert body[0]["supplier_count"] == 1
    assert body[0]["patent_count"] == 1
    assert body[0]["top_suppliers"][0]["name"] == "Acme Corp"
