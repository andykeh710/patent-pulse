"""
Weekly digest fan-out task (Sprint 6).

Scheduled Sunday 7am. Generates and delivers Sonnet weekly briefings
to all weekly_digest subscribers. One AIArtifact per user-week.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ai_models import User
from app.core.subscription_models import TopicSubscription
from app.core.theme_models import Theme, ThemeMatch
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.send_weekly_digest.fan_out_weekly_digests",
)
def fan_out_weekly_digests(self) -> dict:
    logger.info("Starting weekly digest fan-out")

    from app.database import engine as _engine

    async def _run_and_dispose():
        try:
            return await _fan_out_async()
        finally:
            await _engine.dispose()

    try:
        stats = asyncio.run(_run_and_dispose())
    except Exception as e:
        logger.error("Weekly digest fan-out failed: %s", e)
        stats = {"status": "failed", "error": str(e)}

    return stats


async def _fan_out_async(*, session: AsyncSession | None = None) -> dict:
    """Fan out weekly digests. Uses provided session or creates one."""
    if session is not None:
        return await _fan_out_with_session(session)

    async with async_session_maker() as s:
        return await _fan_out_with_session(s)


async def _fan_out_with_session(session: AsyncSession) -> dict:
    stats = {"users_processed": 0, "digests_generated": 0, "deliveries_sent": 0, "errors": 0}

    week_end = date.today()
    week_start = week_end - timedelta(days=7)

    subs_result = await session.execute(
        select(TopicSubscription).where(
            TopicSubscription.mode == "weekly_digest",
            TopicSubscription.paused == False,  # noqa: E712
        )
    )
    subs = subs_result.scalars().all()
    if not subs:
        logger.info("No weekly digest subscribers found")
        return stats

    user_subs: dict[str, list[TopicSubscription]] = {}
    for sub in subs:
        user_subs.setdefault(sub.user_id, []).append(sub)

    for user_id, sub_list in user_subs.items():
        try:
            user = (await session.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()
            if not user or not user.email:
                continue

            topics_data = []
            matches_data = []
            has_any = False

            for sub in sub_list:
                theme = (await session.execute(
                    select(Theme).where(Theme.id == sub.theme_id)
                )).scalar_one_or_none()
                if not theme:
                    continue

                match_rows = (await session.execute(
                    select(ThemeMatch).where(
                        ThemeMatch.theme_id == sub.theme_id,
                        ThemeMatch.matched_at >= week_start,
                    ).order_by(ThemeMatch.match_score.desc()).limit(5)
                )).scalars().all()

                if not match_rows:
                    topics_data.append({
                        "name": theme.name, "match_count": 0,
                        "keywords": theme.keywords or [], "cpc_prefixes": theme.cpc_prefixes or [],
                    })
                    continue

                has_any = True
                topics_data.append({
                    "name": theme.name, "match_count": len(match_rows),
                    "keywords": theme.keywords or [], "cpc_prefixes": theme.cpc_prefixes or [],
                })

                for m in match_rows:
                    from app.core.models import PatentPublication
                    patent = (await session.execute(
                        select(PatentPublication).where(PatentPublication.id == m.patent_id)
                    )).scalar_one_or_none()
                    if patent:
                        matches_data.append({
                            "topic_name": theme.name,
                            "doc_id": patent.doc_id,
                            "title": patent.title or patent.doc_id,
                            "assignee": (patent.assignees or ["unknown"])[0],
                            "cpc": patent.cpc or [],
                        })

            if not has_any:
                continue

            from app.ai.weekly_digest import generate_weekly_digest
            try:
                narrative, artifact_id = await generate_weekly_digest(
                    session, user_id, week_start, week_end, topics_data, matches_data,
                )
            except Exception as e:
                logger.error("Digest generation failed for user %s: %s", user_id, e)
                stats["errors"] += 1
                continue

            stats["digests_generated"] += 1

            sections = []
            for h in narrative.get("highlights", [])[:5]:
                sections.append({"title": h.get("title", "")[:80], "body": h.get("why_it_matters", "")})

            unsubscribe_token = _sign_user_id(user_id)
            from app.email.sender import send_email
            result = await send_email(
                db_session=session,
                to=user.email,
                subject="Your Invention Index 8 Weekly Digest",
                template_name="weekly_digest.html",
                template_kwargs={
                    "greeting": f"Weekly Digest — {week_start} to {week_end}",
                    "intro_blurb": narrative.get("headline", "Here are your weekly patent matches."),
                    "sections": sections,
                    "call_to_action": "View your topics and manage subscriptions",
                    "cta_url": f"{settings.magic_link_base_url}/account",
                    "cta_text": "View Account",
                    "unsubscribe_url": f"{settings.magic_link_base_url}/api/v1/subscriptions/unsubscribe?subscription=USER&token={unsubscribe_token}",
                    "magic_link_base_url": settings.magic_link_base_url,
                },
                user_id=user_id, email_type="weekly_digest", artifact_id=artifact_id,
            )

            if result.get("status") in ("sent", "dev", "dry_run"):
                stats["deliveries_sent"] += 1
                for sub in sub_list:
                    sub.last_delivered_at = datetime.now(timezone.utc)

            stats["users_processed"] += 1

        except Exception as e:
            logger.error("Error processing user %s: %s", user_id, e)
            stats["errors"] += 1

    await session.commit()

    logger.info("Weekly digest fan-out complete: %s", stats)
    return stats


def _sign_user_id(user_id: str) -> str:
    import hashlib
    import hmac
    return hmac.new(
        settings.auth_secret_key.encode(),
        user_id.encode(),
        hashlib.sha256,
    ).hexdigest()
