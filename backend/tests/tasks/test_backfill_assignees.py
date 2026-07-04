"""Tests for assignee normalization backfill task."""

import pytest
from sqlalchemy import text

from app.core.models import PatentPublication

NORMALIZE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION normalize_assignee(name text) RETURNS text AS $$
DECLARE
    result text;
BEGIN
    result := upper(trim(name));
    result := regexp_replace(result, '\\s*\\[[^\\]]+\\]\\s*$', '', 'g');
    result := replace(result, '.', '');
    result := regexp_replace(result, '[,]+$', '', 'g');
    result := regexp_replace(result, '\\s+INCORPORATED\\s*$', ' INC', 'g');
    result := regexp_replace(result, '\\s+CORPORATION\\s*$', ' CORP', 'g');
    result := regexp_replace(result, '\\s+LIMITED\\s+LIABILITY\\s+COMPANY\\s*$', ' LLC', 'g');
    result := regexp_replace(result, '\\s+LIMITED\\s*$', ' LTD', 'g');
    result := regexp_replace(result, '\\s+LTD\\s*$', ' LTD', 'g');
    result := regexp_replace(result, '\\s+INC\\s*$', ' INC', 'g');
    result := regexp_replace(result, '\\s+CORP\\s*$', ' CORP', 'g');
    result := regexp_replace(result, '\\s+COMPANY\\s*$', ' CO', 'g');
    result := regexp_replace(result, '\\s+CO\\s*$', ' CO', 'g');
    result := regexp_replace(result, '\\s+LLC\\s*$', ' LLC', 'g');
    result := regexp_replace(result, '\\s+GMBH\\s*$', ' GMBH', 'g');
    result := regexp_replace(result, '\\s+SA\\s*$', ' SA', 'g');
    result := replace(result, ',', '');
    result := regexp_replace(result, '\\s+', ' ', 'g');
    result := trim(result);
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""


@pytest.fixture(autouse=True)
async def _ensure_normalize_function(db_session) -> None:
    """Create the normalize_assignee function in the test DB.

    The conftest db_session fixture uses Base.metadata.create_all()
    which doesn't run Alembic migrations. PostgreSQL functions must
    be created explicitly for tests that depend on them.
    """
    await db_session.execute(text(NORMALIZE_FUNCTION_SQL))
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_populates_empty_assignees_table(db_session):
    """Fresh assignees table gets populated from patent_publications.assignees."""
    db_session.add_all(
        [
            PatentPublication(
                doc_id="USPTO:AB001",
                publication_number="AB001",
                office="USPTO",
                title="Patent One",
                assignees=["Acme Corporation"],
                cpc=["G06F"],
            ),
            PatentPublication(
                doc_id="USPTO:AB002",
                publication_number="AB002",
                office="USPTO",
                title="Patent Two",
                assignees=["Beta LLC", "Acme Corporation"],
                cpc=["H04L"],
            ),
        ]
    )
    await db_session.commit()

    from app.tasks.backfill_assignees import backfill_assignees_for_session

    stats = await backfill_assignees_for_session(db_session)

    # normalize_assignee("Acme Corporation") → "ACME CORPORATION"
    # normalize_assignee("Beta LLC") → "BETA LLC"
    assert stats["total_processed"] == 2
    assert stats["inserted"] == 2


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_is_idempotent(db_session):
    """Running backfill twice produces same count, second run inserts nothing."""
    db_session.add(
        PatentPublication(
            doc_id="USPTO:AB010",
            publication_number="AB010",
            office="USPTO",
            title="Solo Patent",
            assignees=["One Corp"],
            cpc=["G06F"],
        )
    )
    await db_session.commit()

    from app.tasks.backfill_assignees import backfill_assignees_for_session

    # First run
    stats1 = await backfill_assignees_for_session(db_session)
    assert stats1["total_processed"] == 1
    assert stats1["inserted"] == 1

    # Second run — same data, nothing new to insert
    stats2 = await backfill_assignees_for_session(db_session)
    assert stats2["total_processed"] == 1
    assert stats2["inserted"] == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_updates_patent_count_on_new_patents(db_session):
    """When new patents are added, re-running updates patent_count correctly."""
    db_session.add(
        PatentPublication(
            doc_id="USPTO:AB020",
            publication_number="AB020",
            office="USPTO",
            title="First",
            assignees=["Dual Corp"],
            cpc=["G06F"],
        )
    )
    await db_session.commit()

    from app.tasks.backfill_assignees import backfill_assignees_for_session

    # Initial backfill
    await backfill_assignees_for_session(db_session)

    # Add more patents for the same normalized assignee
    db_session.add_all(
        [
            PatentPublication(
                doc_id="USPTO:AB021",
                publication_number="AB021",
                office="USPTO",
                title="Second",
                assignees=["DUAL CORP"],
                cpc=["H04L"],
            ),
            PatentPublication(
                doc_id="USPTO:AB022",
                publication_number="AB022",
                office="USPTO",
                title="Third",
                assignees=["Dual Corp."],
                cpc=["A61B"],
            ),
        ]
    )
    await db_session.commit()

    # Re-run — should update patent_count from 1 → 3
    stats = await backfill_assignees_for_session(db_session)
    assert stats["total_processed"] == 1  # still one normalized name
    assert stats["inserted"] == 0  # no new names
    assert stats["updated"] == 1

    # Verify patent_count in the table
    from sqlalchemy import text

    result = await db_session.execute(text("SELECT normalized_name, patent_count FROM assignees"))
    rows = result.fetchall()
    assert len(rows) == 1
    # normalize_assignee collapses "Dual Corp", "DUAL CORP", "Dual Corp."
    # into one normalized name — patent_count should be 3
    assert rows[0].patent_count == 3


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_handles_variant_assignee_spellings(db_session):
    """Different case/suffix variants of same company normalize together."""
    db_session.add_all(
        [
            PatentPublication(
                doc_id="USPTO:AB030",
                publication_number="AB030",
                office="USPTO",
                title="A",
                assignees=["International Business Machines Corp"],
                cpc=["G06F"],
            ),
            PatentPublication(
                doc_id="USPTO:AB031",
                publication_number="AB031",
                office="USPTO",
                title="B",
                assignees=["IBM Corporation"],
                cpc=["H04L"],
            ),
            PatentPublication(
                doc_id="USPTO:AB032",
                publication_number="AB032",
                office="USPTO",
                title="C",
                assignees=["INTL BUSINESS MACHINES INC"],
                cpc=["A61B"],
            ),
        ]
    )
    await db_session.commit()

    from app.tasks.backfill_assignees import backfill_assignees_for_session

    stats = await backfill_assignees_for_session(db_session)

    # All three normalize differently (IBM vs International Business Machines
    # are different strings). normalize_assignee doesn't do semantic merge.
    # "International Business Machines Corp" → "INTERNATIONAL BUSINESS MACHINES CORP"
    # "IBM Corporation" → "IBM CORPORATION"
    # "INTL BUSINESS MACHINES INC" → "INTL BUSINESS MACHINES INC"
    assert stats["total_processed"] == 3  # three distinct normalized names


# ── Post-Launch: normalization-only test (no heuristic entity_type) ──


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_normalizes_production_names(db_session):
    """Backfill should normalize names and set patent_count. entity_type
    stays NULL — enriched separately from authoritative sources."""
    names = [
        "SAMSUNG ELECTRONICS CO LTD",
        "INTERNATIONAL BUSINESS MACHINES CORP",
        "TOYOTA JIDOSHA KABUSHIKI KAISHA",
        "QUALCOMM INC",
        "TAIWAN SEMICONDUCTOR MANUFACTURING COMPANY LTD",
        "APPLE INC",
    ]
    for name in names:
        db_session.add(
            PatentPublication(
                doc_id=f"USPTO:TEST_NORM_{name[:15].replace(' ', '_')}",
                publication_number=f"TEST_{hash(name) % 1000000:06d}",
                office="USPTO",
                title="Test",
                assignees=[name],
                cpc=["G06F"],
            )
        )
    await db_session.commit()

    from app.tasks.backfill_assignees import backfill_assignees_for_session

    stats = await backfill_assignees_for_session(db_session)
    assert stats["total_processed"] >= 1

    # Verify normalization populated rows (entity_type stays NULL)
    from sqlalchemy import select

    from app.core.ai_models import Assignee

    result = await db_session.execute(select(Assignee))
    rows = result.scalars().all()
    assert len(rows) > 0, "Backfill should populate assignees table"
    for row in rows:
        assert row.normalized_name is not None
        assert row.display_name is not None
        # entity_type intentionally NULL — not set by this backfill
        assert row.entity_type is None, (
            f"entity_type should be NULL for '{row.normalized_name}' — "
            "heuristic classification removed. Enrichment requires "
            "authoritative external data."
        )
        assert row.patent_count > 0
