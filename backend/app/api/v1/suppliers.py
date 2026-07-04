from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession, current_user

router = APIRouter()


class SupplierSummary(BaseModel):
    total_suppliers: int
    suppliers_with_country: int
    entity_type_enrichment_pending: bool  # True when no verified source exists
    total_supplier_patents: int
    average_patents_per_supplier: float
    high_opportunity_suppliers: int
    countries: list[dict[str, int | str]]


class SupplierItem(BaseModel):
    name: str
    country: str | None
    entity_type: str | None
    enrichment_source: str | None = None  # None = unverified; 'patentsview' = verified
    patent_count: int
    active_patent_count: int
    expiring_soon_count: int
    technology_area_count: int
    average_signal_score: float | None
    supplier_score: float


class SupplierListResponse(BaseModel):
    items: list[SupplierItem]
    total: int
    page: int
    page_size: int
    pages: int


class SupplierMapCountry(BaseModel):
    country: str
    supplier_count: int
    patent_count: int
    average_supplier_score: float
    top_suppliers: list[dict[str, int | str | float]]


def _score_supplier(
    patent_count: int,
    active_patent_count: int,
    expiring_soon_count: int,
    technology_area_count: int,
    average_signal_score: float | None,
) -> float:
    score = min(patent_count, 20) * 2.0
    score += min(active_patent_count, 20) * 1.5
    score += min(technology_area_count, 8) * 4.0
    if average_signal_score is not None:
        score += max(0.0, min(average_signal_score, 100.0)) * 0.25
    score -= min(expiring_soon_count, 10) * 1.5
    return round(max(0.0, min(score, 100.0)), 2)


def _supplier_filters(country: str | None, entity_type: str | None) -> str:
    filters = ["supplier_name IS NOT NULL", "supplier_name != ''"]
    if country:
        filters.append("lower(country) = lower(:country)")
    if entity_type:
        filters.append("lower(entity_type) = lower(:entity_type)")
    return " AND ".join(filters)


@router.get("/summary", response_model=SupplierSummary)
async def supplier_summary(db: DbSession) -> SupplierSummary:
    today = date.today()
    five_years = today + timedelta(days=5 * 365)

    rows = (
        (
            await db.execute(
                text(
                    """
            WITH supplier_rows AS (
                SELECT
                    assignee_val AS supplier_name,
                    MAX(a.country) AS country,
                    MAX(a.entity_type) AS entity_type,
                    COUNT(DISTINCT p.id) AS patent_count,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.legal_status = 'GRANTED') AS active_patent_count,
                    COUNT(DISTINCT p.id) FILTER (
                        WHERE p.legal_status = 'GRANTED'
                          AND p.estimated_expiry_date >= :today
                          AND p.estimated_expiry_date <= :five_years
                    ) AS expiring_soon_count,
                    COUNT(DISTINCT LEFT(cpc_val, 1)) FILTER (WHERE cpc_val IS NOT NULL AND cpc_val != '') AS technology_area_count,
                    AVG(COALESCE(p.opportunity_score, p.interesting_score)) AS average_signal_score
                FROM patent_publications p
                JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
                LEFT JOIN LATERAL jsonb_array_elements_text(p.cpc) AS cpc_val ON true
                LEFT JOIN assignees a
                    ON lower(a.display_name) = lower(assignee_val)
                    OR lower(a.normalized_name) = lower(assignee_val)
                WHERE assignee_val IS NOT NULL AND assignee_val != ''
                GROUP BY assignee_val
            )
            SELECT * FROM supplier_rows
            """
                ).bindparams(today=today, five_years=five_years)
            )
        )
        .mappings()
        .all()
    )

    items = [
        SupplierItem(
            name=row["supplier_name"],
            country=row["country"],
            entity_type=row["entity_type"],
            patent_count=int(row["patent_count"] or 0),
            active_patent_count=int(row["active_patent_count"] or 0),
            expiring_soon_count=int(row["expiring_soon_count"] or 0),
            technology_area_count=int(row["technology_area_count"] or 0),
            average_signal_score=round(float(row["average_signal_score"]), 2)
            if row["average_signal_score"] is not None
            else None,
            supplier_score=_score_supplier(
                int(row["patent_count"] or 0),
                int(row["active_patent_count"] or 0),
                int(row["expiring_soon_count"] or 0),
                int(row["technology_area_count"] or 0),
                float(row["average_signal_score"])
                if row["average_signal_score"] is not None
                else None,
            ),
        )
        for row in rows
    ]

    country_counts: dict[str, int] = {}
    for item in items:
        if item.country:
            country_counts[item.country] = country_counts.get(item.country, 0) + 1

    total_patents = sum(item.patent_count for item in items)
    total = len(items)

    return SupplierSummary(
        total_suppliers=total,
        suppliers_with_country=sum(1 for item in items if item.country),
        entity_type_enrichment_pending=True,  # no verified source data yet
        total_supplier_patents=total_patents,
        average_patents_per_supplier=round(total_patents / total, 2) if total else 0.0,
        high_opportunity_suppliers=sum(1 for item in items if item.supplier_score >= 60),
        countries=[
            {"country": country, "count": count}
            for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        ],
    )


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    db: DbSession,
    country: str | None = None,
    entity_type: str | None = None,
    min_patent_count: int = Query(default=1, ge=1, le=10000),
    sort_by: Literal[
        "supplier_score", "patent_count", "active_patent_count", "average_signal_score"
    ] = "supplier_score",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SupplierListResponse:
    today = date.today()
    five_years = today + timedelta(days=5 * 365)
    where_clause = _supplier_filters(country, entity_type)
    params = {
        "today": today,
        "five_years": five_years,
        "min_patent_count": min_patent_count,
    }
    if country:
        params["country"] = country
    if entity_type:
        params["entity_type"] = entity_type

    rows = (
        (
            await db.execute(
                text(
                    f"""
            WITH supplier_rows AS (
                SELECT
                    assignee_val AS supplier_name,
                    MAX(a.country) AS country,
                    MAX(a.entity_type) AS entity_type,
                    COUNT(DISTINCT p.id) AS patent_count,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.legal_status = 'GRANTED') AS active_patent_count,
                    COUNT(DISTINCT p.id) FILTER (
                        WHERE p.legal_status = 'GRANTED'
                          AND p.estimated_expiry_date >= :today
                          AND p.estimated_expiry_date <= :five_years
                    ) AS expiring_soon_count,
                    COUNT(DISTINCT LEFT(cpc_val, 1)) FILTER (WHERE cpc_val IS NOT NULL AND cpc_val != '') AS technology_area_count,
                    AVG(COALESCE(p.opportunity_score, p.interesting_score)) AS average_signal_score
                FROM patent_publications p
                JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
                LEFT JOIN LATERAL jsonb_array_elements_text(p.cpc) AS cpc_val ON true
                LEFT JOIN assignees a
                    ON lower(a.display_name) = lower(assignee_val)
                    OR lower(a.normalized_name) = lower(assignee_val)
                GROUP BY assignee_val
            )
            SELECT * FROM supplier_rows
            WHERE {where_clause}
              AND patent_count >= :min_patent_count
            """
                ).bindparams(**params)
            )
        )
        .mappings()
        .all()
    )

    items = [
        SupplierItem(
            name=row["supplier_name"],
            country=row["country"],
            entity_type=row["entity_type"],
            patent_count=int(row["patent_count"] or 0),
            active_patent_count=int(row["active_patent_count"] or 0),
            expiring_soon_count=int(row["expiring_soon_count"] or 0),
            technology_area_count=int(row["technology_area_count"] or 0),
            average_signal_score=round(float(row["average_signal_score"]), 2)
            if row["average_signal_score"] is not None
            else None,
            supplier_score=_score_supplier(
                int(row["patent_count"] or 0),
                int(row["active_patent_count"] or 0),
                int(row["expiring_soon_count"] or 0),
                int(row["technology_area_count"] or 0),
                float(row["average_signal_score"])
                if row["average_signal_score"] is not None
                else None,
            ),
        )
        for row in rows
    ]

    reverse = sort_order == "desc"
    items.sort(key=lambda item: getattr(item, sort_by) or 0, reverse=reverse)
    total = len(items)
    offset = (page - 1) * page_size
    paged = items[offset : offset + page_size]
    pages = (total + page_size - 1) // page_size

    return SupplierListResponse(
        items=paged, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/map", response_model=list[SupplierMapCountry])
async def supplier_map(db: DbSession) -> list[SupplierMapCountry]:
    data = await list_suppliers(
        db=db,
        country=None,
        entity_type=None,
        min_patent_count=1,
        sort_by="supplier_score",
        sort_order="desc",
        page=1,
        page_size=10000,
    )
    countries: dict[str, list[SupplierItem]] = {}
    for item in data.items:
        key = item.country or "Unknown"
        countries.setdefault(key, []).append(item)

    result: list[SupplierMapCountry] = []
    for country, items in countries.items():
        top = sorted(items, key=lambda item: item.supplier_score, reverse=True)[:5]
        result.append(
            SupplierMapCountry(
                country=country,
                supplier_count=len(items),
                patent_count=sum(item.patent_count for item in items),
                average_supplier_score=round(
                    sum(item.supplier_score for item in items) / len(items), 2
                ),
                top_suppliers=[
                    {
                        "name": item.name,
                        "patent_count": item.patent_count,
                        "supplier_score": item.supplier_score,
                    }
                    for item in top
                ],
            )
        )

    return sorted(result, key=lambda item: item.patent_count, reverse=True)


class CompanyProfile(BaseModel):
    name: str
    country: str | None
    entity_type: str | None
    enrichment_source: str | None = None  # None = unverified
    patent_count: int
    active_patent_count: int
    expiring_soon_count: int
    technology_area_count: int
    average_signal_score: float | None
    supplier_score: float
    top_cpc: list[dict[str, int | str]]
    recent_patents: list[dict[str, str | float | None]]
    top_inventors: list[dict[str, str | int]] = []


@router.get("/profile/{name}", response_model=CompanyProfile)
async def company_profile(
    db: DbSession,
    name: str,
) -> CompanyProfile:
    """Get profile for a specific company/assignee by name."""
    today = date.today()
    five_years = today + timedelta(days=5 * 365)

    # Get aggregates for this assignee
    row = (
        (
            await db.execute(
                text(
                    """
            WITH supplier_row AS (
                SELECT
                    assignee_val AS supplier_name,
                    MAX(a.country) AS country,
                    MAX(a.entity_type) AS entity_type,
                    COUNT(DISTINCT p.id) AS patent_count,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.legal_status = 'GRANTED') AS active_patent_count,
                    COUNT(DISTINCT p.id) FILTER (
                        WHERE p.legal_status = 'GRANTED'
                          AND p.estimated_expiry_date >= :today
                          AND p.estimated_expiry_date <= :five_years
                    ) AS expiring_soon_count,
                    COUNT(DISTINCT LEFT(cpc_val, 1)) FILTER (WHERE cpc_val IS NOT NULL AND cpc_val != '') AS technology_area_count,
                    AVG(COALESCE(p.opportunity_score, p.interesting_score)) AS average_signal_score
                FROM patent_publications p
                JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
                LEFT JOIN LATERAL jsonb_array_elements_text(p.cpc) AS cpc_val ON true
                LEFT JOIN assignees a
                    ON lower(a.display_name) = lower(assignee_val)
                    OR lower(a.normalized_name) = lower(assignee_val)
                WHERE lower(assignee_val) = lower(:name)
                GROUP BY assignee_val
            )
            SELECT * FROM supplier_row
            """
                ).bindparams(today=today, five_years=five_years, name=name)
            )
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail=f"Company '{name}' not found")

    # Top CPC codes
    cpc_rows = (
        await db.execute(
            text(
                """
            SELECT LEFT(cpc_val, 4) AS cpc, COUNT(*) AS count
            FROM patent_publications p
            JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
            JOIN LATERAL jsonb_array_elements_text(p.cpc) AS cpc_val ON true
            WHERE lower(assignee_val) = lower(:name)
              AND cpc_val IS NOT NULL AND cpc_val != ''
            GROUP BY LEFT(cpc_val, 4)
            ORDER BY count DESC
            LIMIT 10
            """
            ).bindparams(name=name)
        )
    ).fetchall()

    # Recent patents
    recent_rows = (
        await db.execute(
            text(
                """
            SELECT p.id, p.doc_id, p.title, p.publication_date, p.opportunity_score
            FROM patent_publications p
            JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
            WHERE lower(assignee_val) = lower(:name)
            ORDER BY p.publication_date DESC NULLS LAST
            LIMIT 10
            """
            ).bindparams(name=name)
        )
    ).fetchall()

    # Top inventors
    inventor_rows = (
        await db.execute(
            text(
                """
            SELECT inv_val AS name, COUNT(DISTINCT p.id) AS patent_count
            FROM patent_publications p
            JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
            JOIN LATERAL jsonb_array_elements_text(p.inventors) AS inv_val ON true
            WHERE lower(assignee_val) = lower(:name)
              AND inv_val IS NOT NULL AND inv_val != ''
            GROUP BY inv_val
            ORDER BY patent_count DESC
            LIMIT 5
            """
            ).bindparams(name=name)
        )
    ).fetchall()

    return CompanyProfile(
        name=row["supplier_name"],
        country=row["country"],
        entity_type=row["entity_type"],
        patent_count=int(row["patent_count"] or 0),
        active_patent_count=int(row["active_patent_count"] or 0),
        expiring_soon_count=int(row["expiring_soon_count"] or 0),
        technology_area_count=int(row["technology_area_count"] or 0),
        average_signal_score=round(float(row["average_signal_score"]), 2)
        if row["average_signal_score"] is not None
        else None,
        supplier_score=_score_supplier(
            int(row["patent_count"] or 0),
            int(row["active_patent_count"] or 0),
            int(row["expiring_soon_count"] or 0),
            int(row["technology_area_count"] or 0),
            float(row["average_signal_score"]) if row["average_signal_score"] is not None else None,
        ),
        top_cpc=[{"cpc": r.cpc, "count": r.count} for r in cpc_rows],
        recent_patents=[
            {
                "id": str(r.id),
                "doc_id": r.doc_id,
                "title": r.title,
                "publication_date": str(r.publication_date) if r.publication_date else None,
                "opportunity_score": float(r.opportunity_score) if r.opportunity_score else None,
            }
            for r in recent_rows
        ],
        top_inventors=[{"name": r.name, "patent_count": r.patent_count} for r in inventor_rows],
    )


# -- Company follow endpoints (Sprint 5) --


class FollowStatus(BaseModel):
    is_following: bool
    company_name: str


@router.get("/follow/{name}", response_model=FollowStatus)
async def check_follow(
    name: str,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> FollowStatus:
    """Check if the current user follows a company."""
    from app.services.follow_company import list_follows, normalize_company_name

    follows = await list_follows(db, user_id)
    normalized = normalize_company_name(name)
    is_following = any(f.company_normalized_name == normalized for f in follows)
    return FollowStatus(is_following=is_following, company_name=name)


@router.post("/follow/{name}")
async def follow_company(
    name: str,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> dict:
    """Follow a company."""
    from app.services.follow_company import add_follow

    await add_follow(db, user_id, name)
    return {"status": "following", "company_name": name}


@router.delete("/follow/{name}")
async def unfollow_company(
    name: str,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> dict:
    """Unfollow a company."""
    from app.services.follow_company import normalize_company_name, remove_follow

    normalized = normalize_company_name(name)
    removed = await remove_follow(db, user_id, normalized)
    if not removed:
        raise HTTPException(status_code=404, detail="Not following this company")
    return {"status": "unfollowed", "company_name": name}


@router.get("/follows")
async def list_followed_companies(
    db: DbSession,
    user_id: str = Depends(current_user),
) -> list[dict]:
    """List companies the current user follows."""
    from app.services.follow_company import list_follows

    follows = await list_follows(db, user_id)
    return [
        {"company_name": f.display_name, "normalized_name": f.company_normalized_name}
        for f in follows
    ]
