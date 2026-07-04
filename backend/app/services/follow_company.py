import re

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import UserCompanyFollow

_SUFFIX_RE = re.compile(
    r"[ ,.]+(inc|corp|ltd|llc|gmbh|sa|ag|co)\.?$",
    re.IGNORECASE,
)


def normalize_company_name(name: str) -> str:
    """Normalize a company assignee name for deduplication / lookup."""
    return _SUFFIX_RE.sub("", name.strip()).strip().lower()


async def add_follow(db: AsyncSession, user_id: str, company_name: str) -> UserCompanyFollow:
    """Follow a company. Creates a UserCompanyFollow row."""
    normalized = normalize_company_name(company_name)
    follow = UserCompanyFollow(
        user_id=user_id,
        company_normalized_name=normalized,
        display_name=company_name,
    )
    db.add(follow)
    await db.commit()
    await db.refresh(follow)
    return follow


async def remove_follow(db: AsyncSession, user_id: str, normalized_name: str) -> bool:
    """Unfollow a company by normalized name. Returns True if deleted."""
    result = await db.execute(
        delete(UserCompanyFollow).where(
            UserCompanyFollow.user_id == user_id,
            UserCompanyFollow.company_normalized_name == normalized_name,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def list_follows(db: AsyncSession, user_id: str) -> list[UserCompanyFollow]:
    """List all companies a user follows."""
    result = await db.execute(select(UserCompanyFollow).where(UserCompanyFollow.user_id == user_id))
    return list(result.scalars().all())
