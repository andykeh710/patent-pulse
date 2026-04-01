"""
Patent Family API endpoints.

Provides access to INPADOC family data and cross-jurisdiction analysis.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.core.models import PatentPublication

router = APIRouter()


class FamilyMember(BaseModel):
    id: str
    doc_id: str
    office: str
    publication_number: str
    legal_status: str | None
    is_primary: bool


class FamilyResponse(BaseModel):
    family_id: str
    member_count: int
    primary: FamilyMember | None
    members: list[FamilyMember]
    jurisdictions: list[str]


class FamilyListItem(BaseModel):
    family_id: str
    member_count: int
    primary_doc_id: str | None
    jurisdictions: list[str]
    has_grant: bool


@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(db: DbSession, family_id: str) -> FamilyResponse:
    """
    Get detailed information about a patent family.

    Returns all family members with their office and status.
    """
    result = await db.execute(
        select(PatentPublication)
        .where(PatentPublication.family_id == family_id)
        .order_by(PatentPublication.publication_date.asc())
    )
    members = result.scalars().all()

    if not members:
        raise HTTPException(status_code=404, detail="Family not found")

    grants = [m for m in members if m.legal_status == "GRANTED"]
    priority_offices = ["USPTO", "EPO"]

    primary = None
    if grants:
        priority_grants = [g for g in grants if g.office in priority_offices]
        primary = priority_grants[0] if priority_grants else grants[0]
    else:
        priority_pubs = [m for m in members if m.office in priority_offices]
        if priority_pubs:
            primary = min(
                priority_pubs, key=lambda x: x.publication_date or "9999-99-99"
            )
        else:
            primary = members[0]

    jurisdictions = list(set(m.office for m in members))

    member_list = [
        FamilyMember(
            id=str(m.id),
            doc_id=m.doc_id,
            office=m.office,
            publication_number=m.publication_number,
            legal_status=m.legal_status,
            is_primary=(m.id == primary.id) if primary else False,
        )
        for m in members
    ]

    primary_member = None
    if primary:
        primary_member = FamilyMember(
            id=str(primary.id),
            doc_id=primary.doc_id,
            office=primary.office,
            publication_number=primary.publication_number,
            legal_status=primary.legal_status,
            is_primary=True,
        )

    return FamilyResponse(
        family_id=family_id,
        member_count=len(members),
        primary=primary_member,
        members=member_list,
        jurisdictions=jurisdictions,
    )


@router.get("/by-patent/{patent_id}", response_model=FamilyResponse | None)
async def get_family_by_patent(db: DbSession, patent_id: UUID) -> FamilyResponse | None:
    """
    Get family information for a specific patent.

    Returns null if the patent has no family_id assigned.
    """
    result = await db.execute(
        select(PatentPublication.family_id).where(PatentPublication.id == patent_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Patent not found")

    family_id = row[0]
    if not family_id:
        return None

    return await get_family(db, family_id)


@router.get("", response_model=list[FamilyListItem])
async def list_families(
    db: DbSession,
    min_members: int = Query(default=2, ge=1),
    office: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[FamilyListItem]:
    """
    List patent families with multiple members.

    Useful for finding patents with broad geographic coverage.
    """
    subquery = (
        select(
            PatentPublication.family_id,
            func.count(PatentPublication.id).label("member_count"),
            func.array_agg(PatentPublication.office.distinct()).label("jurisdictions"),
            func.bool_or(PatentPublication.legal_status == "GRANTED").label("has_grant"),
        )
        .where(PatentPublication.family_id.isnot(None))
        .group_by(PatentPublication.family_id)
        .having(func.count(PatentPublication.id) >= min_members)
    )

    if office:
        subquery = subquery.having(
            func.array_agg(PatentPublication.office.distinct()).op("@>")(
                func.array([office])
            )
        )

    subquery = subquery.order_by(func.count(PatentPublication.id).desc()).limit(limit)

    result = await db.execute(subquery)
    rows = result.all()

    families = []
    for row in rows:
        primary_result = await db.execute(
            select(PatentPublication.doc_id)
            .where(PatentPublication.family_id == row.family_id)
            .where(PatentPublication.legal_status == "GRANTED")
            .limit(1)
        )
        primary_doc = primary_result.scalar()

        families.append(
            FamilyListItem(
                family_id=row.family_id,
                member_count=row.member_count,
                primary_doc_id=primary_doc,
                jurisdictions=row.jurisdictions or [],
                has_grant=row.has_grant or False,
            )
        )

    return families
