"""
Weekly briefing email renderer.

Renders the user's briefing feed as an editorial email using the
same items as /api/v1/today/briefing. HTML + text fallback.

Phase 5 PR 1: A/B subject line variants picked deterministically by
user_id mod 4. Each variant fills different placeholders from the
briefing items.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.email.sender import _render

logger = logging.getLogger(__name__)


def _utc_date_slug() -> str:
    """Return today's date as 'YYYY-MM-DD' for UTM campaign params."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── A/B subject line variants ──────────────────────────────────────

SUBJECT_VARIANTS = {
    "A": "{top_signal_count} signals — your weekly patent briefing",
    "B": "{hero_company_name} is filing again — your weekly briefing",
    "C": "{top_theme_name} momentum + expiring opportunities",
    "D": "This week's most interesting patent: {top_patent_title}",
}


def pick_variant(user_id: str) -> str:
    """Deterministically pick a subject variant by user.id hash mod 4."""
    # Use a simple hash of the user_id to avoid clustering on UUIDs
    # that might have a common prefix.
    h = 0
    for ch in user_id:
        h = (h * 31 + ord(ch)) & 0x7FFFFFFF
    variants = sorted(SUBJECT_VARIANTS.keys())
    return variants[h % len(variants)]


def build_subject(
    variant: str,
    items: list[dict],
    topic_count: int = 0,
    company_count: int = 0,
) -> str:
    """Build the subject line for a given variant using briefing items.

    Placeholders:
      {top_signal_count}  — total items count
      {hero_company_name} — first company move or first assignee
      {top_theme_name}    — first topic name from items
      {top_patent_title}  — first item title (truncated to 80 chars)
    """
    template = SUBJECT_VARIANTS.get(variant, SUBJECT_VARIANTS["A"])

    # Compute placeholders
    signal_count = max(len(items), topic_count)
    top_patent_title = ""
    hero_company_name = ""
    top_theme_name = ""

    if items:
        top_patent_title = (items[0].get("title") or "")[:80]
        if not top_patent_title:
            top_patent_title = "a new patent"

        # Find a company-move type item
        for item in items:
            if item.get("type") == "company" and item.get("source"):
                hero_company_name = item["source"][:40]
                break
        if not hero_company_name:
            hero_company_name = (items[0].get("source") or "industry")[:40]

        # Find the first topic name
        for item in items:
            tn = item.get("topic_name")
            if tn:
                top_theme_name = tn[:40]
                break
        if not top_theme_name:
            top_theme_name = "Patent"

    subject = template.format(
        top_signal_count=signal_count,
        hero_company_name=hero_company_name or "companies",
        top_theme_name=top_theme_name or "Patent",
        top_patent_title=top_patent_title or "a new patent",
    )
    return subject


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
        {subject, subject_variant, html, text}
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

    # Pick subject variant
    variant = pick_variant(user_id)

    # Build subject line
    subject = build_subject(variant, items, topic_count, company_count)

    kwargs = {
        "hero_stat": hero_stat,
        "items": email_items,
        "unsubscribe_url": f"{settings.magic_link_base_url}/unsubscribe/{unsubscribe_token}",
        "base_url": settings.magic_link_base_url,
        "date_slug": _utc_date_slug(),
    }

    html = _render("weekly_briefing.html", **kwargs)
    text = _render("weekly_briefing.txt", **kwargs)

    return {
        "subject": subject,
        "subject_variant": variant,
        "html": html,
        "text": text,
    }
