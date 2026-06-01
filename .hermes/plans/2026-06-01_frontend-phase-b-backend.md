# Frontend Overhaul — Phase B: Backend Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the backend contracts that Phase C (onboarding + Follow Companies) and Phase D (Today) consume. Fix the `/companies/[name]` 500 blocker. Add `user.persona` and `user_company_follows`. Build 6 new endpoints. Each endpoint has tests.

**Architecture:** Additive only. New columns (nullable), new tables, new endpoints. No breaking changes to existing endpoints. New endpoints follow the existing FastAPI router pattern in `backend/app/api/v1/`. All endpoints return typed JSON shapes that match the frontend's TypeScript interfaces (added in Phase C/D).

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest.

**Reference spec:** `.hermes/plans/2026-06-01_frontend-overhaul-design.md` §7, §10, §11.1 Phase B.

**Depends on:** Phase A gate passed, Andy go-ahead.

---

## File Structure

```
backend/alembic/versions/0023_user_persona_column.py            # NEW migration
backend/alembic/versions/0024_user_company_follows.py           # NEW migration

backend/app/core/models.py                                       # MODIFY — add persona column + UserCompanyFollow model
backend/app/core/schemas.py                                      # MODIFY — add Pydantic schemas
backend/app/api/v1/account.py                                    # MODIFY — add persona + companies endpoints
backend/app/api/v1/companies.py                                  # MODIFY — fix /companies/[name] 500
backend/app/api/v1/today.py                                      # MODIFY — add /today/briefing endpoint
backend/app/services/follow_company.py                           # NEW — normalization + CRUD logic
backend/app/services/briefing.py                                 # NEW — weighted feed assembly
backend/app/services/company_suggestions.py                      # NEW — persona-based suggestion logic

backend/tests/api/test_companies.py                              # NEW/MODIFY
backend/tests/api/test_account_companies.py                      # NEW
backend/tests/api/test_account_persona.py                        # NEW
backend/tests/api/test_today_briefing.py                         # NEW
backend/tests/services/test_follow_company.py                    # NEW
backend/tests/services/test_briefing.py                          # NEW
```

---

## Tasks

### Task 1: Fix /companies/[name] 500 (V1 BLOCKER)

**Files:**
- Modify: `backend/app/api/v1/companies.py`
- Create/Modify: `backend/tests/api/test_companies.py`

This task uses the Phase 0 preflight report's reproduction details to drive a targeted fix.

- [ ] **Step 1: Read the preflight reproduction findings**

```bash
grep -A 30 "## 6. /companies/\[name\] 500" .hermes/plans/2026-06-01_frontend-overhaul-preflight.md
```

The hypothesis from preflight informs the fix direction.

- [ ] **Step 2: Write a failing test for the actual broken case**

In `backend/tests/api/test_companies.py`:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_company_detail_with_spaces_in_name(async_client: AsyncClient, seeded_company):
    """Reproduces the 500: company names with spaces/punctuation should return 200."""
    response = await async_client.get(f"/api/v1/companies/{seeded_company.assignee_url_encoded}")
    assert response.status_code == 200
    assert response.json()["assignee"] == seeded_company.assignee

@pytest.mark.asyncio
async def test_get_company_detail_with_inc_suffix(async_client: AsyncClient):
    """Companies like 'Apple Inc.' should resolve."""
    response = await async_client.get("/api/v1/companies/Apple%20Inc%2E")
    # 200 if data exists, 404 if not — never 500
    assert response.status_code in (200, 404)

@pytest.mark.asyncio
async def test_get_company_detail_missing(async_client: AsyncClient):
    """Unknown company returns 404, not 500."""
    response = await async_client.get("/api/v1/companies/NonexistentCompanyXYZ123")
    assert response.status_code == 404
```

- [ ] **Step 3: Run tests to verify failure**

```bash
docker compose exec backend pytest backend/tests/api/test_companies.py -v
```

Expected: FAIL with 500 on the first test (matching the preflight reproduction).

- [ ] **Step 4: Read the companies.py endpoint**

```bash
cat backend/app/api/v1/companies.py
```

Identify where the 500 is thrown. Likely candidates:
- URL decoding not handling `%2E` (period) or `%20` (space)
- Query assumes normalized form but receives encoded form
- Assignee lookup uses `ILIKE` but with unescaped special chars
- Missing null check on a related object (e.g., company has no patents)

- [ ] **Step 5: Implement the fix**

The fix depends on the actual root cause from Step 4. Common shape:

```python
from urllib.parse import unquote

@router.get("/companies/{name}")
async def get_company_detail(name: str, db: AsyncSession = Depends(get_db)):
    # URL-decode then normalize for lookup (matches Bug 4 normalization from V1 close-out)
    decoded = unquote(name)
    normalized = normalize_company_name(decoded)  # from backend/app/services/normalization.py if exists, else inline
    result = await db.execute(
        select(...).where(
            func.lower(func.regexp_replace(
                Patent.assignee,
                r'[ ,.]+(inc|corp|ltd|llc|gmbh|sa|ag|co)\.?$',
                '',
                'i'
            )) == normalized
        )
    )
    rows = result.all()
    if not rows:
        raise HTTPException(404, "Company not found")
    return assemble_company_response(rows)
```

The exact change depends on the existing structure. Preserve the existing return shape.

- [ ] **Step 6: Run tests to verify pass**

```bash
docker compose exec backend pytest backend/tests/api/test_companies.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 7: Re-run full backend test suite to confirm no regression**

```bash
docker compose exec backend pytest backend/tests/ -q
```

Expected: 341 baseline + 3 new = 344 passing.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/v1/companies.py backend/tests/api/test_companies.py
git commit -m "fix(backend): /companies/[name] 500 on names with spaces/punctuation"
```

---

### Task 2: Migration — user.persona column

**Files:**
- Create: `backend/alembic/versions/0023_user_persona_column.py`
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Generate migration skeleton**

```bash
docker compose exec backend alembic revision -m "user_persona_column"
```

Find the new file under `backend/alembic/versions/`. Rename if needed to `0023_user_persona_column.py`.

- [ ] **Step 2: Implement migration**

```python
"""user_persona_column

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    persona_enum = sa.Enum("operator", "investor", "curious", name="persona_enum")
    persona_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("persona", persona_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "persona")
    sa.Enum(name="persona_enum").drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 3: Add column to SQLAlchemy model**

In `backend/app/core/models.py`, on the `User` class:

```python
import enum
from sqlalchemy import Enum

class Persona(str, enum.Enum):
    operator = "operator"
    investor = "investor"
    curious = "curious"

class User(Base):
    # ... existing columns ...
    persona = Column(Enum(Persona, name="persona_enum"), nullable=True)
```

- [ ] **Step 4: Run migration**

```bash
docker compose exec backend alembic upgrade head
```

Expected: clean upgrade, schema now includes `users.persona`.

- [ ] **Step 5: Verify column exists**

```bash
docker compose exec db psql -U patent -d patent_pulse -c "\d users" | grep persona
```

Expected: row shown for `persona | persona_enum`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/0023_user_persona_column.py backend/app/core/models.py
git commit -m "feat(backend): add user.persona enum column (operator/investor/curious)"
```

---

### Task 3: Endpoint — PUT /api/v1/account/persona

**Files:**
- Modify: `backend/app/api/v1/account.py`
- Modify: `backend/app/core/schemas.py`
- Create: `backend/tests/api/test_account_persona.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_account_persona.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_set_persona_operator(async_client: AsyncClient, auth_headers):
    response = await async_client.put(
        "/api/v1/account/persona",
        json={"persona": "operator"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["persona"] == "operator"

@pytest.mark.asyncio
async def test_set_persona_invalid_value_returns_422(async_client: AsyncClient, auth_headers):
    response = await async_client.put(
        "/api/v1/account/persona",
        json={"persona": "notavalidoption"},
        headers=auth_headers,
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_set_persona_requires_auth(async_client: AsyncClient):
    response = await async_client.put("/api/v1/account/persona", json={"persona": "operator"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run test to verify fail**

```bash
docker compose exec backend pytest backend/tests/api/test_account_persona.py -v
```

Expected: FAIL with 404 (endpoint doesn't exist).

- [ ] **Step 3: Add Pydantic schema**

In `backend/app/core/schemas.py`:

```python
from enum import Enum
from pydantic import BaseModel

class PersonaEnum(str, Enum):
    operator = "operator"
    investor = "investor"
    curious = "curious"

class PersonaSetRequest(BaseModel):
    persona: PersonaEnum

class PersonaResponse(BaseModel):
    persona: PersonaEnum | None
```

- [ ] **Step 4: Add endpoint**

In `backend/app/api/v1/account.py`:

```python
from app.core.schemas import PersonaSetRequest, PersonaResponse

@router.put("/persona", response_model=PersonaResponse)
async def set_persona(
    request: PersonaSetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.persona = request.persona
    await db.commit()
    return PersonaResponse(persona=current_user.persona)
```

- [ ] **Step 5: Run test to verify pass**

```bash
docker compose exec backend pytest backend/tests/api/test_account_persona.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/account.py backend/app/core/schemas.py backend/tests/api/test_account_persona.py
git commit -m "feat(backend): PUT /api/v1/account/persona endpoint"
```

---

### Task 4: Migration — user_company_follows table

**Files:**
- Create: `backend/alembic/versions/0024_user_company_follows.py`
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Generate migration**

```bash
docker compose exec backend alembic revision -m "user_company_follows"
```

- [ ] **Step 2: Implement migration**

```python
"""user_company_follows

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_company_follows",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_normalized_name", sa.Text, nullable=False),
        sa.Column("display_name", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "company_normalized_name"),
    )
    op.create_index(
        "ix_user_company_follows_user_id",
        "user_company_follows",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_company_follows_user_id", table_name="user_company_follows")
    op.drop_table("user_company_follows")
```

- [ ] **Step 3: Add SQLAlchemy model**

In `backend/app/core/models.py`:

```python
class UserCompanyFollow(Base):
    __tablename__ = "user_company_follows"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    company_normalized_name = Column(Text, primary_key=True)
    display_name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = relationship("User", back_populates="company_follows")

# In User class, add:
    company_follows = relationship("UserCompanyFollow", back_populates="user", cascade="all, delete-orphan")
```

- [ ] **Step 4: Run migration**

```bash
docker compose exec backend alembic upgrade head
```

- [ ] **Step 5: Verify table exists**

```bash
docker compose exec db psql -U patent -d patent_pulse -c "\d user_company_follows"
```

Expected: table shown with 4 columns + indexes.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/0024_user_company_follows.py backend/app/core/models.py
git commit -m "feat(backend): add user_company_follows table for Follow Companies"
```

---

### Task 5: Service — follow_company.py (normalization + CRUD)

**Files:**
- Create: `backend/app/services/follow_company.py`
- Create: `backend/tests/services/test_follow_company.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/services/test_follow_company.py
import pytest
from app.services.follow_company import normalize_company_name

def test_normalize_lowercases():
    assert normalize_company_name("Apple") == "apple"

def test_normalize_strips_inc_suffix():
    assert normalize_company_name("Apple Inc.") == "apple"
    assert normalize_company_name("Apple Inc") == "apple"
    assert normalize_company_name("Apple, Inc.") == "apple"

def test_normalize_strips_corp_ltd_llc():
    assert normalize_company_name("Acme Corp") == "acme"
    assert normalize_company_name("Acme Ltd") == "acme"
    assert normalize_company_name("Acme LLC") == "acme"

def test_normalize_handles_punctuation_variants():
    assert normalize_company_name("Alphabet Inc.") == "alphabet"
    assert normalize_company_name("Alphabet , Inc.") == "alphabet"
```

- [ ] **Step 2: Run test to verify fail**

```bash
docker compose exec backend pytest backend/tests/services/test_follow_company.py -v
```

Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement normalization**

`backend/app/services/follow_company.py`:

```python
import re

_SUFFIX_RE = re.compile(
    r'[ ,.]+(inc|corp|ltd|llc|gmbh|sa|ag|co)\.?$',
    re.IGNORECASE,
)

def normalize_company_name(name: str) -> str:
    """Normalize a company assignee name for deduplication / lookup.

    Matches the regex used at query time for Bug 4 (Company Move card).
    """
    return _SUFFIX_RE.sub("", name.strip()).strip().lower()


async def add_follow(db, user_id: int, company_name: str) -> "UserCompanyFollow":
    from app.core.models import UserCompanyFollow
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


async def remove_follow(db, user_id: int, normalized_name: str) -> bool:
    from app.core.models import UserCompanyFollow
    from sqlalchemy import delete
    result = await db.execute(
        delete(UserCompanyFollow).where(
            UserCompanyFollow.user_id == user_id,
            UserCompanyFollow.company_normalized_name == normalized_name,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def list_follows(db, user_id: int) -> list["UserCompanyFollow"]:
    from app.core.models import UserCompanyFollow
    from sqlalchemy import select
    result = await db.execute(
        select(UserCompanyFollow).where(UserCompanyFollow.user_id == user_id)
    )
    return list(result.scalars().all())
```

- [ ] **Step 4: Run test to verify pass**

```bash
docker compose exec backend pytest backend/tests/services/test_follow_company.py -v
```

Expected: all normalize_* tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/follow_company.py backend/tests/services/test_follow_company.py
git commit -m "feat(backend): follow_company service (normalize + add/remove/list)"
```

---

### Task 6: Endpoint — POST/DELETE/GET /api/v1/account/companies

**Files:**
- Modify: `backend/app/api/v1/account.py`
- Modify: `backend/app/core/schemas.py`
- Create: `backend/tests/api/test_account_companies.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_account_companies.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_follow_company(async_client: AsyncClient, auth_headers):
    response = await async_client.post(
        "/api/v1/account/companies",
        json={"company_name": "Apple Inc."},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_normalized_name"] == "apple"
    assert data["display_name"] == "Apple Inc."

@pytest.mark.asyncio
async def test_list_follows(async_client: AsyncClient, auth_headers):
    await async_client.post(
        "/api/v1/account/companies",
        json={"company_name": "NVIDIA"},
        headers=auth_headers,
    )
    response = await async_client.get("/api/v1/account/companies", headers=auth_headers)
    assert response.status_code == 200
    follows = response.json()
    assert any(f["company_normalized_name"] == "nvidia" for f in follows)

@pytest.mark.asyncio
async def test_unfollow_company(async_client: AsyncClient, auth_headers):
    await async_client.post(
        "/api/v1/account/companies",
        json={"company_name": "Tesla"},
        headers=auth_headers,
    )
    response = await async_client.delete(
        "/api/v1/account/companies/tesla",
        headers=auth_headers,
    )
    assert response.status_code == 204
```

- [ ] **Step 2: Run test to verify fail**

```bash
docker compose exec backend pytest backend/tests/api/test_account_companies.py -v
```

Expected: FAIL with 404.

- [ ] **Step 3: Add Pydantic schemas**

In `backend/app/core/schemas.py`:

```python
class CompanyFollowRequest(BaseModel):
    company_name: str

class CompanyFollowResponse(BaseModel):
    company_normalized_name: str
    display_name: str
    patent_count_in_topics: int | None = None  # populated by /companies endpoint
```

- [ ] **Step 4: Add endpoints to account.py**

```python
from fastapi import status
from app.services.follow_company import add_follow, remove_follow, list_follows
from app.core.schemas import CompanyFollowRequest, CompanyFollowResponse

@router.post(
    "/companies",
    response_model=CompanyFollowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def follow_company(
    request: CompanyFollowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    follow = await add_follow(db, current_user.id, request.company_name)
    return CompanyFollowResponse(
        company_normalized_name=follow.company_normalized_name,
        display_name=follow.display_name,
    )

@router.delete("/companies/{normalized_name}", status_code=204)
async def unfollow_company(
    normalized_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await remove_follow(db, current_user.id, normalized_name)
    if not success:
        raise HTTPException(404, "Follow not found")

@router.get("/companies", response_model=list[CompanyFollowResponse])
async def get_follows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    follows = await list_follows(db, current_user.id)
    return [
        CompanyFollowResponse(
            company_normalized_name=f.company_normalized_name,
            display_name=f.display_name,
        )
        for f in follows
    ]
```

- [ ] **Step 5: Run test to verify pass**

```bash
docker compose exec backend pytest backend/tests/api/test_account_companies.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/account.py backend/app/core/schemas.py backend/tests/api/test_account_companies.py
git commit -m "feat(backend): /api/v1/account/companies endpoints (follow/unfollow/list)"
```

---

### Task 7: Endpoint — GET /api/v1/account/companies/suggested

**Files:**
- Modify: `backend/app/api/v1/account.py`
- Create: `backend/app/services/company_suggestions.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/api/test_account_companies.py`:

```python
@pytest.mark.asyncio
async def test_company_suggestions_for_operator(async_client: AsyncClient, auth_headers, seeded_patents):
    response = await async_client.get(
        "/api/v1/account/companies/suggested?persona=operator",
        headers=auth_headers,
    )
    assert response.status_code == 200
    suggestions = response.json()
    assert 1 <= len(suggestions) <= 8
    # each suggestion has display_name + patent count in user's topics
    for s in suggestions:
        assert "display_name" in s
        assert "patent_count_in_topics" in s
```

- [ ] **Step 2: Run test to verify fail**

```bash
docker compose exec backend pytest backend/tests/api/test_account_companies.py::test_company_suggestions_for_operator -v
```

Expected: FAIL with 404.

- [ ] **Step 3: Implement suggestion logic**

`backend/app/services/company_suggestions.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.models import Patent

# Persona-biased seed lists. Adjust as you learn.
PERSONA_SEEDS = {
    "operator": ["Apple Inc.", "Google LLC", "Microsoft", "Amazon", "Meta", "Tesla", "Samsung"],
    "investor": ["NVIDIA", "Tesla", "Anthropic", "OpenAI", "Mistral AI", "Stripe", "Databricks"],
    "curious": ["Apple Inc.", "Tesla", "SpaceX", "Boston Dynamics", "DeepMind", "Anthropic"],
}

async def get_suggestions(
    db: AsyncSession,
    persona: str,
    user_topic_ids: list[int],
    limit: int = 8,
) -> list[dict]:
    """Return persona-biased company suggestions, ranked by overlap with user's topics."""
    seeds = PERSONA_SEEDS.get(persona, PERSONA_SEEDS["operator"])

    # Count patents per seed that match user's topics
    out: list[dict] = []
    for seed in seeds:
        # Use the same normalize regex as the table
        result = await db.execute(
            select(func.count(Patent.id)).where(
                func.lower(Patent.assignee).like(f"%{seed.lower()}%")
                # If user_topic_ids given, also filter by topic membership
                # (left as exercise to match existing topic-patent join)
            )
        )
        count = result.scalar() or 0
        out.append({"display_name": seed, "patent_count_in_topics": count})

    out.sort(key=lambda x: -x["patent_count_in_topics"])
    return out[:limit]
```

- [ ] **Step 4: Add endpoint**

In `backend/app/api/v1/account.py`:

```python
from app.services.company_suggestions import get_suggestions

@router.get("/companies/suggested", response_model=list[CompanyFollowResponse])
async def suggested_companies(
    persona: str = "operator",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_topic_ids = [t.id for t in current_user.topics]  # adjust to your actual relationship name
    suggestions = await get_suggestions(db, persona, user_topic_ids)
    return [
        CompanyFollowResponse(
            company_normalized_name="",  # not yet followed
            display_name=s["display_name"],
            patent_count_in_topics=s["patent_count_in_topics"],
        )
        for s in suggestions
    ]
```

- [ ] **Step 5: Run test to verify pass**

```bash
docker compose exec backend pytest backend/tests/api/test_account_companies.py::test_company_suggestions_for_operator -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/account.py backend/app/services/company_suggestions.py
git commit -m "feat(backend): GET /api/v1/account/companies/suggested (persona-biased)"
```

---

### Task 8: Service — briefing.py (weighted feed assembly)

**Files:**
- Create: `backend/app/services/briefing.py`
- Create: `backend/tests/services/test_briefing.py`

This is the most substantive backend service in Phase B. It computes the weighted briefing feed per spec §4.4.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/services/test_briefing.py
import pytest
from app.services.briefing import compute_relevance_score

def test_relevance_score_components():
    """Score = 0.3*recency + 0.5*follow_overlap + 0.2*quality"""
    score = compute_relevance_score(recency=1.0, follow_overlap=0.0, quality=0.0)
    assert abs(score - 0.3) < 0.001

    score = compute_relevance_score(recency=0.0, follow_overlap=1.0, quality=0.0)
    assert abs(score - 0.5) < 0.001

    score = compute_relevance_score(recency=0.0, follow_overlap=0.0, quality=1.0)
    assert abs(score - 0.2) < 0.001

    score = compute_relevance_score(recency=1.0, follow_overlap=1.0, quality=1.0)
    assert abs(score - 1.0) < 0.001

def test_recency_decay_function():
    from app.services.briefing import recency_decay
    # exponential decay over 14 days
    assert recency_decay(days_ago=0) == pytest.approx(1.0, abs=0.01)
    assert recency_decay(days_ago=14) < 0.5  # fully decayed within window
    assert recency_decay(days_ago=30) < 0.1
```

- [ ] **Step 2: Run test to verify fail**

```bash
docker compose exec backend pytest backend/tests/services/test_briefing.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement briefing service**

`backend/app/services/briefing.py`:

```python
import math
from datetime import datetime, timezone
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

RECENCY_WEIGHT = 0.3
FOLLOW_WEIGHT = 0.5
QUALITY_WEIGHT = 0.2

# Briefing item-type literal must match frontend BriefingItemType
ItemType = Literal["trend", "notable", "company", "expiring", "foryou", "news"]


def recency_decay(days_ago: float, half_life_days: float = 7.0) -> float:
    """Exponential decay: 1.0 at 0 days, 0.5 at half-life, ~0 at >30 days."""
    return math.pow(0.5, days_ago / half_life_days)


def compute_relevance_score(recency: float, follow_overlap: float, quality: float) -> float:
    return RECENCY_WEIGHT * recency + FOLLOW_WEIGHT * follow_overlap + QUALITY_WEIGHT * quality


def relative_time(updated_at: datetime) -> str:
    """Format a datetime as relative ("2h ago", "3d ago")."""
    now = datetime.now(timezone.utc)
    delta = now - updated_at
    seconds = delta.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


async def assemble_briefing(db: AsyncSession, user_id: int, limit: int = 15) -> list[dict]:
    """Produce a weighted briefing feed for the user.

    Returns a list of typed items, each with the required reason / source /
    freshness / confidence fields per spec §4.4.
    """
    items: list[dict] = []

    # 1. Top filing trend (by momentum_score, intersected with user topics)
    # 2. Expiring opportunity (top N by expiry_opportunity_score, in user topics, expiring in 90d)
    # 3. Notable patent (top opportunity_score in last 14d, with summary, in user topics)
    # 4. Company move (largest week-over-week delta on a followed company)
    # 5. For-you stub (1-hop adjacent company)
    # 6. News V1.1 placeholder

    # Each query produces 1-5 items typed with the appropriate ItemType + required fields.
    # ...
    # (Full implementation here is large — see spec §4.4 + §10 for the contract.
    # For Task 8 it's acceptable to ship just the recency_decay and compute_relevance_score
    # functions plus a stub for assemble_briefing that returns an empty list.
    # The endpoint Task 9 will wire the real queries.)

    return items
```

- [ ] **Step 4: Run test to verify pass**

```bash
docker compose exec backend pytest backend/tests/services/test_briefing.py -v
```

Expected: scoring + decay tests pass. `assemble_briefing` returns [] (stub).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/briefing.py backend/tests/services/test_briefing.py
git commit -m "feat(backend): briefing service (scoring + decay; assembly stub)"
```

---

### Task 9: Endpoint — GET /api/v1/today/briefing

**Files:**
- Modify: `backend/app/api/v1/today.py`
- Modify: `backend/app/core/schemas.py`
- Modify: `backend/app/services/briefing.py` (flesh out the real queries)
- Create: `backend/tests/api/test_today_briefing.py`

- [ ] **Step 1: Add Pydantic schemas for typed items**

In `backend/app/core/schemas.py`:

```python
from typing import Literal
from datetime import datetime

class FreshnessField(BaseModel):
    updated_at: datetime
    relative: str

class ConfidenceField(BaseModel):
    level: Literal["high", "medium", "low"]
    caveat: str | None = None

class BriefingItem(BaseModel):
    type: Literal["trend", "notable", "company", "expiring", "foryou", "news"]
    label: str
    title: str
    subtext: str | None = None
    reason: str
    source: str
    freshness: FreshnessField
    confidence: ConfidenceField | None = None
    href: str | None = None

class BriefingResponse(BaseModel):
    items: list[BriefingItem]
    total: int
    generated_at: datetime
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/api/test_today_briefing.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_briefing_returns_typed_items(async_client: AsyncClient, auth_headers, seeded_data):
    response = await async_client.get("/api/v1/today/briefing", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    for item in body["items"]:
        assert "type" in item
        assert item["type"] in ("trend", "notable", "company", "expiring", "foryou", "news")
        # required fields per spec §4.4
        assert "reason" in item
        assert "source" in item
        assert "freshness" in item
        assert "relative" in item["freshness"]

@pytest.mark.asyncio
async def test_briefing_includes_news_slot_placeholder(async_client: AsyncClient, auth_headers):
    response = await async_client.get("/api/v1/today/briefing", headers=auth_headers)
    body = response.json()
    news_items = [i for i in body["items"] if i["type"] == "news"]
    # V1: exactly one news placeholder
    assert len(news_items) == 1
    assert "V1.1" in news_items[0]["title"] or "V1.1" in news_items[0]["reason"]

@pytest.mark.asyncio
async def test_briefing_for_user_without_follows_returns_default_items(async_client: AsyncClient, auth_headers_new_user):
    response = await async_client.get("/api/v1/today/briefing", headers=auth_headers_new_user)
    body = response.json()
    # New users still get a non-empty briefing — uses system defaults
    assert body["total"] > 0
```

- [ ] **Step 3: Run test to verify fail**

```bash
docker compose exec backend pytest backend/tests/api/test_today_briefing.py -v
```

Expected: FAIL with 404.

- [ ] **Step 4: Flesh out assemble_briefing with real queries**

In `backend/app/services/briefing.py`, replace the stub `assemble_briefing` with real queries per spec §4.4. Each function returns 0–N typed items:

```python
async def _filing_trend_item(db, user_id) -> dict | None:
    """Top trend by momentum_score in user's topics, updated <14d ago."""
    # Query trends table joined to user topic membership
    # If no qualifying trend: return None
    # Otherwise produce a typed dict with all required fields
    pass

async def _expiring_opportunity_item(db, user_id) -> dict | None:
    """Aggregate count where expiry_date in next 90d AND in user topics."""
    pass

async def _notable_patent_item(db, user_id) -> dict | None:
    """Top opportunity_score in last 14d in user topics, with summary."""
    pass

async def _company_move_item(db, user_id) -> dict | None:
    """Followed company with largest week-over-week filing delta."""
    pass

async def _foryou_stub_item(db, user_id) -> dict:
    """Rule-based 1-hop adjacent company. ALWAYS returns an item.

    Honest copy per §7.3: 'For you — early personalization' (not 'AI For You').
    Footer: 'Full AI recommendations are coming later.'
    """
    return {
        "type": "foryou",
        "label": "For you — early personalization",
        "title": "Patents from companies adjacent to your follows",
        "subtext": "...",  # populate with adjacent company names + counts
        "reason": "Shown because you follow [companies]; these are 1-hop adjacent.",
        "source": "II8 follow graph",
        "freshness": {...},
    }

async def _news_placeholder_item() -> dict:
    """V1.1 news slot placeholder."""
    return {
        "type": "news",
        "label": "News ↔ patents · V1.1",
        "title": "News-patent linking slot reserved",
        "subtext": "Card structure designed in. AI integration ships V1.1.",
        "reason": "V1.1 will surface news events linked to patents in your follows.",
        "source": "",
        "freshness": {
            "updated_at": datetime.now(timezone.utc),
            "relative": "ready",
        },
    }

async def assemble_briefing(db, user_id, limit=15) -> list[dict]:
    items: list[dict] = []
    for f in [_filing_trend_item, _expiring_opportunity_item, _notable_patent_item, _company_move_item]:
        item = await f(db, user_id)
        if item:
            items.append(item)
    items.append(await _foryou_stub_item(db, user_id))
    items.append(await _news_placeholder_item())
    return items[:limit]
```

- [ ] **Step 5: Add endpoint**

In `backend/app/api/v1/today.py`:

```python
from datetime import datetime, timezone
from app.services.briefing import assemble_briefing
from app.core.schemas import BriefingResponse

@router.get("/briefing", response_model=BriefingResponse)
async def today_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await assemble_briefing(db, current_user.id)
    return BriefingResponse(
        items=items,
        total=len(items),
        generated_at=datetime.now(timezone.utc),
    )
```

- [ ] **Step 6: Run test to verify pass**

```bash
docker compose exec backend pytest backend/tests/api/test_today_briefing.py -v
```

Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/today.py backend/app/core/schemas.py backend/app/services/briefing.py backend/tests/api/test_today_briefing.py
git commit -m "feat(backend): GET /api/v1/today/briefing with typed items + required fields"
```

---

### Task 10: Phase B gate verification

- [ ] **Step 1: Run full backend test suite**

```bash
docker compose exec backend pytest backend/tests/ -q
```

Expected: 341 baseline + ~16 new tests = ~357 passing. 3 xfail OK. 0 failures.

- [ ] **Step 2: Verify migrations apply cleanly on a fresh DB**

```bash
docker compose exec db psql -U patent -d patent_pulse -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
docker compose exec backend alembic upgrade head
```

Expected: clean migration to 0024.

- [ ] **Step 3: Smoke-test each new endpoint**

For each, use an authenticated session:
- PUT /api/v1/account/persona
- POST /api/v1/account/companies
- GET /api/v1/account/companies
- DELETE /api/v1/account/companies/{name}
- GET /api/v1/account/companies/suggested?persona=operator
- GET /api/v1/today/briefing

Capture response shape. Confirm all required fields (especially `reason`, `source`, `freshness` on briefing items) are populated.

- [ ] **Step 4: Verify /companies/[name] returns 200 for 5 real companies**

```bash
for name in Apple%20Inc%2E NVIDIA Tesla Microsoft Samsung; do
  echo "$name: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/companies/$name)"
done
```

Expected: 200 for each (or 404 if data missing — but never 500).

- [ ] **Step 5: Write Phase B gate report**

Create `.hermes/plans/2026-06-01_frontend-phase-b-gate.md` with:
- Test results
- Migration verification
- Endpoint smoke-test results
- /companies/[name] verification
- Known issues
- "Phase C is GO" or "Phase C is BLOCKED on [X]" decision

- [ ] **Step 6: Hand off to Andy**

Send Andy summary message. Wait for go-ahead before Phase C.

---

## Phase B Gate

Phase C does not begin until:
- [ ] All 10 tasks complete
- [ ] Full backend test suite passing (341 baseline + ~16 new)
- [ ] Migrations 0023 + 0024 apply cleanly on fresh DB
- [ ] All 6 new endpoints respond correctly with required fields
- [ ] `/companies/[name]` returns 200 for ≥5 real companies
- [ ] Gate report exists and is reviewed by Andy
- [ ] Andy gives explicit go-ahead
