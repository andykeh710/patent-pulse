"""
V3.2 — Personalized feed ranking engine.

Deterministic, explainable ranking. No ML. No unbounded multiplicative
boost stacking. Every feed item carries why-shown explanations and
evidence backed by database facts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import User as UserModel
from app.core.ai_models import UserCompanyFollow
from app.core.subscription_models import TopicSubscription

# ── Feed item schema (internal typed dict) ────────────────────────────

FEED_ITEM_FIELDS = [
    "id",
    "object_type",
    "object_id",
    "feed_type",
    "title",
    "summary",
    "why_this",
    "why_now",
    "why_for_user",
    "evidence",
    "confidence",
    "source_date",
    "related_patents",
    "related_companies",
    "related_topics",
    "primary_action",
    "secondary_action",
    "rank_score",
    "seen_state",
    "feedback_state",
    "created_at",
]


# ── Role / use_case boost map ─────────────────────────────────────────

# Mapping: (persona, use_case) → feed_types to boost by +0.5
ROLE_USE_CASE_BOOSTS: dict[tuple[str | None, str | None], dict[str, float]] = {
    ("founder", None): {
        "expiry_opportunity": 0.5,
        "high_opportunity_patent": 0.4,
        "recommended_action": 0.2,
    },
    ("founder", "startup_ideas"): {
        "expiry_opportunity": 0.6,
        "high_opportunity_patent": 0.5,
        "similar_topic_patent": 0.3,
        "recommended_action": 0.3,
    },
    ("vc", None): {
        "followed_company_signal": 0.6,
        "company_new_patents": 0.5,
        "high_opportunity_patent": 0.4,
    },
    ("vc", "investment_research"): {
        "followed_company_signal": 0.7,
        "company_new_patents": 0.6,
        "high_opportunity_patent": 0.5,
    },
    ("engineer", None): {
        "topic_new_patents": 0.4,
        "similar_topic_patent": 0.5,
    },
    ("engineer", "rd_monitoring"): {
        "topic_new_patents": 0.5,
        "similar_topic_patent": 0.6,
    },
    ("researcher", None): {
        "topic_new_patents": 0.5,
        "high_opportunity_patent": 0.3,
    },
    ("patent_legal", None): {
        "expiry_opportunity": 0.7,
    },
    ("patent_legal", "expiry_freedom"): {
        "expiry_opportunity": 0.8,
    },
}

# Default boosts for any persona/use_case
DEFAULT_BOOSTS: dict[str, float] = {
    "fresh_ingestion_summary": 0.5,
    "recommended_action": 0.2,
}


# ── Public API ────────────────────────────────────────────────────────


async def build_personalized_feed(
    db: AsyncSession,
    user_id: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """
    Build a personalized Today feed for a user.

    1. Collect user preference context
    2. Gather candidate signals from real data
    3. Rank with deterministic additive formula
    4. Attach why-shown explanations
    5. Exclude hidden items
    """
    ctx = await _build_user_context(db, user_id)
    candidates = await _gather_candidates(db, ctx)
    ranked = _rank_candidates(candidates, ctx)
    feed_items = ranked[:limit]
    _attach_explanations(feed_items, ctx)
    return feed_items


# ── User context ──────────────────────────────────────────────────────


async def _build_user_context(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Collect all user preferences, follows, and interactions."""
    user = await db.get(UserModel, user_id)
    if not user:
        raise ValueError("User not found")

    # Followed topic IDs
    topic_rows = await db.execute(
        select(TopicSubscription.theme_id).where(TopicSubscription.user_id == user_id)
    )
    followed_topic_ids = {row[0] for row in topic_rows.fetchall() if row[0]}

    # Followed company names
    company_rows = await db.execute(
        select(UserCompanyFollow.company_normalized_name).where(
            UserCompanyFollow.user_id == user_id
        )
    )
    followed_companies = {row[0] for row in company_rows.fetchall() if row[0]}

    # Saved patent IDs
    patent_rows = await db.execute(
        text("SELECT patent_id FROM watchlist_items WHERE user_id = :uid"),
        {"uid": user_id},
    )
    saved_patent_ids = {row[0] for row in patent_rows.fetchall() if row[0]}

    # Hidden item IDs (object_type:object_id pairs)
    hidden_rows = await db.execute(
        text("SELECT object_type, object_id FROM hidden_feed_items WHERE user_id = :uid"),
        {"uid": user_id},
    )
    hidden_items = {f"{row[0]}:{row[1]}" for row in hidden_rows.fetchall()}

    # Not-useful type counters
    not_useful_rows = await db.execute(
        text(
            """SELECT object_type, COUNT(*) FROM feed_interactions
               WHERE user_id = :uid AND interaction_type = 'marked_not_useful'
               GROUP BY object_type"""
        ),
        {"uid": user_id},
    )
    not_useful_counts = {row[0]: row[1] for row in not_useful_rows.fetchall()}

    return {
        "user": user,
        "followed_topic_ids": followed_topic_ids,
        "followed_companies": followed_companies,
        "saved_patent_ids": saved_patent_ids,
        "hidden_items": hidden_items,
        "not_useful_counts": not_useful_counts,
    }


# ── Candidate gathering ───────────────────────────────────────────────


async def _gather_candidates(db: AsyncSession, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect candidate feed items from real data sources."""
    now = datetime.now(timezone.utc)
    candidates: list[dict[str, Any]] = []

    # 1. Expiring opportunities (top 3 by opportunity_score, expiry <365 days)
    expiring = await db.execute(
        text("""
            SELECT id, title, assignees, publication_date,
                   opportunity_score, estimated_expiry_date, legal_status_confidence
            FROM patent_publications
            WHERE opportunity_score IS NOT NULL
              AND estimated_expiry_date IS NOT NULL
              AND estimated_expiry_date <= CURRENT_DATE + INTERVAL '365 days'
            ORDER BY opportunity_score DESC
            LIMIT 3
        """)
    )
    for row in expiring.fetchall():
        candidates.append(
            _make_item(
                feed_type="expiry_opportunity",
                object_type="patent",
                object_id=str(row[0]),
                title=row[1] or "Untitled patent",
                summary=f"Expiring patent from {_first_assignee(row[2])}",
                evidence={
                    "opportunity_score": row[4],
                    "estimated_expiry_date": str(row[5]) if row[5] else None,
                    "legal_status_confidence": row[6],
                },
                source_date=str(row[5]) if row[5] else None,
                created_at=now,
            )
        )

    # 2. High-opportunity patents (top 3 recent)
    high_opp = await db.execute(
        text("""
            SELECT id, title, assignees, publication_date, opportunity_score,
                   opportunity_breakdown
            FROM patent_publications
            WHERE opportunity_score IS NOT NULL
              AND publication_date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY opportunity_score DESC
            LIMIT 3
        """)
    )
    for row in high_opp.fetchall():
        candidates.append(
            _make_item(
                feed_type="high_opportunity_patent",
                object_type="patent",
                object_id=str(row[0]),
                title=row[1] or "Untitled patent",
                summary=f"High-opportunity patent from {_first_assignee(row[2])}",
                evidence={
                    "opportunity_score": row[4],
                    "publication_date": str(row[3]) if row[3] else None,
                },
                source_date=str(row[3]) if row[3] else None,
                created_at=now,
            )
        )

    # 3. Company signals (top 3 filing spikes in followed companies, or top overall)
    if ctx["followed_companies"]:
        company_list = "', '".join(
            c.replace("'", "''") for c in list(ctx["followed_companies"])[:20]
        )
        company_rows = await db.execute(
            text(f"""
                SELECT assignee, COUNT(*) as cnt
                FROM patent_publications,
                     LATERAL jsonb_array_elements_text(assignees) as assignee
                WHERE assignee IN ('{company_list}')
                  AND publication_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY assignee
                ORDER BY cnt DESC
                LIMIT 3
            """)
        )
    else:
        company_rows = await db.execute(
            text("""
                SELECT assignee, COUNT(*) as cnt
                FROM patent_publications,
                     LATERAL jsonb_array_elements_text(assignees) as assignee
                WHERE publication_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY assignee
                ORDER BY cnt DESC
                LIMIT 3
            """)
        )
    for row in company_rows.fetchall():
        candidates.append(
            _make_item(
                feed_type="followed_company_signal"
                if row[0] in ctx["followed_companies"]
                else "company_new_patents",
                object_type="company",
                object_id=row[0],
                title=f"{row[0]} filing activity",
                summary=f"{row[0]}: {row[1]} patents in last 30 days",
                evidence={"recent_filings": row[1]},
                related_companies=[row[0]],
                created_at=now,
            )
        )

    # 4. Topic signals (top patents from followed topics)
    if ctx["followed_topic_ids"]:
        topic_id_list = "', '".join(str(tid) for tid in ctx["followed_topic_ids"])
        topic_rows = await db.execute(
            text(f"""
                SELECT pp.id, pp.title, pp.assignees, pp.publication_date,
                       pp.opportunity_score, t.name as topic_name
                FROM patent_publications pp
                JOIN theme_matches tm ON tm.patent_id = pp.id
                JOIN themes t ON t.id = tm.theme_id
                WHERE tm.theme_id IN ('{topic_id_list}')
                ORDER BY pp.opportunity_score DESC NULLS LAST, pp.publication_date DESC
                LIMIT 5
            """)
        )
        for row in topic_rows.fetchall():
            candidates.append(
                _make_item(
                    feed_type="topic_new_patents",
                    object_type="patent",
                    object_id=str(row[0]),
                    title=row[1] or "Untitled patent",
                    summary=f"New patent in {row[5]}: {_first_assignee(row[2])}",
                    evidence={
                        "topic_name": row[5],
                        "publication_date": str(row[4]) if row[4] else None,
                        "opportunity_score": row[3],
                    },
                    related_topics=[row[5]],
                    source_date=str(row[4]) if row[4] else None,
                    created_at=now,
                )
            )

    # 5. Fresh ingestion summary
    ingestion_rows = await db.execute(
        text("""
            SELECT finished_at, grants_created + apps_created AS new_records
            FROM ingestion_runs
            WHERE status = 'success'
            ORDER BY finished_at DESC LIMIT 1
        """)
    )
    ing_row = ingestion_rows.first()
    if ing_row:
        candidates.append(
            _make_item(
                feed_type="fresh_ingestion_summary",
                object_type="ingestion",
                object_id="latest",
                title="Patent data freshness",
                summary=f"Ingestion ran {_relative_time(ing_row[1])}: {ing_row[1]} new records"
                if ing_row[1]
                else "Ingestion ran successfully (no new records)",
                evidence={"new_records": ing_row[1]},
                created_at=now,
            )
        )

    # 6. Recommended actions
    if not ctx["followed_topic_ids"]:
        candidates.append(
            _make_item(
                feed_type="recommended_action",
                object_type="action",
                object_id="follow_topics",
                title="Personalize your briefing",
                summary="Follow topics and companies to get tailored invention intelligence.",
                created_at=now,
            )
        )

    return candidates


# ── Ranking ────────────────────────────────────────────────────────────


def _rank_candidates(candidates: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Score and sort candidates deterministically."""
    user = ctx["user"]
    persona = user.persona
    use_case = getattr(user, "use_case", None)
    hidden = ctx["hidden_items"]
    not_useful = ctx["not_useful_counts"]

    for item in candidates:
        feed_type = item["feed_type"]
        score = 1.0  # base score

        # Followed topic boost
        if ctx["followed_topic_ids"] and item.get("related_topics"):
            if any(t in ctx["followed_topic_ids"] for t in item.get("related_topics", [])):
                score += 0.5

        # Followed company boost
        if ctx["followed_companies"] and item.get("related_companies"):
            if any(c in ctx["followed_companies"] for c in item.get("related_companies", [])):
                score += 0.5

        # Role/use case boost
        boosts = ROLE_USE_CASE_BOOSTS.get((persona, use_case), {})
        if not boosts:
            boosts = ROLE_USE_CASE_BOOSTS.get((persona, None), {})
        score += boosts.get(feed_type, 0.0)
        score += DEFAULT_BOOSTS.get(feed_type, 0.0)

        # Recency boost
        if item.get("source_date"):
            try:
                from datetime import date

                sd = item["source_date"]
                if isinstance(sd, str):
                    sd_date = date.fromisoformat(sd[:10])
                    days_old = (date.today() - sd_date).days
                    score += max(-0.5, -days_old * 0.02)
            except (ValueError, TypeError):
                pass

        # Opportunity score boost
        evidence = item.get("evidence", {})
        if evidence.get("opportunity_score"):
            score += min(0.5, evidence["opportunity_score"] / 200)

        # Expiry urgency boost
        expiry = evidence.get("estimated_expiry_date")
        if expiry:
            try:
                from datetime import date

                if isinstance(expiry, str):
                    exp_date = date.fromisoformat(expiry[:10])
                    days_to_expiry = (exp_date - date.today()).days
                    if days_to_expiry <= 90:
                        score += 0.5
                    elif days_to_expiry <= 365:
                        score += 0.2
            except (ValueError, TypeError):
                pass

        # Penalties
        hidden_key = f"{item['object_type']}:{item['object_id']}"
        if hidden_key in hidden:
            score -= 10.0  # strong penalty, effectively excluded

        nt_count = not_useful.get(feed_type, 0)
        if nt_count > 0:
            score -= min(0.5, nt_count * 0.1)

        # Cap final score
        item["rank_score"] = round(max(0.0, min(5.0, score)), 2)

    candidates.sort(key=lambda x: x["rank_score"], reverse=True)
    return candidates


# ── Why-shown ──────────────────────────────────────────────────────────


def _attach_explanations(items: list[dict[str, Any]], ctx: dict[str, Any]) -> None:
    """Attach why_this, why_now, and why_for_user to each feed item."""
    user = ctx["user"]
    persona = user.persona
    use_case = getattr(user, "use_case", None)

    for item in items:
        feed_type = item["feed_type"]
        reasons_this: list[str] = []
        reasons_now: list[str] = []
        reasons_user: list[str] = []

        # Why this
        evidence = item.get("evidence", {})
        if evidence.get("opportunity_score"):
            reasons_this.append(
                f"This patent has a high opportunity score ({evidence['opportunity_score']})."
            )
        if evidence.get("topic_name"):
            reasons_this.append(
                f"This patent is in the '{evidence['topic_name']}' technology area."
            )
        if item.get("related_companies"):
            reasons_this.append(f"Involves {', '.join(item['related_companies'][:2])}.")

        # Why now
        if feed_type == "expiry_opportunity" and evidence.get("estimated_expiry_date"):
            reasons_now.append("This patent is approaching its estimated expiry window.")
        if feed_type == "fresh_ingestion_summary":
            reasons_now.append("This reflects the latest patent data ingestion.")

        # Why for user
        if item.get("related_topics"):
            for t in item["related_topics"]:
                reasons_user.append(f"Shown because you follow {t}.")
        if item.get("related_companies"):
            for c in item["related_companies"]:
                if c in ctx.get("followed_companies", set()):
                    reasons_user.append(f"Shown because you follow {c}.")
        if persona:
            persona_label = persona.replace("_", " ").title()
            reasons_user.append(f"Your selected role: {persona_label}.")
        if use_case:
            uc_label = use_case.replace("_", " ").title()
            reasons_user.append(f"Your selected use case: {uc_label}.")
        if feed_type == "recommended_action":
            reasons_user.append("Shown to help you get started with personalization.")

        if not reasons_user:
            reasons_user.append("Shown as a general signal of interest.")

        item["why_this"] = reasons_this[0] if reasons_this else ""
        item["why_now"] = reasons_now[0] if reasons_now else ""
        item["why_for_user"] = reasons_user[0] if reasons_user else ""


# ── Helpers ────────────────────────────────────────────────────────────


def _make_item(**kwargs: Any) -> dict[str, Any]:
    """Create a feed item dict with defaults."""
    now = datetime.now(timezone.utc)
    item: dict[str, Any] = {
        "id": f"{kwargs.get('object_type', 'unknown')}:{kwargs.get('object_id', 'unknown')}",
        "object_type": "",
        "object_id": "",
        "feed_type": "",
        "title": "",
        "summary": "",
        "why_this": "",
        "why_now": "",
        "why_for_user": "",
        "evidence": {},
        "confidence": "medium",
        "source_date": None,
        "related_patents": [],
        "related_companies": [],
        "related_topics": [],
        "primary_action": None,
        "secondary_action": None,
        "rank_score": 0.0,
        "seen_state": "unseen",
        "feedback_state": "none",
        "created_at": now.isoformat(),
    }
    item.update({k: v for k, v in kwargs.items() if k in item})
    return item


def _first_assignee(assignees: Any) -> str:
    """Extract first assignee from JSONB array or string."""
    import json

    if not assignees:
        return "Unknown"
    if isinstance(assignees, list):
        return assignees[0] if assignees else "Unknown"
    if isinstance(assignees, str):
        try:
            parsed = json.loads(assignees)
            return parsed[0] if parsed else "Unknown"
        except json.JSONDecodeError:
            return assignees
    return "Unknown"


def _relative_time(dt: Any) -> str:
    """Human-readable relative time."""
    from datetime import datetime, timezone

    if not dt:
        return "unknown"
    now = datetime.now(timezone.utc)
    if hasattr(dt, "replace"):
        dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    diff = now - dt
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return "just now"
    if hours < 24:
        return f"{int(hours)}h ago"
    days = int(hours / 24)
    return f"{days}d ago"
