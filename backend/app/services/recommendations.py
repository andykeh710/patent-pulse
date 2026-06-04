"""
Recommendation engine — embedding-based personalized patent recommendations.

Computes user embeddings from view/save/follow history, then finds
similar unviewed patents via pgvector cosine similarity.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication, UserViewEvent
from app.database import async_session_maker

logger = logging.getLogger(__name__)

MIN_EVENTS = 5
CACHE_TTL_SECONDS = 21600  # 6 hours


async def recommend_for_user(
    user_id: str,
    limit: int = 10,
    session: AsyncSession | None = None,
) -> list[dict]:
    """Return personalized patent recommendations for a user.

    Uses cosine similarity between the user's weighted embedding centroid
    and unviewed patent embeddings. Falls back to empty list if < 5 events.
    """
    _session = session or async_session_maker()

    try:
        if session is None:
            async with _session as s:
                return await _recommend(s, user_id, limit)
        return await _recommend(_session, user_id, limit)
    except Exception:
        logger.exception("Recommendation failed for user %s", user_id)
        return []


async def _recommend(session: AsyncSession, user_id: str, limit: int) -> list[dict]:
    # Check user embedding
    from app.core.models import UserEmbedding

    ue = (await session.execute(
        select(UserEmbedding).where(UserEmbedding.user_id == user_id)
    )).scalar_one_or_none()

    if not ue or ue.event_count < MIN_EVENTS:
        return []

    # Find unviewed patents
    viewed = (await session.execute(
        select(UserViewEvent.patent_id).where(UserViewEvent.user_id == user_id)
    )).scalars().all()
    viewed_ids = set(viewed)

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    emb_list = ue.embedding
    emb_str = f"[{','.join(str(x) for x in emb_list)}]"

    rows = await session.execute(
        text("""
            SELECT p.id, p.title, p.doc_id, p.assignees, p.publication_number,
                   1 - (p.embedding <=> :emb::vector) as similarity
            FROM patent_publications p
            WHERE p.embedding IS NOT NULL
              AND p.publication_date >= :cutoff
              AND 1 - (p.embedding <=> :emb::vector) >= 0.5
            ORDER BY similarity DESC
            LIMIT :limit
        """),
        {"emb": emb_str, "cutoff": cutoff, "limit": limit * 2},
    )

    results = []
    for row in rows.all():
        pid = row[0]  # UUID
        if pid in viewed_ids:
            continue
        assignee = (row[3] or ["Unknown"])[0] if row[3] else "Unknown"
        results.append({
            "patent_id": str(pid),
            "title": row[1] or row[4] or "Untitled",
            "assignee": assignee,
            "similarity": round(float(row[5]), 3),
        })
        if len(results) >= limit:
            break

    return results


async def compute_user_embedding(
    user_id: str,
    session: AsyncSession | None = None,
) -> bool:
    """Compute a user's embedding as weighted centroid of viewed patents.

    Returns True if embedding was updated, False if skipped (< 5 events).
    """
    _session = session or async_session_maker()
    try:
        if session is None:
            async with _session as s:
                return await _compute(s, user_id)
        return await _compute(_session, user_id)
    except Exception:
        logger.exception("User embedding computation failed for %s", user_id)
        return False


async def _compute(session: AsyncSession, user_id: str) -> bool:
    from app.core.models import UserEmbedding

    # Get user's weighted events
    events = (await session.execute(
        select(UserViewEvent).where(UserViewEvent.user_id == user_id)
        .order_by(UserViewEvent.created_at.desc()).limit(200)
    )).scalars().all()

    if len(events) < MIN_EVENTS:
        return False

    # Get embeddings for viewed patents
    patent_ids = list({e.patent_id for e in events})
    patents = (await session.execute(
        select(PatentPublication.id, PatentPublication.embedding)
        .where(PatentPublication.id.in_(patent_ids))
        .where(PatentPublication.embedding.isnot(None))
    )).all()

    patent_embeddings = {p[0]: p[1] for p in patents}

    # Weighted centroid
    total_weight = 0
    centroid = [0.0] * 1536

    for event in events:
        emb = patent_embeddings.get(event.patent_id)
        if emb:
            w = event.weight
            for i, val in enumerate(emb):
                centroid[i] += val * w
            total_weight += w

    if total_weight == 0:
        return False

    centroid = [v / total_weight for v in centroid]

    # Normalize
    norm = sum(v * v for v in centroid) ** 0.5
    if norm > 0:
        centroid = [v / norm for v in centroid]

    # Upsert
    ue = (await session.execute(
        select(UserEmbedding).where(UserEmbedding.user_id == user_id)
    )).scalar_one_or_none()

    if ue:
        ue.embedding = centroid
        ue.event_count = len(events)
        ue.updated_at = datetime.now(timezone.utc)
    else:
        session.add(UserEmbedding(
            user_id=user_id,
            embedding=centroid,
            event_count=len(events),
        ))

    await session.commit()
    logger.info("User embedding updated: %s (%d events)", user_id, len(events))
    return True


async def track_view(
    user_id: str,
    patent_id: str,
    event_type: str = "view",
    weight: int = 1,
) -> None:
    """Record a user view/save/follow event."""
    from uuid import UUID

    async with async_session_maker() as session:
        session.add(UserViewEvent(
            user_id=user_id,
            patent_id=UUID(patent_id),
            event_type=event_type,
            weight=weight,
        ))
        await session.commit()
