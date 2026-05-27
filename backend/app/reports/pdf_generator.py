"""PDF report generator (Sprint 7). Single-patent branded PDF via WeasyPrint."""
from __future__ import annotations

import logging
import re
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import AIArtifact, PatentUsageSignals, ExpiryAssessment
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

TEMPLATE_DIR = str(__import__("pathlib").Path(__file__).parent / "templates")
_jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

FORBIDDEN_PHRASES = [
    "free to use",
    "public domain",
    "is used by",
    "definitely used",
]


def _filter_forbidden(text: str) -> str:
    """Replace forbidden phrases in legacy cached AI content."""
    for phrase in FORBIDDEN_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("[filtered]", text)
    return text


async def generate_patent_report(
    session: AsyncSession,
    patent_id: UUID,
) -> bytes:
    """Render a single patent as branded PDF. Returns PDF bytes."""
    from fastapi import HTTPException

    patent = (await session.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )).scalar_one_or_none()

    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    expiry_row = (await session.execute(
        select(ExpiryAssessment).where(ExpiryAssessment.patent_publication_id == patent_id)
    )).scalar_one_or_none()

    usage_row = (await session.execute(
        select(PatentUsageSignals).where(PatentUsageSignals.patent_publication_id == patent_id)
    )).scalar_one_or_none()

    # Fetch top 5 usage evidence rows
    from app.core.ai_models import UsageEvidence
    evidence_rows = (await session.execute(
        select(UsageEvidence).where(UsageEvidence.patent_id == patent_id).limit(5)
    )).scalars().all() if usage_row else []

    # Fetch cached why_now AIArtifact
    why_now = None
    why_now_artifact = (await session.execute(
        select(AIArtifact).where(
            AIArtifact.subject_key == f"why_now:{patent_id}",
        ).order_by(AIArtifact.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if why_now_artifact and why_now_artifact.content_json:
        why_now = _filter_forbidden(str(why_now_artifact.content_json.get("summary", "")))

    # Fetch claims summary from cache
    claims_artifact = (await session.execute(
        select(AIArtifact).where(
            AIArtifact.subject_key == f"claims_summary:{patent_id}",
        ).order_by(AIArtifact.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    claims_data = None
    if claims_artifact and claims_artifact.content_json:
        cj = claims_artifact.content_json
        claims_data = {
            "what_it_is": _filter_forbidden(str(cj.get("what_it_is", ""))),
            "problem_solved": _filter_forbidden(str(cj.get("problem_solved", ""))),
            "commercial_significance": _filter_forbidden(str(cj.get("commercial_significance", ""))),
        }

    family_members = getattr(patent, "family_members", None) or []

    # Build template context
    ctx = {
        "title": patent.title or patent.doc_id,
        "doc_id": patent.doc_id or "",
        "assignees": "; ".join(patent.assignees or []),
        "filing_date": str(patent.filing_date) if patent.filing_date else None,
        "grant_date": str(patent.issue_date) if getattr(patent, "issue_date", None) else None,
        "legal_status": getattr(patent, "legal_status", None),
        "expiry": {
            "status": expiry_row.expiry_status if expiry_row else "unknown",
            "confidence": expiry_row.expiry_status_confidence if expiry_row else "unknown",
            "estimated_date": str(expiry_row.estimated_expiry_date) if expiry_row and expiry_row.estimated_expiry_date else None,
            "days_until": str(expiry_row.days_until_expiry) if expiry_row and expiry_row.days_until_expiry is not None else None,
            "opportunity_score": str(expiry_row.expiry_opportunity_score) if expiry_row and expiry_row.expiry_opportunity_score is not None else None,
            "active_family_risk": str(expiry_row.active_family_risk).lower() if expiry_row else "unknown",
            "maintenance_status": expiry_row.maintenance_status if expiry_row else None,
        },
        "claims_summary": claims_data,
        "claims": None,  # raw claims not fetched for PDF — use summary
        "family_members": family_members[:10] if family_members else [],
        "family_id": getattr(patent, "family_id", None),
        "usage": {
            "score": str(usage_row.usage_signal_score) if usage_row and usage_row.usage_signal_score is not None else "N/A",
            "evidence_count": usage_row.evidence_count if usage_row else 0,
            "strong": usage_row.strong_evidence_count if usage_row else 0,
            "medium": usage_row.medium_evidence_count if usage_row else 0,
            "weak": usage_row.weak_evidence_count if usage_row else 0,
            "has_self_cite": usage_row.has_self_citation_risk if usage_row else False,
            "top_evidence": [
                {
                    "source_title": getattr(e, "source_patent_title", "N/A"),
                    "source_patent": getattr(e, "source_patent_doc_id", "N/A"),
                    "source_assignee": getattr(e, "source_patent_assignee", "N/A"),
                    "tier": getattr(e, "evidence_tier", "weak"),
                    "similarity": str(getattr(e, "similarity_score", "N/A")),
                }
                for e in evidence_rows
            ],
        } if usage_row else None,
        "why_now": {
            "summary": why_now,
            "model": why_now_artifact.model if why_now_artifact else "unknown",
            "key_points": _filter_forbidden(why_now_artifact.content_json.get("key_points", [])) if why_now_artifact else [],
        } if why_now else None,
    }

    template = _jinja_env.get_template("patent_report.html")
    html = template.render(ctx)

    return _render_pdf(html)


def _render_pdf(html: str) -> bytes:
    import weasyprint
    return weasyprint.HTML(string=html).write_pdf()
