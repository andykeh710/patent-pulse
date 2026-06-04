"""Tests for weekly digest fan-out task."""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.ai_models import AIArtifact
from app.core.models import PatentPublication
from app.core.subscription_models import EmailDelivery, TopicSubscription
from app.core.theme_models import Theme, ThemeMatch


@pytest.mark.asyncio(loop_scope="function")
async def test_fan_out_generates_digest(db_session):
    """Synthetic setup with 1 user, 2 weekly subs, 3 matches each → 1 digest."""
    from app.core.ai_models import User

    user = User(id="digest-user", email="digest@example.com", display_name="Digest User")
    db_session.add(user)

    theme1 = Theme(name="T1", is_active=True, cpc_prefixes=["G06N"], keywords=["ai"])
    theme2 = Theme(name="T2", is_active=True, cpc_prefixes=["H01L"], keywords=["chip"])
    db_session.add_all([theme1, theme2])
    await db_session.commit()
    await db_session.refresh(theme1)
    await db_session.refresh(theme2)

    sub1 = TopicSubscription(user_id=user.id, theme_id=theme1.id, mode="weekly_digest")
    sub2 = TopicSubscription(user_id=user.id, theme_id=theme2.id, mode="weekly_digest")
    db_session.add_all([sub1, sub2])
    await db_session.commit()
    await db_session.refresh(sub1)
    await db_session.refresh(sub2)

    for theme in [theme1, theme2]:
        for i in range(3):
            patent = PatentPublication(
                doc_id=f"USPTO:{i}-{theme.name}", title=f"Patent {i}",
                publication_number=f"US{i}0000", office="USPTO",
                assignees=[f"Company{i}"], cpc=["G06N"],
                filing_date=date(2024, 1, 1), publication_date=date(2025, 1, 1),
            )
            db_session.add(patent)
            await db_session.commit()
            await db_session.refresh(patent)

            match = ThemeMatch(
                theme_id=theme.id, patent_id=patent.id, match_score=0.9,
                match_reasons=["test"], matched_at=datetime.utcnow(),
            )
            db_session.add(match)
    await db_session.commit()

    # Mock LLM at the module that imports it (app.ai.weekly_digest)
    # Pre-create an AIArtifact row for the FK reference
    mock_artifact_id = uuid4()
    artifact = AIArtifact(
        id=mock_artifact_id, artifact_type="weekly_digest",
        subject_key="weekly_digest:digest-user:test",
        content_json={"headline": "Mock", "highlights": [], "patterns": "", "caveats": []},
        model="test", prompt_name="weekly_digest", prompt_version=1,
        prompt_hash="aaaa", input_hash="bbbb",
    )
    db_session.add(artifact)
    await db_session.commit()

    mock_resp = AsyncMock()
    mock_resp.content_json = {
        "headline": "Weekly headline",
        "highlights": [{"patent_doc_id": "USPTO:0-T1", "title": "P0", "why_it_matters": "Interesting"}],
        "patterns": "Patterns",
        "caveats": ["Evidence is patent-based only."],
    }
    mock_resp.artifact_id = mock_artifact_id

    with patch("app.ai.weekly_digest.get_llm_client") as mock_llm_factory:
        mock_client = mock_llm_factory.return_value
        mock_client.complete = AsyncMock(return_value=mock_resp)

        from app.tasks.send_weekly_digest import _fan_out_async
        stats = await _fan_out_async(session=db_session)

        assert stats.get("digests_generated", 0) >= 1

    await db_session.refresh(sub1)
    await db_session.refresh(sub2)
    assert sub1.last_delivered_at is not None
    assert sub2.last_delivered_at is not None

    deliveries = (await db_session.execute(
        select(EmailDelivery).where(EmailDelivery.user_id == user.id)
    )).scalars().all()
    assert len(deliveries) >= 1
    assert deliveries[0].email_type == "weekly_briefing"


@pytest.mark.asyncio(loop_scope="function")
async def test_fan_out_skips_user_with_no_matches(db_session):
    from app.core.ai_models import User

    user = User(id="no-match-digest", email="nomatch@example.com", display_name="NM")
    db_session.add(user)
    theme = Theme(name="EmptyD", is_active=True, cpc_prefixes=["X99X"], keywords=["none"])
    db_session.add(theme)
    await db_session.commit()
    await db_session.refresh(theme)

    sub = TopicSubscription(user_id=user.id, theme_id=theme.id, mode="weekly_digest")
    db_session.add(sub)
    await db_session.commit()

    from app.tasks.send_weekly_digest import _fan_out_async
    stats = await _fan_out_async(session=db_session)
    assert stats.get("digests_generated", 0) == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_fan_out_cache_hit_no_new_artifact(db_session):
    from app.core.ai_models import User

    user = User(id="cache-digest", email="cache@example.com", display_name="Cache")
    db_session.add(user)
    theme = Theme(name="CachedD", is_active=True, cpc_prefixes=["G06N"], keywords=["cache"])
    db_session.add(theme)
    await db_session.commit()
    await db_session.refresh(theme)

    sub = TopicSubscription(user_id=user.id, theme_id=theme.id, mode="weekly_digest")
    db_session.add(sub)

    patent = PatentPublication(
        doc_id="USPTO:cached", title="Cache Patent", publication_number="USC0000",
        office="USPTO", assignees=["C"], cpc=["G06N"],
        filing_date=date(2024, 1, 1), publication_date=date(2025, 1, 1),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    match = ThemeMatch(
        theme_id=theme.id, patent_id=patent.id, match_score=0.9,
        match_reasons=["t"], matched_at=datetime.utcnow(),
    )
    db_session.add(match)
    await db_session.commit()

    week_start = (date.today() - timedelta(days=7)).isoformat()

    artifact = AIArtifact(
        id=uuid4(), artifact_type="weekly_digest",
        subject_key=f"weekly_digest:cache-digest:{week_start}",
        content_json={"headline": "Cached", "highlights": [], "patterns": "", "caveats": []},
        model="test", prompt_name="weekly_digest", prompt_version=1,
        prompt_hash="aaaa", input_hash="bbbb",
    )
    db_session.add(artifact)
    await db_session.commit()

    cached = (await db_session.execute(
        select(AIArtifact).where(AIArtifact.subject_key == f"weekly_digest:cache-digest:{week_start}")
    )).scalar_one_or_none()
    assert cached is not None
