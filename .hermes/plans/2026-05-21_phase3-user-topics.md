# Phase 3 — User-Created Topics Implementation Plan

> **For Hermes:** Implement task-by-task. Verify at each step.

**Goal:** Extend the Theme system so users can create/manage their own topics with rich filtering (keywords, opportunity tags, score thresholds) while preserving the 8 CPC-section system themes. Rebrand frontend from "Themes" to "Topics".

**Architecture:** Extend `Theme` model with 4 new columns (keywords, opportunity_tags, min_opportunity_score, user_id). Update API schemas. Extend theme_matcher to use keywords. Add create/edit UI on frontend. Add 6 default topic packs. No new tables — themes and topics coexist in the same table, differentiated by user_id (NULL = system, non-NULL = user).

**Tech Stack:** Alembic migration, SQLAlchemy ORM, FastAPI/Pydantic, Next.js App Router, SWR.

**Key files to modify:**
- `backend/app/core/theme_models.py` — add columns to Theme
- `backend/alembic/versions/0005_add_topic_fields.py` — new migration
- `backend/app/api/v1/themes.py` — update schemas + add create/update support
- `backend/app/api/v1/admin.py` — add default topic packs to seed
- `backend/app/tasks/theme_matcher.py` — extend matching to use keywords
- `frontend/src/lib/types.ts` — add Topic type
- `frontend/src/lib/api.ts` — add topicsApi
- `frontend/src/hooks/useThemes.ts` — add create/update hooks
- `frontend/src/app/themes/page.tsx` — add create/edit UI, rename to Topics
- `frontend/src/app/NavSidebar.tsx` — rename Themes → Topics

---

## Task 1: Create DB migration for new topic fields

**Objective:** Add keywords, opportunity_tags, min_opportunity_score, user_id columns to themes table.

**Files:**
- Create: `backend/alembic/versions/0005_add_topic_fields.py`

**Step 1: Create migration**

```bash
cd backend && alembic revision -m "add_topic_fields" --autogenerate
```

OR write it manually since autogenerate sometimes misses things:

```python
"""add_topic_fields

Revision ID: 0005
Revises: 0004
Create Date: 2024-05-21

Add keywords, opportunity_tags, min_opportunity_score, user_id to themes table
to support user-created topics alongside system themes.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("themes", sa.Column("keywords", sa.JSON(), nullable=True))
    op.add_column("themes", sa.Column("opportunity_tags", sa.JSON(), nullable=True))
    op.add_column("themes", sa.Column("min_opportunity_score", sa.Float(), nullable=True))
    op.add_column("themes", sa.Column("user_id", sa.String(64), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("themes", "user_id")
    op.drop_column("themes", "min_opportunity_score")
    op.drop_column("themes", "opportunity_tags")
    op.drop_column("themes", "keywords")
```

**Step 2: Run migration**

```bash
cd backend && alembic upgrade head
```
Expected: "Running upgrade 0004 -> 0005"

**Step 3: Verify columns exist**

```bash
cd backend && python -c "
from app.core.theme_models import Theme
print([c.name for c in Theme.__table__.columns])
"
```
Expected: list includes 'keywords', 'opportunity_tags', 'min_opportunity_score', 'user_id'

---

## Task 2: Update Theme model with new columns

**Objective:** Add the new fields to the SQLAlchemy Theme model.

**Files:**
- Modify: `backend/app/core/theme_models.py`

**Step 1: Add columns to Theme class**

Add after `title_keywords` line and before `is_active`:

```python
    # Topic fields (for user-created topics; NULL for system themes)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    opportunity_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    min_opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, default=None
    )
```

**Step 2: Verify model loads**

```bash
cd backend && python -c "from app.core.theme_models import Theme; print('OK')"
```
Expected: no import errors

---

## Task 3: Update themes API schemas (backend)

**Objective:** Add new fields to Pydantic schemas for create/update/response.

**Files:**
- Modify: `backend/app/api/v1/themes.py`

**Step 1: Update ThemeCreate**

```python
class ThemeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    cpc_prefixes: list[str] = []
    assignee_keywords: list[str] = []
    title_keywords: list[str] = []
    keywords: list[str] | None = None
    opportunity_tags: list[str] | None = None
    min_opportunity_score: float | None = None
    user_id: str | None = None
```

**Step 2: Update ThemeUpdate**

```python
class ThemeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cpc_prefixes: list[str] | None = None
    assignee_keywords: list[str] | None = None
    title_keywords: list[str] | None = None
    keywords: list[str] | None = None
    opportunity_tags: list[str] | None = None
    min_opportunity_score: float | None = None
    is_active: bool | None = None
```

**Step 3: Update ThemeResponse**

```python
class ThemeResponse(BaseModel):
    id: str
    name: str
    description: str | None
    cpc_prefixes: list[str]
    assignee_keywords: list[str]
    title_keywords: list[str]
    keywords: list[str] | None
    opportunity_tags: list[str] | None
    min_opportunity_score: float | None
    user_id: str | None
    is_active: bool
    patent_count: int
    created_at: str
```

**Step 4: Update create_theme endpoint** to pass new fields:

In the Theme(...) constructor call, add:
```python
    keywords=theme_data.keywords,
    opportunity_tags=theme_data.opportunity_tags,
    min_opportunity_score=theme_data.min_opportunity_score,
    user_id=theme_data.user_id or "anonymous",
```

**Step 5: Update all response builders** (list_themes, get_theme, update_theme, create_theme) to include:

```python
    keywords=theme.keywords or [],
    opportunity_tags=theme.opportunity_tags or [],
    min_opportunity_score=theme.min_opportunity_score,
    user_id=theme.user_id,
```

**Step 6: Verify**

```bash
cd backend && python -c "from app.api.v1.themes import ThemeCreate, ThemeUpdate, ThemeResponse; print('Schemas OK')"
```

---

## Task 4: Add default topic packs to seed-themes

**Objective:** Extend seed-themes endpoint to also seed 6 user-ready topic packs.

**Files:**
- Modify: `backend/app/api/v1/admin.py`

**Step 1: Add DEFAULT_TOPICS list** (after DEFAULT_THEMES)

```python
DEFAULT_TOPICS = [
    {
        "name": "AI Agents & LLMs",
        "description": "Autonomous agents, large language models, RAG, prompt engineering, multi-agent systems",
        "cpc_prefixes": ["G06N", "G06F"],
        "keywords": ["agent", "LLM", "large language model", "prompt", "retrieval augmented", "multi-agent", "autonomous", "reasoning"],
        "opportunity_tags": ["startup", "enterprise", "cross_industry"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Robotics & Automation",
        "description": "Industrial robots, autonomous vehicles, manipulation, perception, human-robot interaction",
        "cpc_prefixes": ["B25J", "G05D", "G05B"],
        "keywords": ["robot", "autonomous", "manipulation", "gripper", "end effector", "SLAM", "path planning", "human-robot"],
        "opportunity_tags": ["enterprise", "revival"],
        "min_opportunity_score": 25,
    },
    {
        "name": "Climate Tech",
        "description": "Carbon capture, renewable energy, energy storage, green materials, climate adaptation",
        "cpc_prefixes": ["Y02E", "Y02C", "Y02P", "B01D"],
        "keywords": ["carbon capture", "renewable", "solar", "wind", "battery", "energy storage", "hydrogen", "decarbonization"],
        "opportunity_tags": ["sustainability", "startup"],
        "min_opportunity_score": 25,
    },
    {
        "name": "Battery Technology",
        "description": "Lithium-ion, solid-state, sodium-ion, flow batteries, battery management systems",
        "cpc_prefixes": ["H01M", "H02J"],
        "keywords": ["lithium", "solid state", "sodium ion", "cathode", "anode", "electrolyte", "BMS", "thermal runaway"],
        "opportunity_tags": ["enterprise", "sustainability"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Biotech & Gene Therapy",
        "description": "CRISPR, mRNA, cell therapy, gene editing, protein engineering, precision medicine",
        "cpc_prefixes": ["C12N", "C07K", "A61K"],
        "keywords": ["CRISPR", "mRNA", "gene therapy", "cell therapy", "CAR-T", "protein engineering", "monoclonal antibody"],
        "opportunity_tags": ["startup", "revival"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Quantum Computing",
        "description": "Quantum processors, error correction, quantum algorithms, quantum networking, quantum sensing",
        "cpc_prefixes": ["G06N", "H01L"],
        "keywords": ["quantum", "qubit", "superconducting", "trapped ion", "quantum error", "quantum annealing", "entanglement"],
        "opportunity_tags": ["cross_industry", "startup"],
        "min_opportunity_score": 25,
    },
]
```

**Step 2: Add seeding in seed_themes endpoint**

After seeding DEFAULT_THEMES, also seed DEFAULT_TOPICS:

```python
    # Seed default topic packs
    for topic_data in DEFAULT_TOPICS:
        name = topic_data["name"]
        result = await db.execute(select(Theme).where(Theme.name == name))
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
        else:
            theme = Theme(
                name=name,
                description=topic_data["description"],
                cpc_prefixes=topic_data["cpc_prefixes"],
                keywords=topic_data.get("keywords"),
                opportunity_tags=topic_data.get("opportunity_tags"),
                min_opportunity_score=topic_data.get("min_opportunity_score"),
                user_id="default_pack",
            )
            db.add(theme)
            created += 1
```

---

## Task 5: Extend theme matcher to use keywords field

**Objective:** The matching logic should also check `keywords` against patent titles and abstracts.

**Files:**
- Modify: `backend/app/tasks/theme_matcher.py`

**Step 1: In `_match_single_theme`, add keyword matching conditions**

After the `title_keywords` block, add:

```python
    if theme.keywords:
        for keyword in theme.keywords:
            conditions.append(PatentPublication.title.ilike(f"%{keyword}%"))
            conditions.append(
                func.coalesce(PatentPublication.abstract, "").ilike(f"%{keyword}%")
            )
```

**Step 2: In `_calculate_match_score`, add keyword scoring**

After the `title_keywords` block, add:

```python
    if theme.keywords and patent.title:
        title_lower = patent.title.lower()
        abstract_lower = (patent.abstract or "").lower()
        for keyword in theme.keywords:
            kw = keyword.lower()
            if kw in title_lower:
                score += 0.3
                reasons.append(f"Keyword(title): {keyword}")
            elif kw in abstract_lower:
                score += 0.15
                reasons.append(f"Keyword(abstract): {keyword}")
```

**Step 3: Also handle opportunity_tags filter** (optional, for later use)

Not strictly necessary for matching — opportunity_tags are for frontend filtering.

---

## Task 6: Update frontend types for Topics

**Objective:** Add new Topic type and update API client.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

**Step 1: Replace Theme interface with Topic**

```ts
export interface Topic {
  id: string;
  name: string;
  description: string | null;
  cpc_prefixes: string[];
  assignee_keywords: string[];
  title_keywords: string[];
  keywords: string[] | null;
  opportunity_tags: string[] | null;
  min_opportunity_score: number | null;
  user_id: string | null;
  is_active: boolean;
  patent_count: number;
  created_at: string;
}
```

Keep Theme as alias for backward compat: `export type Theme = Topic;`

**Step 2: Add TopicCreate type**

```ts
export interface TopicCreate {
  name: string;
  description?: string;
  cpc_prefixes?: string[];
  assignee_keywords?: string[];
  title_keywords?: string[];
  keywords?: string[];
  opportunity_tags?: string[];
  min_opportunity_score?: number;
}
```

**Step 3: Add topicsApi to api.ts**

```ts
export const topicsApi = {
  list: () => apiFetch<Topic[]>(`/api/v1/themes`),
  create: (data: TopicCreate) =>
    apiFetch<Topic>(`/api/v1/themes`, { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<TopicCreate & { is_active: boolean }>) =>
    apiFetch<Topic>(`/api/v1/themes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/api/v1/themes/${id}`, { method: "DELETE" }),
  getPatents: (id: string, params: { page?: number; page_size?: number } = {}) =>
    apiFetch<PaginatedResponse<PatentListItem>>(
      `/api/v1/themes/${id}/patents?${toQueryString(params)}`
    ),
  getStats: (id: string) =>
    apiFetch<{ total_matches: number; avg_score: number; top_assignees: string[]; recent_matches: number }>(
      `/api/v1/themes/${id}/stats`
    ),
};
```

Keep `themesApi` as alias: `export const themesApi = topicsApi;`

---

## Task 7: Add create/edit topic UI to the themes page

**Objective:** Rebuild `/themes` page with create topic form, delete buttons for user topics, and improved layout.

**Files:**
- Modify: `frontend/src/app/themes/page.tsx`
- Modify: `frontend/src/hooks/useThemes.ts` (add mutate)

**Step 1: Add create topic modal/form**

Add state for showing a create form with fields: name, description, CPC prefixes (comma-separated), keywords (comma-separated). Submit calls `topicsApi.create()`.

**Step 2: Add delete button for user topics**

Only show delete on topics where `user_id` is not null (skip system themes).

**Step 3: Update hooks**

Add `useCreateTopic` and use SWR's `mutate` to refresh list after create/delete.

---

## Task 8: Rename nav from "Themes" to "Topics"

**Objective:** Update sidebar label.

**Files:**
- Modify: `frontend/src/app/NavSidebar.tsx`

**Step 1: Change label**

```ts
{ href: "/themes", label: "Topics" }
```

(Keep the route `/themes` for backward compatibility — we can alias later.)

---

## Task 9: Update Today page to link to topics

**Files:**
- Modify: `frontend/src/app/today/page.tsx`

**Step 1: Update the "Your Patent Pulse" placeholder**

Replace the static text with a link to create topics:

```tsx
<p className="text-sm text-gray-600 mt-1">
  <Link href="/themes" className="text-primary-600 hover:underline">
    Create topics
  </Link>{" "}
  to track technology areas that matter to you. Matched patents and trend signals
  will appear here automatically.
</p>
```

---

## Task 10: Backend tests for topics API

**Objective:** Add test coverage for the extended themes/topics API.

**Files:**
- Create: `backend/tests/api/test_themes.py`

**Step 1: Write test file** covering:
- List themes (includes both system + user topics)
- Create topic with keywords
- Get topic by ID
- Update topic
- Delete topic
- Delete fails for nonexistent topic
- Create fails for duplicate name

**Step 2: Run tests**

```bash
cd backend && python -m pytest tests/api/test_themes.py -v
```

---

## Task 11: Full verification

**Step 1: Backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: 136+ tests pass (existing + new)

**Step 2: Frontend build**

```bash
cd frontend && npm run build
```

Expected: 0 errors

**Step 3: Migration rollback test**

```bash
cd backend && alembic downgrade -1 && alembic upgrade head
```

---

## Verification Checklist

- [ ] Migration 0005 runs cleanly (up and down)
- [ ] Theme model has all 4 new columns
- [ ] API returns keywords/opportunity_tags/min_opportunity_score/user_id in responses
- [ ] API accepts new fields in create/update
- [ ] Seed-themes creates 6 default topic packs
- [ ] Theme matcher uses keywords for matching
- [ ] Frontend types updated
- [ ] Create topic UI works
- [ ] Delete user topic works (system themes not deletable from UI)
- [ ] Nav label says "Topics"
- [ ] Today page links to topics
- [ ] Backend tests pass (136+)
- [ ] Frontend build passes
