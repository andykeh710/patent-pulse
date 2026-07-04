"""Sprint 7 — PDF report endpoint."""

from __future__ import annotations

from datetime import date as date_type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import current_user, get_db
from app.core.ai_models import User
from app.core.billing_models import Export
from app.reports.pdf_generator import generate_patent_report

router = APIRouter()

PDF_TIERS = {"lifetime", "enterprise"}


@router.post("/{patent_id}/report")
async def get_patent_report(
    patent_id: UUID,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Generate a branded PDF report for a single patent.

    Requires Lifetime or Enterprise tier.
    """
    from sqlalchemy import select

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    tier = user.tier if user else "free"
    if tier not in PDF_TIERS:
        raise HTTPException(
            status_code=402,
            detail="PDF reports require Lifetime or Enterprise tier. Upgrade at /account/billing.",
        )

    pdf_bytes = await generate_patent_report(db, patent_id)

    db.add(
        Export(
            user_id=user_id,
            export_type="pdf",
            scope="patent_report",
            payload_size_bytes=len(pdf_bytes),
        )
    )
    await db.commit()

    today = date_type.today().isoformat()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=patent-report-{patent_id}-{today}.pdf"
        },
    )
