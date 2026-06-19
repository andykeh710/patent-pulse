"""Onboarding wizard API.

POST /onboarding/complete  — submit persona + industry + interests,
                             returns suggested companies and themes.
POST /onboarding/confirm   — accept suggestions, create follows +
                             subscriptions, mark onboarded.
GET  /onboarding/status    — return onboarded state.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text

from app.api.deps import current_user, get_db
from app.core.ai_models import User, UserCompanyFollow
from app.services.industry_cpc_map import INDUSTRY_CPC_MAP

router = APIRouter()


# ── Request / response models ────────────────────────────────────


class OnboardingCompleteRequest(BaseModel):
    persona: str
    industry_focus: str
    interests_freetext: str = ""
    use_case: str | None = None


class SuggestedCompany(BaseModel):
    normalized_name: str
    display_name: str
    patent_count: int
    top_cpc_prefixes: list[str]


class SuggestedTheme(BaseModel):
    id: str
    name: str
    description: str | None
    cpc_prefixes: list[str]


class OnboardingCompleteResponse(BaseModel):
    suggested_companies: list[SuggestedCompany]
    suggested_themes: list[SuggestedTheme]


class OnboardingConfirmRequest(BaseModel):
    company_ids: list[str]  # normalized_name values
    theme_ids: list[str]    # UUID strings


class OnboardingConfirmResponse(BaseModel):
    ok: bool


class OnboardingStatusResponse(BaseModel):
    onboarded: bool
    persona: str | None


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def onboarding_complete(
    body: OnboardingCompleteRequest,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Submit wizard answers and get suggested companies + themes."""
    from app.core.ai_models import User as UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user fields
    user.persona = body.persona
    user.industry_focus = body.industry_focus
    if body.interests_freetext:
        user.interests_freetext = body.interests_freetext
    if body.use_case is not None:
        user.use_case = body.use_case
    await db.commit()

    # Get CPC prefixes for this industry
    cpc_prefixes = INDUSTRY_CPC_MAP.get(body.industry_focus, [])

    # ── Suggested companies: top assignees by patent count ────────
    companies: list[SuggestedCompany] = []
    if cpc_prefixes:
        company_rows = await db.execute(
            text("""
                SELECT normalized_name, display_name, patent_count
                FROM assignees
                WHERE patent_count > 0
                ORDER BY patent_count DESC
                LIMIT 5
            """)
        )
        rows = company_rows.fetchall()
        companies = [
            SuggestedCompany(
                normalized_name=row[0],
                display_name=row[1] or row[0],
                patent_count=row[2] or 0,
                top_cpc_prefixes=cpc_prefixes[:3],
            )
            for row in rows
        ]

    # ── Suggested themes: existing themes matching CPC prefixes ───
    themes: list[SuggestedTheme] = []
    if cpc_prefixes:
        # Use ANY to match JSON array
        like_clauses = " OR ".join(
            [f"cpc_prefixes::text ILIKE '%{cpc}%'" for cpc in cpc_prefixes]
        )
        theme_rows = await db.execute(
            text(
                f"""
                SELECT id, name, description, cpc_prefixes
                FROM themes
                WHERE is_active = true AND ({like_clauses})
                LIMIT 3
                """
            )
        )
        for row in theme_rows.fetchall():
            themes.append(
                SuggestedTheme(
                    id=str(row[0]),
                    name=row[1],
                    description=row[2],
                    cpc_prefixes=list(row[3]) if row[3] else [],
                )
            )

    return OnboardingCompleteResponse(
        suggested_companies=companies,
        suggested_themes=themes,
    )


@router.post("/confirm", response_model=OnboardingConfirmResponse)
async def onboarding_confirm(
    body: OnboardingConfirmRequest,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Accept suggestions, create subscriptions, mark onboarded."""
    from app.core.ai_models import User as UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create company follows
    for name in body.company_ids:
        existing = await db.execute(
            select(UserCompanyFollow).where(
                UserCompanyFollow.user_id == user_id,
                UserCompanyFollow.company_normalized_name == name,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(
                UserCompanyFollow(
                    user_id=user_id,
                    company_normalized_name=name,
                    display_name=name,
                )
            )

    # Create theme subscriptions for theme_ids
    from app.core.subscription_models import TopicSubscription

    for tid in body.theme_ids:
        existing = await db.execute(
            select(TopicSubscription).where(
                TopicSubscription.user_id == user_id,
                TopicSubscription.theme_id == tid,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(
                TopicSubscription(
                    user_id=user_id,
                    theme_id=tid,
                    mode="instant_alert",
                )
            )

    user.onboarded_at = datetime.utcnow()
    await db.commit()

    return OnboardingConfirmResponse(ok=True)


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Check whether the current user has completed onboarding."""
    result = await db.execute(
        select(User.onboarded_at, User.persona).where(User.id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return OnboardingStatusResponse(
        onboarded=row[0] is not None,
        persona=row[1],
    )
