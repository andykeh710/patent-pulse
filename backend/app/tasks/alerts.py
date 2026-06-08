"""
Phase 5 PR 2 — Alert detection and delivery.

Hourly scan for 4 alert types:
  1. assignee_filed: Followed company filed new patent matching user's themes
  2. patent_expiring: Patent in watched theme/company expiring within 90 days
  3. trend_spike: CPC area in watched theme >2x filing increase vs prior month
  4. high_opportunity: New patent with opportunity_score > 80

Delivery: webhook (HMAC-signed) for Lifetime+, email fallback otherwise.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.core.ai_models import User, UserCompanyFollow
from app.core.alert_models import Alert, UserWebhookConfig
from app.core.models import PatentPublication
from app.core.subscription_models import TopicSubscription
from app.core.theme_models import Theme, ThemeMatch
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

PENDING_STATUS = "pending"
SENT_STATUS = "sent"
FAILED_STATUS = "failed"
MAX_RETRIES = 3
EXPIRY_WINDOW_DAYS = 90
SPIKE_THRESHOLD = 2.0
HIGH_OPPORTUNITY_THRESHOLD = 80


# ═══════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════


@celery_app.task(
    bind=True,
    name="app.tasks.alerts.scan_for_alerts",
    max_retries=1,
)
def scan_for_alerts(self) -> dict:
    """Hourly beat task: scan for new alerts across all users."""
    import asyncio

    from app.database import engine as _engine

    async def _run():
        try:
            return await _scan_async()
        finally:
            await _engine.dispose()

    try:
        stats = asyncio.run(_run())
    except Exception as e:
        logger.error("Alert scan failed: %s", e)
        stats = {"status": "failed", "error": str(e)}
    return stats


async def _scan_async() -> dict:
    async with async_session_maker() as session:
        return await _scan_with_session(session)


async def _scan_with_session(session) -> dict:
    stats = {"assignee_filed": 0, "patent_expiring": 0, "trend_spike": 0, "high_opportunity": 0}

    # Get all users with active subscriptions or followed companies
    subs_result = await session.execute(
        select(TopicSubscription).where(
            TopicSubscription.paused == False,  # noqa: E712
        )
    )
    subs = subs_result.scalars().all()

    # Group by user
    user_subs: dict[str, list[TopicSubscription]] = {}
    for sub in subs:
        user_subs.setdefault(sub.user_id, []).append(sub)

    now_utc = datetime.now(timezone.utc)
    since = now_utc - timedelta(hours=24)

    for user_id, sub_list in user_subs.items():
        user = (await session.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()
        if not user:
            continue

        # Collected themes + CPC prefixes
        theme_ids = [s.theme_id for s in sub_list]
        themes_result = await session.execute(
            select(Theme).where(Theme.id.in_(theme_ids))
        )
        themes = list(themes_result.scalars().all())

        all_cpc_prefixes: list[str] = []
        for t in themes:
            for prefix in (t.cpc_prefixes or []):
                # Match any CPC starting with the prefix
                all_cpc_prefixes.append(prefix)

        # Followed companies
        follows_result = await session.execute(
            select(UserCompanyFollow).where(UserCompanyFollow.user_id == user_id)
        )
        followed_companies = [
            f.company_normalized_name for f in follows_result.scalars().all()
        ]

        # ── 1. assignee_filed ──
        if followed_companies:
            new_patents = await _find_new_assignee_patents(
                session, followed_companies, all_cpc_prefixes, since
            )
            for patent in new_patents:
                await _create_alert(
                    session,
                    user_id=user_id,
                    alert_type="assignee_filed",
                    payload={
                        "patent_id": patent.doc_id,
                        "title": patent.title or patent.doc_id,
                        "assignee": _match_assignee(patent.assignees or [], followed_companies),
                        "themes": [t.name for t in themes],
                        "url": f"{settings.magic_link_base_url}/patents/{patent.id}",
                    },
                )
                stats["assignee_filed"] += 1

        # ── 2. patent_expiring ──
        if all_cpc_prefixes or followed_companies:
            expiring = await _find_expiring_patents(
                session, all_cpc_prefixes, followed_companies, now_utc
            )
            for patent in expiring:
                await _create_alert(
                    session,
                    user_id=user_id,
                    alert_type="patent_expiring",
                    payload={
                        "patent_id": patent.doc_id,
                        "title": patent.title or patent.doc_id,
                        "expiry_date": str(patent.estimated_expiry_date) if patent.estimated_expiry_date else "unknown",
                        "assignee": (patent.assignees or ["unknown"])[0],
                        "url": f"{settings.magic_link_base_url}/patents/{patent.id}",
                    },
                )
                stats["patent_expiring"] += 1

        # ── 3. trend_spike ──
        if all_cpc_prefixes:
            spikes = await _find_trend_spikes(session, all_cpc_prefixes, since)
            for spike in spikes:
                await _create_alert(
                    session,
                    user_id=user_id,
                    alert_type="trend_spike",
                    payload={
                        "cpc_area": spike["cpc"],
                        "new_filings": spike["new_count"],
                        "baseline_count": spike["baseline_count"],
                        "ratio": round(spike["ratio"], 2),
                        "theme": [t.name for t in themes][0] if themes else "",
                    },
                )
                stats["trend_spike"] += 1

        # ── 4. high_opportunity ──
        if all_cpc_prefixes:
            high_opp = await _find_high_opportunity_patents(
                session, all_cpc_prefixes, since
            )
            for patent in high_opp:
                await _create_alert(
                    session,
                    user_id=user_id,
                    alert_type="high_opportunity",
                    payload={
                        "patent_id": patent.doc_id,
                        "title": patent.title or patent.doc_id,
                        "assignee": (patent.assignees or ["unknown"])[0],
                        "url": f"{settings.magic_link_base_url}/patents/{patent.id}",
                    },
                )
                stats["high_opportunity"] += 1

    await session.commit()
    logger.info("Alert scan complete: %s", stats)
    return stats


async def _create_alert(session, *, user_id: str, alert_type: str, payload: dict) -> Alert:
    """Create an alert row. De-duplicates by (user_id, type, payload doc_id)."""
    # Simple dedup: check if same user+type+patent_id exists in last 24h
    patent_id = payload.get("patent_id")
    if patent_id:
        existing = (await session.execute(
            select(Alert).where(
                Alert.user_id == user_id,
                Alert.type == alert_type,
                Alert.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                Alert.payload["patent_id"].astext == patent_id,
            )
        )).scalar_one_or_none()
        if existing:
            return existing

    alert = Alert(
        user_id=user_id,
        type=alert_type,
        payload=payload,
        status=PENDING_STATUS,
    )
    session.add(alert)
    return alert


# ── Detection helpers ──────────────────────────────────────────────


async def _find_new_assignee_patents(
    session, followed_companies: list[str], cpc_prefixes: list[str], since: datetime
) -> list[PatentPublication]:
    """Find patents filed by followed companies matching CPC areas."""
    if not followed_companies or not cpc_prefixes:
        return []

    # Match assignee by normalized name pattern
    patterns = []
    for company in followed_companies:
        patterns.append(company[:30])

    result = await session.execute(
        select(PatentPublication).where(
            PatentPublication.publication_date >= since.date(),
        ).limit(50)
    )
    patents = result.scalars().all()

    # Filter in Python (JSONB array matching is complex in raw SQL)
    matches = []
    for p in patents:
        assignees_lower = [a.lower().strip() for a in (p.assignees or [])]
        for company in followed_companies:
            if company.lower() in " ".join(assignees_lower):
                # Check CPC match
                for cpc in (p.cpc or []):
                    for prefix in cpc_prefixes:
                        if cpc.startswith(prefix):
                            matches.append(p)
                            break
                    else:
                        continue
                    break
                break
    return matches[:20]  # max 20 per user per scan


async def _find_expiring_patents(
    session, cpc_prefixes: list[str], followed_companies: list[str], now: datetime
) -> list[PatentPublication]:
    """Patents expiring within EXPIRY_WINDOW_DAYS in watched areas."""
    cutoff = (now + timedelta(days=EXPIRY_WINDOW_DAYS)).date()

    # Build query
    query = select(PatentPublication).where(
        PatentPublication.estimated_expiry_date.isnot(None),
        PatentPublication.estimated_expiry_date <= cutoff,
        PatentPublication.estimated_expiry_date >= now.date(),
    ).limit(50)

    result = await session.execute(query)
    patents = result.scalars().all()

    matches = []
    for p in patents:
        for cpc in (p.cpc or []):
            for prefix in cpc_prefixes:
                if cpc.startswith(prefix):
                    matches.append(p)
                    break
            else:
                continue
            break
    return matches[:10]


async def _find_trend_spikes(
    session, cpc_prefixes: list[str], since: datetime
) -> list[dict]:
    """Find CPC areas with >2x filing increase in last 24h vs prior month daily avg."""
    # Compute new filings in last 24h per CPC section
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    month_ago = now - timedelta(days=30)

    spikes = []
    for prefix in cpc_prefixes[:10]:  # Limit prefixes
        # New filings (last 24h)
        new_count_result = await session.execute(
            select(PatentPublication).where(
                PatentPublication.publication_date >= day_ago.date(),
                PatentPublication.cpc.any().startswith(prefix),
            )
        )
        new_count = len(new_count_result.scalars().all())

        # Baseline: daily avg over prior month
        baseline_result = await session.execute(
            select(PatentPublication).where(
                PatentPublication.publication_date >= month_ago.date(),
                PatentPublication.publication_date < day_ago.date(),
                PatentPublication.cpc.any().startswith(prefix),
            )
        )
        baseline_total = len(baseline_result.scalars().all())
        baseline_avg = baseline_total / 29 if baseline_total > 0 else 0.5

        if baseline_avg > 0 and new_count / baseline_avg >= SPIKE_THRESHOLD and new_count >= 3:
            spikes.append({
                "cpc": prefix,
                "new_count": new_count,
                "baseline_count": round(baseline_avg, 1),
                "ratio": round(new_count / baseline_avg, 2),
            })

    return spikes[:5]


async def _find_high_opportunity_patents(
    session, cpc_prefixes: list[str], since: datetime
) -> list[PatentPublication]:
    """New patents with opportunity_score > 80 in watched CPC areas."""
    result = await session.execute(
        select(PatentPublication).where(
            PatentPublication.publication_date >= since.date(),
        ).limit(100)
    )
    patents = result.scalars().all()

    # Check opportunity_score from summary JSON
    matches = []
    for p in patents:
        summary = p.summary or {}
        opp_score = summary.get("opportunity_score", 0)
        if isinstance(opp_score, (int, float)) and opp_score > HIGH_OPPORTUNITY_THRESHOLD:
            for cpc in (p.cpc or []):
                for prefix in cpc_prefixes:
                    if cpc.startswith(prefix):
                        matches.append(p)
                        break
                else:
                    continue
                break
    return matches[:10]


def _match_assignee(assignees: list[str], followed: list[str]) -> str:
    for a in assignees:
        a_lower = a.lower().strip()
        for f in followed:
            if f in a_lower or a_lower in f:
                return a
    return assignees[0] if assignees else "unknown"


# ═══════════════════════════════════════════════════════════════════════
# Delivery
# ═══════════════════════════════════════════════════════════════════════


@celery_app.task(
    bind=True,
    name="app.tasks.alerts.deliver_pending_alerts",
    max_retries=1,
)
def deliver_pending_alerts(self) -> dict:
    """Hourly beat task: deliver all pending alerts."""
    import asyncio

    from app.database import engine as _engine

    async def _run():
        try:
            return await _deliver_async()
        finally:
            await _engine.dispose()

    try:
        stats = asyncio.run(_run())
    except Exception as e:
        logger.error("Alert delivery failed: %s", e)
        stats = {"status": "failed", "error": str(e)}
    return stats


async def _deliver_async() -> dict:
    async with async_session_maker() as session:
        return await _deliver_with_session(session)


async def _deliver_with_session(session) -> dict:
    stats = {"sent_webhook": 0, "sent_email": 0, "failed": 0, "skipped": 0}

    # Get all pending alerts (not yet sent, under max retries)
    pending = (await session.execute(
        select(Alert).where(
            Alert.status == PENDING_STATUS,
            Alert.retry_count < MAX_RETRIES,
        ).limit(200)
    )).scalars().all()

    for alert in pending:
        user = (await session.execute(
            select(User).where(User.id == alert.user_id)
        )).scalar_one_or_none()
        if not user:
            alert.status = FAILED_STATUS
            stats["failed"] += 1
            continue

        # Check if user has webhook config (Lifetime+ only)
        webhook_result = await session.execute(
            select(UserWebhookConfig).where(
                UserWebhookConfig.user_id == alert.user_id,
                UserWebhookConfig.enabled == True,  # noqa: E712
                UserWebhookConfig.webhook_url.isnot(None),
            )
        )
        webhook_config = webhook_result.scalar_one_or_none()

        if webhook_config and user.tier in ("lifetime", "enterprise"):
            # ── Webhook delivery ──
            success = await _deliver_via_webhook(alert, webhook_config)
            if success:
                alert.status = SENT_STATUS
                alert.sent_at = datetime.now(timezone.utc)
                alert.delivery_method = "webhook"
                webhook_config.last_success_at = alert.sent_at
                stats["sent_webhook"] += 1
            else:
                alert.retry_count += 1
                alert.status = FAILED_STATUS if alert.retry_count >= MAX_RETRIES else PENDING_STATUS
                webhook_config.last_failure_at = datetime.now(timezone.utc)
                stats["failed"] += 1
        else:
            # ── Email fallback ──
            success = await _deliver_via_email(alert, user)
            if success:
                alert.status = SENT_STATUS
                alert.sent_at = datetime.now(timezone.utc)
                alert.delivery_method = "email"
                stats["sent_email"] += 1
            else:
                alert.retry_count += 1
                alert.status = FAILED_STATUS if alert.retry_count >= MAX_RETRIES else PENDING_STATUS
                stats["failed"] += 1

    await session.commit()
    logger.info("Alert delivery complete: %s", stats)
    return stats


async def _deliver_via_webhook(alert: Alert, config: UserWebhookConfig) -> bool:
    """POST alert to webhook URL with HMAC signature. Returns True on 2xx."""
    body = {
        "alert_id": str(alert.id),
        "type": alert.type,
        "user_id": alert.user_id,
        "data": alert.payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body_bytes = json.dumps(body).encode()

    signature = _compute_hmac(body_bytes, config.secret_key or "")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                config.webhook_url,
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-IIE-Signature": f"sha256={signature}",
                    "X-IIE-Event": f"alerts.{alert.type}",
                },
            )
            if 200 <= resp.status_code < 300:
                logger.info("Webhook delivered alert=%s to %s", alert.id, config.webhook_url)
                return True
            else:
                logger.warning(
                    "Webhook returned %d for alert=%s url=%s",
                    resp.status_code, alert.id, config.webhook_url,
                )
                return False
    except Exception as e:
        logger.error("Webhook delivery failed for alert=%s: %s", alert.id, e)
        return False


async def _deliver_via_email(alert: Alert, user: User) -> bool:
    """Send alert via email using existing infra. Returns True on success."""
    if not user.email:
        return False
    try:
        from app.email.sender import send_email
        result = await send_email(
            db_session=None,  # We'll handle session outside
            to=user.email,
            subject=f"[Invention Index 8] {_alert_subject(alert)}",
            template_name="alert_notification.html",
            template_kwargs={
                "alert_type": alert.type,
                "payload": alert.payload,
                "base_url": settings.magic_link_base_url,
            },
            user_id=alert.user_id,
            email_type=f"alert_{alert.type}",
        )
        return result.get("status") in ("sent", "dev", "dry_run")
    except Exception as e:
        logger.error("Email delivery failed for alert=%s: %s", alert.id, e)
        return False


def _alert_subject(alert: Alert) -> str:
    labels = {
        "assignee_filed": "New filing by a company you follow",
        "patent_expiring": "Patent expiring soon",
        "trend_spike": "Trend spike detected",
        "high_opportunity": "High-opportunity patent found",
    }
    return labels.get(alert.type, "Alert")


def _compute_hmac(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8") if secret else b"",
        payload,
        hashlib.sha256,
    ).hexdigest()
