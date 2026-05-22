import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import and_, select, update

from app.core.enums import LegalStatus, MaintenanceStatus
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

EXPIRY_WARNING_DAYS = 365
GRACE_PERIOD_DAYS = 180


@celery_app.task(
    bind=True,
    name="app.tasks.expiry_watch.update_expiry_flags",
)
def update_expiry_flags(self) -> dict:
    """
    Daily task to update maintenance status flags based on expiry dates.

    Returns:
        Stats dict with counts of updated records.
    """
    logger.info("Starting expiry watch update")

    stats = asyncio.run(_update_expiry_flags_async())

    logger.info(f"Expiry watch complete: {stats}")
    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.expiry_watch.get_expiring_soon",
)
def get_expiring_soon(self, days_ahead: int = 365) -> list[dict]:
    """
    Get list of patents expiring within the specified timeframe.

    Args:
        days_ahead: Number of days to look ahead

    Returns:
        List of patent summary dicts
    """
    patents = asyncio.run(_get_expiring_patents(days_ahead))

    return [
        {
            "id": str(p.id),
            "doc_id": p.doc_id,
            "title": p.title,
            "assignees": p.assignees,
            "estimated_expiry_date": p.estimated_expiry_date.isoformat()
            if p.estimated_expiry_date
            else None,
            "days_until_expiry": (p.estimated_expiry_date - date.today()).days
            if p.estimated_expiry_date
            else None,
        }
        for p in patents
    ]


async def _update_expiry_flags_async() -> dict:
    """Update maintenance status flags based on dates."""
    today = date.today()
    grace_cutoff = today + timedelta(days=GRACE_PERIOD_DAYS)

    stats = {"marked_expired": 0, "marked_grace_period": 0, "marked_current": 0}

    async with async_session_maker() as session:
        await session.execute(
            update(PatentPublication)
            .where(
                and_(
                    PatentPublication.estimated_expiry_date < today,
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                    PatentPublication.maintenance_status != MaintenanceStatus.LAPSED,
                )
            )
            .values(legal_status=LegalStatus.EXPIRED)
        )
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.legal_status == LegalStatus.EXPIRED)
        )
        stats["marked_expired"] = len(result.scalars().all())

        await session.execute(
            update(PatentPublication)
            .where(
                and_(
                    PatentPublication.estimated_expiry_date >= today,
                    PatentPublication.estimated_expiry_date < grace_cutoff,
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                )
            )
            .values(maintenance_status=MaintenanceStatus.GRACE_PERIOD)
        )

        await session.execute(
            update(PatentPublication)
            .where(
                and_(
                    PatentPublication.estimated_expiry_date >= grace_cutoff,
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                )
            )
            .values(maintenance_status=MaintenanceStatus.CURRENT)
        )

        await session.commit()

    return stats


async def _get_expiring_patents(days_ahead: int) -> list[PatentPublication]:
    """Get patents expiring within the specified days."""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication)
            .where(
                and_(
                    PatentPublication.estimated_expiry_date >= today,
                    PatentPublication.estimated_expiry_date <= cutoff,
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                )
            )
            .order_by(PatentPublication.estimated_expiry_date.asc())
            .limit(100)
        )
        return list(result.scalars().all())
