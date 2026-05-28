"""Sprint 7 — Enterprise API key management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import current_user, get_db
from app.auth.api_keys import generate_api_key
from app.core.billing_models import APIKey

router = APIRouter()


class CreateAPIKeyRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)


class APIKeyResponse(BaseModel):
    id: UUID
    key_prefix: str
    name: str | None
    raw_token: str | None = None  # only present on create
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    body: CreateAPIKeyRequest = CreateAPIKeyRequest(),
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    # Enterprise tier gate (inlined to avoid double Depends(current_user))
    from app.core.ai_models import User as _U
    u = (await db.execute(select(_U).where(_U.id == user_id))).scalar_one_or_none()
    if not u or u.tier != "enterprise":
        raise HTTPException(status_code=402, detail="API keys require Enterprise tier. Upgrade at /account/billing.")

    raw_token, key_hash = generate_api_key()
    key_row = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=raw_token[:16],
        name=body.name,
    )
    db.add(key_row)
    await db.commit()
    await db.refresh(key_row)

    return APIKeyResponse(
        id=key_row.id,
        key_prefix=key_row.key_prefix,
        name=key_row.name,
        raw_token=raw_token,
        last_used_at=None,
        revoked_at=None,
        created_at=key_row.created_at,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    rows = (await db.execute(
        select(APIKey).where(APIKey.user_id == user_id)
    )).scalars().all()
    return [
        APIKeyResponse(
            id=k.id, key_prefix=k.key_prefix, name=k.name,
            last_used_at=k.last_used_at, revoked_at=k.revoked_at, created_at=k.created_at,
        )
        for k in rows
    ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
async def revoke_api_key(
    api_key_id: UUID,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    key_row = (await db.execute(
        select(APIKey).where(APIKey.id == api_key_id)
    )).scalar_one_or_none()

    if not key_row:
        raise HTTPException(status_code=404, detail="API key not found")
    if key_row.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your API key")

    key_row.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return None
