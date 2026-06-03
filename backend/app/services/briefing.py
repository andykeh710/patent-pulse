"""Briefing feed assembler — weighted relevance scoring over patent events."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import TrendSnapshot
from app.core.models import PatentPublication


async def assemble_briefing(
    db: AsyncSession,
    user_id: str | None = None,
    followed_companies: list[str] | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Build a ranked briefing feed. Returns items with required fields."""
    items: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=14)).replace(tzinfo=None)
    companies = [c.lower() for c in (followed_companies or [])]

    # 1. Top filing trends
    trend_rows = await db.execute(
        select(TrendSnapshot)
        .where(TrendSnapshot.created_at >= cutoff)
        .order_by(desc(TrendSnapshot.z_score))
        .limit(4)
    )
    for t in trend_rows.scalars().all():
        items.append({
            "type": "trend",
            "label": f"Filing trend · {getattr(t, 'trend_surface', 'cpc').upper()}",
            "title": f"{getattr(t, 'trend_label', 'Unknown')} — z-score {t.z_score:.1f}",
            "subtext": f"{getattr(t, 'count_4w', 0)} filings in 4 weeks",
            "reason": _trend_reason(t, companies),
            "source": "USPTO · EPO · WIPO",
            "freshness": {"updated_at": t.created_at.isoformat(), "relative": _relative(t.created_at)},
            "confidence": None,
            "href": f"/trends/{getattr(t, 'trend_surface', 'cpc')}/{getattr(t, 'trend_key', '')}",
        })

    # 2. Notable patents
    patent_rows = await db.execute(
        select(PatentPublication)
        .where(PatentPublication.opportunity_score.isnot(None))
        .where(PatentPublication.publication_date >= cutoff.date())
        .order_by(desc(PatentPublication.opportunity_score))
        .limit(4)
    )
    for p in patent_rows.scalars().all():
        assignee = (p.assignees or ["Unknown"])[0] if p.assignees else "Unknown"
        items.append({
            "type": "notable",
            "label": "Notable patent",
            "title": p.title or p.publication_number,
            "subtext": f"{assignee} · {p.publication_number}",
            "reason": _patent_reason(p, companies),
            "source": f"{p.office or 'USPTO'} direct",
            "freshness": {"updated_at": str(p.publication_date), "relative": _relative_date(p.publication_date)},
            "confidence": {"level": "medium", "caveat": "AI-generated summary — verify"} if p.summarized_at else None,
            "href": f"/patents/{p.id}",
        })

    # 3. Company moves
    if companies:
        for c in companies[:3]:
            items.append({
                "type": "company",
                "label": "Company move",
                "title": f"{c.title()} — recent activity in your follows",
                "reason": f"You follow {c.title()}",
                "source": "USPTO · WIPO",
                "freshness": {"updated_at": now.isoformat(), "relative": "just now"},
                "href": f"/companies/{c}",
            })

    # 4. Expiring opportunities
    items.append({
        "type": "expiring",
        "label": "Expiring opportunity",
        "title": "Expiring patent radar — check your topics",
        "reason": "Patent expiry creates whitespace opportunities",
        "source": "USPTO · computed expiry estimates",
        "freshness": {"updated_at": now.isoformat(), "relative": "updated daily"},
        "confidence": {"level": "low", "caveat": "Verify with official registers before relying on expiry status"},
        "href": "/expiry",
    })

    # 5. For You stub (honest — no fake AI)
    items.append({
        "type": "foryou",
        "label": "For You · early personalization",
        "title": "Personalized feed will grow as you follow topics and companies",
        "reason": "Based on your activity and follows",
        "source": "Invention Index 8",
        "freshness": {"updated_at": now.isoformat(), "relative": "just now"},
        "href": "/themes",
    })

    return items[:limit]


def _trend_reason(trend, companies: list[str]) -> str:
    top = (getattr(trend, 'top_assignees', None) or [])[:2]
    if top and any(c in a.lower() for a in top for c in companies):
        return f"Trending in your followed companies: {', '.join(top[:2])}"
    if top:
        return f"Strong filing momentum — led by {', '.join(top[:2])}"
    return "Filing trend detected in your topic area"


def _patent_reason(patent, companies: list[str]) -> str:
    assignee = (patent.assignees or ["Unknown"])[0] if patent.assignees else ""
    if assignee and any(c in assignee.lower() for c in companies):
        return f"New patent from a company you follow: {assignee}"
    score = patent.opportunity_score or 0
    if score >= 70:
        return f"High opportunity score ({score:.0f}) — worth attention"
    return "Notable based on opportunity signals"


def _relative(dt) -> str:
    if not dt:
        return "unknown"
    hours = (datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    if hours < 1:
        return "just now"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def _relative_date(d) -> str:
    if not d:
        return "unknown"
    days = (datetime.now(timezone.utc).date() - d).days
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days}d ago"
