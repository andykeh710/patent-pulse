"""
RSS news ingestion + news-patent linking task.

Runs every 15 minutes. Fetches from curated RSS feed list,
embeds headlines, links to similar patents via pgvector.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from xml.etree import ElementTree

import httpx

from app.core.models import NewsItem, NewsPatentLink
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Reuters Technology", "https://feeds.reuters.com/reuters/technologyNews"),
    ("WIPO News", "https://www.wipo.int/pressroom/en/rss.xml"),
    ("EPO News", "https://www.epo.org/en/news-feed.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Wired", "https://www.wired.com/feed/rss"),
]

MIN_SIMILARITY = 0.55


@celery_app.task(
    bind=True,
    name="app.tasks.news.ingest_news",
    max_retries=1,
)
def ingest_news(self) -> dict:
    """Fetch RSS feeds, embed headlines, link to similar patents."""
    logger.info("Starting news ingestion")
    stats = asyncio.run(_ingest_news_async())
    logger.info("News ingestion complete: %s", stats)
    return stats


async def _ingest_news_async() -> dict:
    stats = {"feeds_checked": 0, "items_added": 0, "items_skipped": 0, "links_created": 0}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for source, url in RSS_FEEDS:
            stats["feeds_checked"] += 1
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    logger.warning("RSS feed %s returned %d", source, resp.status_code)
                    continue

                root = ElementTree.fromstring(resp.text)
                items = root.findall(".//item") or root.findall(
                    ".//{http://www.w3.org/2005/Atom}entry"
                )

                for item in items[:10]:  # max 10 per feed
                    headline = _text(item, "title")
                    link = _text(item, "link")
                    snippet = _text(item, "description") or _text(item, "summary")

                    if not headline:
                        continue

                    # Check for duplicates by URL
                    async with async_session_maker() as session:
                        from sqlalchemy import select

                        existing = (
                            await session.execute(
                                select(NewsItem).where(NewsItem.source_url == link)
                            )
                        ).scalar_one_or_none()

                        if existing:
                            stats["items_skipped"] += 1
                            continue

                        # Create news item
                        pub_date = _parse_date(item)
                        news = NewsItem(
                            headline=headline[:500],
                            source=source,
                            source_url=link,
                            snippet=snippet[:2000] if snippet else None,
                            published_at=pub_date,
                        )
                        session.add(news)
                        await session.commit()
                        await session.refresh(news)
                        stats["items_added"] += 1

                        # Embed and link to patents
                        try:
                            await _link_to_patents(session, news)
                            stats["links_created"] += 1
                        except Exception:
                            logger.debug("Failed to link news %s to patents", news.id)

            except Exception:
                logger.exception("Failed to process feed %s", source)

    return stats


async def _link_to_patents(session, news: NewsItem) -> None:
    """Embed news headline and find similar patents."""
    from app.ai.embedder import PatentEmbedder

    embedder = PatentEmbedder()
    emb = embedder.generate_embedding(news.headline)
    if not emb:
        return

    news.embedding = emb
    await session.commit()

    # Find similar patents
    emb_str = f"[{','.join(str(x) for x in emb)}]"
    from sqlalchemy import text

    rows = await session.execute(
        text("""
            SELECT id, 1 - (embedding <=> :emb::vector) as similarity
            FROM patent_publications
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> :emb::vector) >= :min_sim
            ORDER BY similarity DESC
            LIMIT 5
        """),
        {"emb": emb_str, "min_sim": MIN_SIMILARITY},
    )

    for row in rows.all():
        session.add(
            NewsPatentLink(
                news_id=news.id,
                patent_id=row[0],
                similarity=round(float(row[1]), 4),
            )
        )


def _text(element, tag: str) -> str:
    """Get text from RSS item, handling namespaces."""
    child = element.find(tag)
    if child is None:
        # Try with RSS namespace
        child = element.find(f"{{*}}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _parse_date(element) -> datetime | None:
    """Parse date from RSS item."""
    raw = _text(element, "pubDate") or _text(element, "published") or _text(element, "updated")
    if not raw:
        return None
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"]:
        try:
            from datetime import datetime as dt

            return dt.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


# ── User embedding recompute task ───────────────────────────────


@celery_app.task(
    bind=True,
    name="app.tasks.recommendations.recompute_user_embeddings",
    max_retries=1,
)
def recompute_user_embeddings(self) -> dict:
    """Recompute embeddings for all users with recent view activity."""
    logger.info("Recomputing user embeddings")
    stats = asyncio.run(_recompute_async())
    logger.info("User embeddings done: %s", stats)
    return stats


async def _recompute_async() -> dict:
    from sqlalchemy import func, select

    from app.core.models import UserViewEvent
    from app.services.recommendations import compute_user_embedding

    stats = {"users_checked": 0, "users_updated": 0, "users_skipped": 0}

    async with async_session_maker() as session:
        # Get distinct user_ids with recent events
        rows = await session.execute(
            select(UserViewEvent.user_id, func.count(UserViewEvent.id))
            .group_by(UserViewEvent.user_id)
            .having(func.count(UserViewEvent.id) >= 5)
        )
        users = rows.all()

        for user_id, count in users:
            stats["users_checked"] += 1
            try:
                updated = await compute_user_embedding(user_id, session)
                if updated:
                    stats["users_updated"] += 1
                else:
                    stats["users_skipped"] += 1
            except Exception:
                logger.exception("Failed to compute embedding for %s", user_id)

    return stats
