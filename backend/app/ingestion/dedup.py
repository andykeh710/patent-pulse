import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication

logger = logging.getLogger(__name__)


async def upsert_patent(
    session: AsyncSession,
    patent_data: dict,
) -> tuple[PatentPublication, bool]:
    """
    Insert or update a patent by doc_id.

    Uses INSERT ... ON CONFLICT (doc_id) DO UPDATE to be atomic.
    Never silently drops a record.

    Args:
        session: Database session
        patent_data: Normalized patent data dictionary

    Returns:
        Tuple of (PatentPublication record, was_created: bool)
    """
    doc_id = patent_data.get("doc_id")
    if not doc_id:
        raise ValueError("patent_data must include doc_id")

    existing = await session.execute(
        select(PatentPublication.id, PatentPublication.created_at).where(
            PatentPublication.doc_id == doc_id
        )
    )
    existing_row = existing.first()
    was_existing = existing_row is not None

    # Build update_data carefully:
    #  - Never overwrite 'id', 'created_at', or 'doc_id' (identity / audit fields)
    #  - Never overwrite enriched content fields with NULL. These columns are
    #    populated by downstream enrichment tasks (EPO OPS, Google Patents,
    #    summarizer). USPTO's initial ingest has abstract=None, claims=None, etc.,
    #    so blindly setting them on re-ingestion wipes out all enrichment.
    #  - Never overwrite AI-generated fields from ingestion; those come from
    #    the summarizer/scorer/embedder pipeline.
    _EXCLUDED_FROM_UPDATE = {"id", "created_at", "doc_id"}
    _ENRICHED_CONTENT_FIELDS = {
        "abstract",
        "claims_text",
        "description_text",
        "citations_backward",
        "family_members",
        "summary",
        "novel_applications",
        "interesting_score",
        "score_breakdown",
        "embedding",
        "summarized_at",
    }
    update_data: dict = {}
    for k, v in patent_data.items():
        if k in _EXCLUDED_FROM_UPDATE:
            continue
        # Never overwrite an enriched column with empty source data.
        if k in _ENRICHED_CONTENT_FIELDS and (v is None or v == "" or v == [] or v == {}):
            continue
        update_data[k] = v
    update_data["updated_at"] = datetime.utcnow()

    stmt = (
        insert(PatentPublication)
        .values(**patent_data)
        .on_conflict_do_update(
            index_elements=["doc_id"],
            set_=update_data,
        )
        .returning(PatentPublication)
    )

    result = await session.execute(stmt)
    await session.commit()

    record = result.scalar_one()
    await session.refresh(record)
    was_created = not was_existing

    if was_created:
        logger.info(f"Created new patent: {doc_id}")
    else:
        logger.debug(f"Updated existing patent: {doc_id}")

    return record, was_created


async def bulk_upsert_patents(
    session: AsyncSession,
    patents_data: list[dict],
) -> dict:
    """
    Bulk upsert multiple patents.

    Args:
        session: Database session
        patents_data: List of normalized patent data dictionaries

    Returns:
        Stats dict with created, updated, failed counts
    """
    stats = {"created": 0, "updated": 0, "failed": 0, "doc_ids": {"created": [], "updated": []}}

    for patent_data in patents_data:
        try:
            record, was_created = await upsert_patent(session, patent_data)
            if was_created:
                stats["created"] += 1
                stats["doc_ids"]["created"].append(record.doc_id)
            else:
                stats["updated"] += 1
                stats["doc_ids"]["updated"].append(record.doc_id)
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"Failed to upsert patent {patent_data.get('doc_id')}: {e}")

    return stats


async def get_patent_by_doc_id(
    session: AsyncSession,
    doc_id: str,
) -> PatentPublication | None:
    """Fetch a patent by its doc_id."""
    result = await session.execute(
        select(PatentPublication).where(PatentPublication.doc_id == doc_id)
    )
    return result.scalar_one_or_none()


async def get_unsummarized_patents(
    session: AsyncSession,
    limit: int = 100,
) -> list[PatentPublication]:
    """Get patents that haven't been summarized yet."""
    result = await session.execute(
        select(PatentPublication)
        .where(PatentPublication.summarized_at.is_(None))
        .where(PatentPublication.title.isnot(None))
        .order_by(PatentPublication.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
