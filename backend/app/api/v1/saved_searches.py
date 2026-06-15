"""Saved searches for authenticated users (Sprint 4.5).

Stores query, filters, sort so users can reopen a named search
later.  Scoped to user — no sharing.  One user can have multiple
saved searches with the same name (the ID differentiates them).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.api.deps import DbSession, current_user
from app.core.ai_models import Base

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


# -- Model --


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column()
    query: Mapped[str] = mapped_column(default="")
    mode: Mapped[str] = mapped_column(default="hybrid")
    filters_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_by: Mapped[str] = mapped_column(default="relevance")
    sort_order: Mapped[str] = mapped_column(default="desc")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_opened_at: Mapped[datetime | None] = mapped_column(nullable=True)


# -- Schemas --


class SavedSearchCreate(BaseModel):
    name: str
    query: str = ""
    mode: str = "hybrid"
    filters_json: dict | None = None
    sort_by: str = "relevance"
    sort_order: str = "desc"


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    query: str
    mode: str
    filters_json: dict | None = None
    sort_by: str
    sort_order: str
    created_at: str
    updated_at: str
    last_opened_at: str | None = None


class SavedSearchList(BaseModel):
    items: list[SavedSearchResponse]
    total: int


# -- Endpoints --


@router.get("", response_model=SavedSearchList)
async def list_saved_searches(
    db: DbSession,
    user_id: str = Depends(current_user),
) -> SavedSearchList:
    """List saved searches for the authenticated user, newest first."""
    rows = (
        await db.execute(
            text(
                "SELECT * FROM saved_searches WHERE user_id = :uid "
                "ORDER BY updated_at DESC"
            ),
            {"uid": user_id},
        )
    ).fetchall()

    items = [
        SavedSearchResponse(
            id=str(r.id),
            name=r.name,
            query=r.query,
            mode=r.mode,
            filters_json=r.filters_json,
            sort_by=r.sort_by,
            sort_order=r.sort_order,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
            last_opened_at=r.last_opened_at.isoformat() if r.last_opened_at else None,
        )
        for r in rows
    ]
    return SavedSearchList(items=items, total=len(items))


@router.post("", response_model=SavedSearchResponse, status_code=201)
async def create_saved_search(
    body: SavedSearchCreate,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> SavedSearchResponse:
    """Create a saved search."""
    now = datetime.now(timezone.utc)
    search_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO saved_searches (id, user_id, name, query, mode, "
            "filters_json, sort_by, sort_order, created_at, updated_at) "
            "VALUES (:id, :uid, :name, :query, :mode, CAST(:filters AS jsonb), "
            ":sort_by, :sort_order, :now, :now)"
        ),
        {
            "id": search_id,
            "uid": user_id,
            "name": body.name,
            "query": body.query,
            "mode": body.mode,
            "filters": body.filters_json or "null",
            "sort_by": body.sort_by,
            "sort_order": body.sort_order,
            "now": now,
        },
    )
    await db.commit()
    return SavedSearchResponse(
        id=str(search_id),
        name=body.name,
        query=body.query,
        mode=body.mode,
        filters_json=body.filters_json,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


@router.delete("/{search_id}")
async def delete_saved_search(
    search_id: str,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> dict:
    """Delete a saved search. Only the owner can delete."""
    result = await db.execute(
        text(
            "DELETE FROM saved_searches WHERE id = :id AND user_id = :uid"
        ),
        {"id": search_id, "uid": user_id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"status": "deleted"}
