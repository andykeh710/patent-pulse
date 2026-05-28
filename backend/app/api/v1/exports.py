"""Sprint 7 — CSV export endpoint (quota-gated)."""
from __future__ import annotations

import csv
import io
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.api.deps import current_user, get_db
from app.core.ai_models import ExpiryAssessment, PatentUsageSignals
from app.core.billing_models import Export
from app.core.models import PatentPublication

router = APIRouter()

CSV_COLUMNS = [
    "doc_id", "publication_number", "office", "title",
    "assignees", "estimated_expiry_date", "days_until_expiry",
    "expiry_status", "expiry_status_confidence",
    "expiry_opportunity_score", "active_family_risk",
    "maintenance_status", "usage_signal_score",
    "usage_signal_evidence_count", "usage_has_self_citation_risk",
    "legal_status", "legal_status_confidence",
]


@router.get("/expiry.csv")
async def export_expiry_csv(
    request: Request,
    user_id: str = Depends(current_user),
    db = Depends(get_db),
    expiry_status: str | None = Query(default=None),
    expiry_confidence: str | None = Query(default=None),
    active_family_risk: bool | None = Query(default=None),
    days_ahead: int | None = Query(default=None),
    office: str | None = Query(default=None),
):
    """Export filtered expiry list as CSV."""
    from sqlalchemy import and_, select

    # Quota check: inlined to avoid double Depends(current_user)
    from app.core.ai_models import User
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    tier = user.tier if user else "free"
    if tier not in ("basic", "lifetime", "enterprise"):
        raise HTTPException(
            status_code=402,
            detail="CSV exports require Basic tier or higher. Upgrade at /account/billing.",
        )

    # Build query with LEFT JOINs matching the expiry endpoint pattern.
    base = (
        select(PatentPublication, ExpiryAssessment, PatentUsageSignals)
        .outerjoin(ExpiryAssessment, PatentPublication.id == ExpiryAssessment.patent_publication_id)
        .outerjoin(PatentUsageSignals, PatentPublication.id == PatentUsageSignals.patent_publication_id)
    )

    conditions = []
    if expiry_status:
        conditions.append(ExpiryAssessment.expiry_status == expiry_status)
    if active_family_risk is not None:
        conditions.append(ExpiryAssessment.active_family_risk == active_family_risk)
    if office:
        conditions.append(PatentPublication.office == office.upper())

    if conditions:
        base = base.where(and_(*conditions))

    base = base.order_by(PatentPublication.opportunity_score.desc().nulls_last()).limit(5000)

    result = await db.execute(base)
    rows = result.all()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)

    for patent, expiry, signals in rows:
        writer.writerow([
            patent.doc_id or "",
            patent.publication_number or "",
            patent.office or "",
            patent.title or "",
            "; ".join(patent.assignees or []),
            str(expiry.estimated_expiry_date) if expiry and expiry.estimated_expiry_date else "",
            str(expiry.days_until_expiry) if expiry and expiry.days_until_expiry is not None else "",
            expiry.expiry_status if expiry else "",
            expiry.expiry_status_confidence if expiry else "",
            str(expiry.expiry_opportunity_score) if expiry and expiry.expiry_opportunity_score is not None else "",
            str(expiry.active_family_risk).lower() if expiry and expiry.active_family_risk is not None else "",
            expiry.maintenance_status if expiry else "",
            str(signals.usage_signal_score) if signals and signals.usage_signal_score is not None else "",
            str(signals.evidence_count) if signals and signals.evidence_count is not None else "",
            str(signals.has_self_citation_risk).lower() if signals and signals.has_self_citation_risk is not None else "",
            patent.legal_status or "",
            expiry.legal_status_confidence if expiry else "",
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    today = date_type.today().isoformat()

    # Write audit row
    export_row = Export(
        user_id=user_id,
        export_type="csv",
        scope="expiry_list",
        payload_size_bytes=len(csv_bytes),
    )
    db.add(export_row)
    await db.commit()

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expiry-{today}.csv"},
    )
