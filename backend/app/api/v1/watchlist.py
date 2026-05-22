"""
Watchlist API.

Allows users to save patents for tracking.
Note: user_id is hardcoded as "anonymous" until Phase 4 auth.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.api.deps import DbSession
from app.core.models import PatentPublication
from app.core.schemas import PatentListItem
from app.core.theme_models import WatchlistItem

router = APIRouter()

DEFAULT_USER_ID = "anonymous"


class WatchlistAdd(BaseModel):
    patent_id: UUID
    note: str | None = None
    tags: list[str] = []


class WatchlistUpdate(BaseModel):
    note: str | None = None
    tags: list[str] | None = None


class WatchlistItemResponse(BaseModel):
    id: str
    patent: PatentListItem
    note: str | None
    tags: list[str]
    added_at: str


@router.get("", response_model=list[WatchlistItemResponse])
async def get_watchlist(
    db: DbSession,
    tag: str | None = None,
) -> list[WatchlistItemResponse]:
    """Get all items in the watchlist."""
    query = (
        select(WatchlistItem, PatentPublication)
        .join(PatentPublication, PatentPublication.id == WatchlistItem.patent_id)
        .where(WatchlistItem.user_id == DEFAULT_USER_ID)
    )

    if tag:
        query = query.where(WatchlistItem.tags.contains([tag]))

    query = query.order_by(WatchlistItem.added_at.desc())

    result = await db.execute(query)
    rows = result.all()

    return [
        WatchlistItemResponse(
            id=str(item.id),
            patent=PatentListItem.from_patent(patent),
            note=item.note,
            tags=item.tags or [],
            added_at=item.added_at.isoformat(),
        )
        for item, patent in rows
    ]


@router.post("", response_model=WatchlistItemResponse)
async def add_to_watchlist(db: DbSession, data: WatchlistAdd) -> WatchlistItemResponse:
    """Add a patent to the watchlist."""
    patent_id = data.patent_id

    patent_result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = patent_result.scalar_one_or_none()

    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == DEFAULT_USER_ID,
            WatchlistItem.patent_id == patent_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Patent already in watchlist")

    item = WatchlistItem(
        user_id=DEFAULT_USER_ID,
        patent_id=patent_id,
        note=data.note,
        tags=data.tags,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return WatchlistItemResponse(
        id=str(item.id),
        patent=PatentListItem.from_patent(patent),
        note=item.note,
        tags=item.tags or [],
        added_at=item.added_at.isoformat(),
    )


@router.patch("/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    db: DbSession, item_id: UUID, data: WatchlistUpdate
) -> WatchlistItemResponse:
    """Update a watchlist item's note or tags."""
    result = await db.execute(
        select(WatchlistItem, PatentPublication)
        .join(PatentPublication, PatentPublication.id == WatchlistItem.patent_id)
        .where(WatchlistItem.id == item_id)
        .where(WatchlistItem.user_id == DEFAULT_USER_ID)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    item, patent = row

    if data.note is not None:
        item.note = data.note
    if data.tags is not None:
        item.tags = data.tags

    await db.commit()
    await db.refresh(item)

    return WatchlistItemResponse(
        id=str(item.id),
        patent=PatentListItem.from_patent(patent),
        note=item.note,
        tags=item.tags or [],
        added_at=item.added_at.isoformat(),
    )


@router.delete("/{item_id}")
async def remove_from_watchlist(db: DbSession, item_id: UUID) -> dict:
    """Remove an item from the watchlist."""
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.id == item_id)
        .where(WatchlistItem.user_id == DEFAULT_USER_ID)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    await db.delete(item)
    await db.commit()

    return {"deleted": True}


@router.get("/check/{patent_id}")
async def check_in_watchlist(db: DbSession, patent_id: UUID) -> dict:
    """Check if a patent is in the watchlist."""
    result = await db.execute(
        select(WatchlistItem.id).where(
            WatchlistItem.user_id == DEFAULT_USER_ID,
            WatchlistItem.patent_id == patent_id,
        )
    )
    item = result.scalar_one_or_none()

    return {
        "in_watchlist": item is not None,
        "watchlist_item_id": str(item) if item else None,
    }


@router.get("/tags")
async def get_watchlist_tags(db: DbSession) -> list[str]:
    """Get all unique tags used in the watchlist."""
    result = await db.execute(
        select(WatchlistItem.tags)
        .where(WatchlistItem.user_id == DEFAULT_USER_ID)
        .where(WatchlistItem.tags.isnot(None))
    )
    rows = result.scalars().all()

    all_tags = set()
    for tags in rows:
        if tags:
            all_tags.update(tags)

    return sorted(all_tags)
