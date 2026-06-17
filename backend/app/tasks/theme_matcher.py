"""
Theme Matching Tasks.

Matches patents to themes based on CPC prefixes, assignee keywords,
and title keywords.
"""

import asyncio
import logging
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, or_, text, bindparam
from sqlalchemy import Text as TextType
from sqlalchemy.dialects.postgresql import insert

from app.core.models import PatentPublication
from app.core.theme_models import Theme, ThemeMatch
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.send_instant_alert import send_instant_alert

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.theme_matcher.match_all_themes",
)
def match_all_themes(self, limit_per_theme: int = 500) -> dict:
    """
    Match patents to all active themes.

    Args:
        limit_per_theme: Maximum patents to match per theme

    Returns:
        Stats dict with matched/failed counts per theme
    """
    logger.info("Starting theme matching for all themes")

    stats = asyncio.run(_match_all_themes_async(limit_per_theme))

    logger.info(f"Theme matching complete: {stats}")
    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.theme_matcher.match_theme",
)
def match_theme(self, theme_id: str, limit: int = 500) -> dict:
    """
    Match patents to a specific theme.

    Args:
        theme_id: UUID of the theme
        limit: Maximum patents to process

    Returns:
        Stats dict with matched count
    """
    logger.info(f"Starting theme matching for theme {theme_id}")

    stats = asyncio.run(_match_theme_async(UUID(theme_id), limit))

    logger.info(f"Theme matching complete for {theme_id}: {stats}")
    return stats


async def _match_all_themes_async(limit_per_theme: int) -> dict:
    """Match patents to all active themes."""
    stats = {"themes_processed": 0, "total_matches": 0, "errors": 0}

    async with async_session_maker() as session:
        result = await session.execute(select(Theme).where(Theme.is_active))
        themes = result.scalars().all()

        for theme in themes:
            try:
                theme_stats = await _match_single_theme(session, theme, limit_per_theme)
                stats["total_matches"] += theme_stats["matched"]
                stats["themes_processed"] += 1
            except Exception as e:
                logger.error(f"Failed to match theme {theme.name}: {e}")
                stats["errors"] += 1

        await session.commit()

    return stats


async def _match_theme_async(theme_id: UUID, limit: int) -> dict:
    """Match patents to a specific theme."""
    async with async_session_maker() as session:
        result = await session.execute(select(Theme).where(Theme.id == theme_id))
        theme = result.scalar_one_or_none()

        if not theme:
            return {"error": "Theme not found"}

        stats = await _match_single_theme(session, theme, limit)
        await session.commit()

        return stats


async def _match_single_theme(session, theme: Theme, limit: int) -> dict:
    """Match patents to a single theme."""
    stats: dict = {"matched": 0, "updated": 0, "skipped": 0, "alerts_enqueued": 0}

    conditions = []

    if theme.cpc_prefixes:
        for prefix in theme.cpc_prefixes:
            # cpc is JSONB, not PostgreSQL ARRAY. Use jsonb_array_elements_text + LIKE.
            conditions.append(
                text(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements_text(patent_publications.cpc) AS elem WHERE elem LIKE :pat)"
                ).bindparams(bindparam("pat", value=f"{prefix}%"))
            )

    if theme.assignee_keywords:
        for keyword in theme.assignee_keywords:
            # assignees is JSONB, cast to text for ILIKE search
            conditions.append(
                func.cast(PatentPublication.assignees, TextType).ilike(
                    f"%{keyword}%"
                )
            )

    if theme.title_keywords:
        for keyword in theme.title_keywords:
            conditions.append(PatentPublication.title.ilike(f"%{keyword}%"))

    if theme.keywords:
        for keyword in theme.keywords:
            conditions.append(PatentPublication.title.ilike(f"%{keyword}%"))
            conditions.append(
                func.coalesce(PatentPublication.abstract, "").ilike(f"%{keyword}%")
            )

    if not conditions:
        return stats

    query = (
        select(PatentPublication)
        .where(or_(*conditions))
        .order_by(PatentPublication.publication_date.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    patents = result.scalars().all()

    for patent in patents:
        score, reasons = _calculate_match_score(patent, theme)

        if score > 0:
            stmt = (
                insert(ThemeMatch)
                .values(
                    theme_id=theme.id,
                    patent_id=patent.id,
                    match_score=score,
                    match_reasons=reasons,
                    matched_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["theme_id", "patent_id"],
                    set_={
                        "match_score": score,
                        "match_reasons": reasons,
                        "matched_at": datetime.utcnow(),
                    },
                )
            )
            await session.execute(stmt)
            stats["matched"] += 1

            # Sprint 6: enqueue instant alerts for this match.
            cnt = await _enqueue_match_alerts(session, theme.id, patent.id, patent.opportunity_score or 0)
            stats["alerts_enqueued"] += cnt
        else:
            stats["skipped"] += 1

    return stats


async def _enqueue_match_alerts(session, theme_id, patent_id, opportunity_score: float) -> int:
    """Enqueue instant alerts for matching subscriptions. Returns count."""
    from app.core.subscription_models import TopicSubscription

    subs_result = await session.execute(
        select(TopicSubscription).where(
            TopicSubscription.theme_id == theme_id,
            TopicSubscription.mode == "instant_alert",
            TopicSubscription.paused == False,  # noqa: E712
        )
    )
    subs = subs_result.scalars().all()

    enqueued = 0
    for sub in subs:
        # min_score filter.
        if sub.min_score is not None and opportunity_score < sub.min_score:
            continue

        send_instant_alert.delay(str(sub.id), str(patent_id), str(theme_id))
        enqueued += 1

    return enqueued


_WORD_PATTERN_CACHE: dict[str, re.Pattern] = {}


def _contains_word(haystack: str, keyword: str) -> bool:
    """Whole-word, case-insensitive containment check.

    Uses alphanumeric boundaries so short keywords like "AI" match the token
    "AI" but NOT a substring inside another word (e.g. "Hyundai", "said").
    Multi-word keywords ("machine learning") and hyphenated company names are
    handled correctly. This is what prevents the false-positive theme matches
    that the substring (`in`) check produced.
    """
    kw = keyword.strip().lower()
    if not kw:
        return False
    pattern = _WORD_PATTERN_CACHE.get(kw)
    if pattern is None:
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])")
        _WORD_PATTERN_CACHE[kw] = pattern
    return pattern.search(haystack.lower()) is not None


def _calculate_match_score(patent: PatentPublication, theme: Theme) -> tuple[float, list[str]]:
    """Calculate how well a patent matches a theme.

    Text keywords use whole-word matching (see `_contains_word`) so short or
    ambiguous keywords cannot substring-match unrelated words. CPC matching is
    a deliberate prefix match (e.g. "G06N" matches "G06N3/084").
    """
    score = 0.0
    reasons = []

    if theme.cpc_prefixes and patent.cpc:
        for prefix in theme.cpc_prefixes:
            for cpc in patent.cpc:
                if cpc.upper().startswith(prefix.upper()):
                    score += 0.4
                    reasons.append(f"CPC: {cpc}")
                    break

    if theme.assignee_keywords and patent.assignees:
        assignee_text = " ".join(patent.assignees)
        for keyword in theme.assignee_keywords:
            if _contains_word(assignee_text, keyword):
                score += 0.3
                reasons.append(f"Assignee: {keyword}")

    if theme.title_keywords and patent.title:
        for keyword in theme.title_keywords:
            if _contains_word(patent.title, keyword):
                score += 0.3
                reasons.append(f"Title: {keyword}")

    if theme.keywords and patent.title:
        abstract_text = patent.abstract or ""
        for keyword in theme.keywords:
            if _contains_word(patent.title, keyword):
                score += 0.3
                reasons.append(f"Keyword(title): {keyword}")
            elif _contains_word(abstract_text, keyword):
                score += 0.15
                reasons.append(f"Keyword(abstract): {keyword}")

    score = min(score, 1.0)
    return score, reasons
