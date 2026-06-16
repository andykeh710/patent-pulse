"""
Theme Management API.

Themes are tracked technology areas defined by CPC prefixes and keywords.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from app.api.deps import DbSession, current_user
from app.core.models import PatentPublication
from app.core.schemas import PaginatedResponse, PatentListItem
from app.core.theme_models import Theme, ThemeMatch

router = APIRouter()


class ThemeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    cpc_prefixes: list[str] = []
    assignee_keywords: list[str] = []
    title_keywords: list[str] = []
    keywords: list[str] | None = None
    opportunity_tags: list[str] | None = None
    min_opportunity_score: float | None = None
    user_id: str | None = None


class ThemeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cpc_prefixes: list[str] | None = None
    assignee_keywords: list[str] | None = None
    title_keywords: list[str] | None = None
    keywords: list[str] | None = None
    opportunity_tags: list[str] | None = None
    min_opportunity_score: float | None = None
    is_active: bool | None = None


class ThemeResponse(BaseModel):
    id: str
    name: str
    description: str | None
    cpc_prefixes: list[str]
    assignee_keywords: list[str]
    title_keywords: list[str]
    keywords: list[str] | None
    opportunity_tags: list[str] | None
    min_opportunity_score: float | None
    user_id: str | None
    is_active: bool
    patent_count: int
    created_at: str


class ThemeStats(BaseModel):
    theme_id: str
    name: str
    total_matches: int
    recent_matches: int
    avg_score: float
    top_assignees: list[dict]


@router.get("", response_model=list[ThemeResponse])
async def list_themes(db: DbSession, include_inactive: bool = False) -> list[ThemeResponse]:
    """List all themes."""
    query = select(Theme)
    if not include_inactive:
        query = query.where(Theme.is_active.is_(True))

    result = await db.execute(query.order_by(Theme.name))
    themes = result.scalars().all()

    # Single GROUP BY query to avoid N+1
    count_query = (
        select(ThemeMatch.theme_id, func.count(ThemeMatch.id).label("cnt"))
        .group_by(ThemeMatch.theme_id)
    )
    count_result = await db.execute(count_query)
    count_map = {row.theme_id: row.cnt for row in count_result}

    responses = []
    for theme in themes:
        patent_count = count_map.get(theme.id, 0)

        responses.append(
            ThemeResponse(
                id=str(theme.id),
                name=theme.name,
                description=theme.description,
                cpc_prefixes=theme.cpc_prefixes or [],
                assignee_keywords=theme.assignee_keywords or [],
                title_keywords=theme.title_keywords or [],
                keywords=theme.keywords,
                opportunity_tags=theme.opportunity_tags,
                min_opportunity_score=theme.min_opportunity_score,
                user_id=theme.user_id,
                is_active=theme.is_active,
                patent_count=patent_count,
                created_at=theme.created_at.isoformat(),
            )
        )

    return responses


@router.post("", response_model=ThemeResponse)
async def create_theme(
    db: DbSession,
    theme_data: ThemeCreate,
    user_id: str = Depends(current_user),
) -> ThemeResponse:
    """Create a new theme. User-scoped — the authenticated user's ID is used."""
    existing = await db.execute(select(Theme).where(Theme.name == theme_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Theme with this name already exists")

    theme = Theme(
        name=theme_data.name,
        description=theme_data.description,
        cpc_prefixes=theme_data.cpc_prefixes,
        assignee_keywords=theme_data.assignee_keywords,
        title_keywords=theme_data.title_keywords,
        keywords=theme_data.keywords,
        opportunity_tags=theme_data.opportunity_tags,
        min_opportunity_score=theme_data.min_opportunity_score,
        user_id=user_id,  # use authenticated user's ID
    )
    db.add(theme)
    await db.commit()
    await db.refresh(theme)

    return ThemeResponse(
        id=str(theme.id),
        name=theme.name,
        description=theme.description,
        cpc_prefixes=theme.cpc_prefixes or [],
        assignee_keywords=theme.assignee_keywords or [],
        title_keywords=theme.title_keywords or [],
        keywords=theme.keywords,
        opportunity_tags=theme.opportunity_tags,
        min_opportunity_score=theme.min_opportunity_score,
        user_id=theme.user_id,
        is_active=theme.is_active,
        patent_count=0,
        created_at=theme.created_at.isoformat(),
    )


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(db: DbSession, theme_id: UUID) -> ThemeResponse:
    """Get a specific theme."""
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    count_result = await db.execute(
        select(func.count(ThemeMatch.id)).where(ThemeMatch.theme_id == theme.id)
    )
    patent_count = count_result.scalar() or 0

    return ThemeResponse(
        id=str(theme.id),
        name=theme.name,
        description=theme.description,
        cpc_prefixes=theme.cpc_prefixes or [],
        assignee_keywords=theme.assignee_keywords or [],
        title_keywords=theme.title_keywords or [],
        keywords=theme.keywords,
        opportunity_tags=theme.opportunity_tags,
        min_opportunity_score=theme.min_opportunity_score,
        user_id=theme.user_id,
        is_active=theme.is_active,
        patent_count=patent_count,
        created_at=theme.created_at.isoformat(),
    )


@router.patch("/{theme_id}", response_model=ThemeResponse)
async def update_theme(
    db: DbSession, theme_id: UUID, theme_data: ThemeUpdate
) -> ThemeResponse:
    """Update a theme."""
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    update_data = theme_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(theme, key, value)

    await db.commit()
    await db.refresh(theme)

    count_result = await db.execute(
        select(func.count(ThemeMatch.id)).where(ThemeMatch.theme_id == theme.id)
    )
    patent_count = count_result.scalar() or 0

    return ThemeResponse(
        id=str(theme.id),
        name=theme.name,
        description=theme.description,
        cpc_prefixes=theme.cpc_prefixes or [],
        assignee_keywords=theme.assignee_keywords or [],
        title_keywords=theme.title_keywords or [],
        keywords=theme.keywords,
        opportunity_tags=theme.opportunity_tags,
        min_opportunity_score=theme.min_opportunity_score,
        user_id=theme.user_id,
        is_active=theme.is_active,
        patent_count=patent_count,
        created_at=theme.created_at.isoformat(),
    )


@router.delete("/{theme_id}")
async def delete_theme(
    db: DbSession,
    theme_id: UUID,
    user_id: str = Depends(current_user),
) -> dict:
    """Delete a theme and its matches. Only the owner can delete."""
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    if theme.user_id and theme.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own themes")

    await db.execute(delete(ThemeMatch).where(ThemeMatch.theme_id == theme_id))
    await db.delete(theme)
    await db.commit()

    return {"deleted": True}


# -- Sprint Boris: themes the user is subscribed to via onboarding --


@router.get("/following", response_model=list[ThemeResponse])
async def list_followed_themes(
    db: DbSession,
    user_id: str = Depends(current_user),
) -> list[ThemeResponse]:
    from app.core.subscription_models import TopicSubscription

    sub_result = await db.execute(
        select(TopicSubscription.theme_id).where(
            TopicSubscription.user_id == user_id,
        )
    )
    subscribed_ids = [row[0] for row in sub_result.fetchall()]
    if not subscribed_ids:
        return []

    result = await db.execute(
        select(Theme).where(Theme.id.in_(subscribed_ids)).order_by(Theme.name)
    )
    themes = result.scalars().all()

    count_query = (
        select(ThemeMatch.theme_id, func.count(ThemeMatch.id).label("cnt"))
        .where(ThemeMatch.theme_id.in_(subscribed_ids))
        .group_by(ThemeMatch.theme_id)
    )
    count_result = await db.execute(count_query)
    count_map = {row.theme_id: row.cnt for row in count_result}

    return [
        ThemeResponse(
            id=str(t.id), name=t.name, description=t.description,
            cpc_prefixes=t.cpc_prefixes or [],
            assignee_keywords=t.assignee_keywords or [],
            title_keywords=t.title_keywords or [],
            keywords=t.keywords, opportunity_tags=t.opportunity_tags,
            min_opportunity_score=t.min_opportunity_score,
            user_id=t.user_id, is_active=t.is_active,
            patent_count=count_map.get(t.id, 0),
            created_at=t.created_at.isoformat(),
        )
        for t in themes
    ]


@router.get("/{theme_id}/patents", response_model=PaginatedResponse[PatentListItem])
async def get_theme_patents(
    db: DbSession,
    theme_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0.0, ge=0, le=1),
) -> PaginatedResponse[PatentListItem]:
    """Get patents matching a theme."""
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    base_query = (
        select(PatentPublication, ThemeMatch.match_score)
        .join(ThemeMatch, ThemeMatch.patent_id == PatentPublication.id)
        .where(ThemeMatch.theme_id == theme_id)
        .where(ThemeMatch.match_score >= min_score)
    )

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(ThemeMatch.match_score.desc()).offset(offset).limit(page_size)
    )
    rows = result.all()

    items = [PatentListItem.from_patent(row[0]) for row in rows]
    pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{theme_id}/stats", response_model=ThemeStats)
async def get_theme_stats(db: DbSession, theme_id: UUID) -> ThemeStats:
    """Get statistics for a theme."""
    result = await db.execute(select(Theme).where(Theme.id == theme_id))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    total_result = await db.execute(
        select(func.count(ThemeMatch.id)).where(ThemeMatch.theme_id == theme_id)
    )
    total_matches = total_result.scalar() or 0

    avg_result = await db.execute(
        select(func.avg(ThemeMatch.match_score)).where(ThemeMatch.theme_id == theme_id)
    )
    avg_score = avg_result.scalar() or 0.0

    return ThemeStats(
        theme_id=str(theme.id),
        name=theme.name,
        total_matches=total_matches,
        recent_matches=0,
        avg_score=round(float(avg_score), 4),
        top_assignees=[],
    )
