"""
Weekly briefing email renderer.

Renders the user's briefing feed as an editorial email using the
same items as /api/v1/today/briefing. HTML + text fallback.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.email.sender import _render

logger = logging.getLogger(__name__)


def render_weekly_briefing(
    items: list[dict],
    user_email: str,
    user_id: str,
    unsubscribe_token: str,
    topic_count: int = 0,
    company_count: int = 0,
) -> dict[str, str]:
    """Render a weekly briefing email for a user.

    Args:
        items: Briefing items from briefing.assemble_briefing()
        user_email: Recipient email
        user_id: User ID
        unsubscribe_token: Signed JWT token for unsubscribe link
        topic_count: Number of topics the user follows
        company_count: Number of companies the user follows

    Returns:
        {subject, html, text}
    """
    # Build hero stat
    parts = []
    if topic_count:
        parts.append(f"{topic_count} topic{'s' if topic_count > 1 else ''}")
    if company_count:
        parts.append(f"{company_count} compan{'ies' if company_count > 1 else 'y'}")
    coverage = " and ".join(parts) if parts else "your interests"
    hero_stat = f"What's new this week in {coverage}"

    # Build email items from briefing items
    email_items = []
    type_labels = {
        "trend": "Filing trend",
        "notable": "Notable patent",
        "company": "Company move",
        "expiring": "Expiring opportunity",
        "foryou": "For you",
    }

    for item in items[:8]:
        confidence = item.get("confidence") or {}
        freshness = item.get("freshness", {})

        email_items.append({
            "type_label": type_labels.get(item.get("type", ""), item.get("label", "Update")),
            "title": item.get("title", "")[:120],
            "reason": item.get("reason", "")[:200],
            "source": item.get("source", ""),
            "freshness": freshness.get("relative", ""),
            "confidence_caveat": confidence.get("caveat", ""),
        })

    if not email_items:
        email_items.append({
            "type_label": "Update",
            "title": "No new patent activity in your topics this week",
            "reason": "We'll let you know when new patents match your interests.",
            "source": "Invention Index 8",
            "freshness": "just now",
            "confidence_caveat": "",
        })

    kwargs = {
        "hero_stat": hero_stat,
        "items": email_items,
        "unsubscribe_url": f"{settings.magic_link_base_url}/unsubscribe/{unsubscribe_token}",
        "base_url": settings.magic_link_base_url,
    }

    html = _render("weekly_briefing.html", **kwargs)
    text = _render("weekly_briefing.txt", **kwargs)
    subject = f"Invention Index 8 Weekly — {hero_stat}"

    return {"subject": subject, "html": html, "text": text}
