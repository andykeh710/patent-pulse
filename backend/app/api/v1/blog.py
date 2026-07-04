"""Phase 6 PR 2 — Blog API (admin CRUD + public read + seed)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import current_user, get_db
from app.core.blog_models import BlogPost

logger = logging.getLogger(__name__)
router = APIRouter(tags=["blog"])

# ── schemas ──────────────────────────────────────────────────────


class BlogPostCreate(BaseModel):
    slug: str
    title: str
    subtitle: str | None = None
    excerpt: str | None = None
    content_markdown: str
    hero_image_url: str | None = None
    author_name: str
    author_role: str | None = None
    tags: list[str] = []
    related_patent_doc_ids: list[str] = []
    related_theme_slugs: list[str] = []
    related_company_names: list[str] = []


class BlogPostUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    excerpt: str | None = None
    content_markdown: str | None = None
    hero_image_url: str | None = None
    author_name: str | None = None
    author_role: str | None = None
    tags: list[str] | None = None
    related_patent_doc_ids: list[str] | None = None
    related_theme_slugs: list[str] | None = None
    related_company_names: list[str] | None = None


class BlogPostResponse(BaseModel):
    slug: str
    title: str
    subtitle: str | None = None
    excerpt: str | None = None
    content_markdown: str
    hero_image_url: str | None = None
    author_name: str
    author_role: str | None = None
    tags: list[str] = []
    related_patent_doc_ids: list[str] = []
    related_theme_slugs: list[str] = []
    related_company_names: list[str] = []
    published_at: str | None = None
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class BlogPostListItem(BaseModel):
    slug: str
    title: str
    subtitle: str | None = None
    excerpt: str | None = None
    hero_image_url: str | None = None
    author_name: str
    tags: list[str] = []
    published_at: str | None = None
    status: str


# ── public endpoints ─────────────────────────────────────────────


@router.get("", response_model=list[BlogPostListItem])
async def list_blog_posts() -> list[BlogPostListItem]:
    """Public: list published posts, newest first."""
    async for db in get_db():
        rows = (
            (
                await db.execute(
                    select(BlogPost)
                    .where(BlogPost.status == "published")
                    .order_by(BlogPost.published_at.desc())
                    .limit(50)
                )
            )
            .scalars()
            .all()
        )
        return [
            BlogPostListItem(
                slug=r.slug,
                title=r.title,
                subtitle=r.subtitle,
                excerpt=r.excerpt,
                hero_image_url=r.hero_image_url,
                author_name=r.author_name,
                tags=r.tags or [],
                published_at=r.published_at.isoformat() if r.published_at else None,
                status=r.status,
            )
            for r in rows
        ]
    return []


@router.get("/{slug}", response_model=BlogPostResponse)
async def get_blog_post(slug: str) -> BlogPostResponse:
    """Public: get a single published post by slug."""
    async for db in get_db():
        row = (
            await db.execute(
                select(BlogPost).where(BlogPost.slug == slug, BlogPost.status == "published")
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(404, "Post not found")
        return BlogPostResponse(
            slug=row.slug,
            title=row.title,
            subtitle=row.subtitle,
            excerpt=row.excerpt,
            content_markdown=row.content_markdown,
            hero_image_url=row.hero_image_url,
            author_name=row.author_name,
            author_role=row.author_role,
            tags=row.tags or [],
            related_patent_doc_ids=row.related_patent_doc_ids or [],
            related_theme_slugs=row.related_theme_slugs or [],
            related_company_names=row.related_company_names or [],
            published_at=row.published_at.isoformat() if row.published_at else None,
            status=row.status,
            created_at=row.created_at.isoformat(),
        )
    raise HTTPException(404, "Post not found")


# ── admin endpoints ──────────────────────────────────────────────


async def _require_admin(user_id: str, db):
    from app.core.ai_models import User

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_admin:
        raise HTTPException(403, "Admin required")
    return user


@router.post("", response_model=BlogPostResponse)
async def admin_create_post(
    body: BlogPostCreate,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    await _require_admin(user_id, db)

    existing = (
        await db.execute(select(BlogPost).where(BlogPost.slug == body.slug))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Slug '{body.slug}' already exists")

    post = BlogPost(
        slug=body.slug,
        title=body.title,
        subtitle=body.subtitle,
        excerpt=body.excerpt,
        content_markdown=body.content_markdown,
        hero_image_url=body.hero_image_url,
        author_name=body.author_name,
        author_role=body.author_role,
        tags=body.tags,
        related_patent_doc_ids=body.related_patent_doc_ids,
        related_theme_slugs=body.related_theme_slugs,
        related_company_names=body.related_company_names,
        status="draft",
    )
    db.add(post)
    await db.commit()
    return BlogPostResponse(
        slug=post.slug,
        title=post.title,
        subtitle=post.subtitle,
        excerpt=post.excerpt,
        content_markdown=post.content_markdown,
        hero_image_url=post.hero_image_url,
        author_name=post.author_name,
        author_role=post.author_role,
        tags=post.tags or [],
        related_patent_doc_ids=post.related_patent_doc_ids or [],
        related_theme_slugs=post.related_theme_slugs or [],
        related_company_names=post.related_company_names or [],
        published_at=None,
        status=post.status,
        created_at=post.created_at.isoformat(),
    )


@router.patch("/{slug}", response_model=BlogPostResponse)
async def admin_update_post(
    slug: str,
    body: BlogPostUpdate,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    await _require_admin(user_id, db)

    post = (await db.execute(select(BlogPost).where(BlogPost.slug == slug))).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(post, field, val)
    post.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return BlogPostResponse(
        slug=post.slug,
        title=post.title,
        subtitle=post.subtitle,
        excerpt=post.excerpt,
        content_markdown=post.content_markdown,
        hero_image_url=post.hero_image_url,
        author_name=post.author_name,
        author_role=post.author_role,
        tags=post.tags or [],
        related_patent_doc_ids=post.related_patent_doc_ids or [],
        related_theme_slugs=post.related_theme_slugs or [],
        related_company_names=post.related_company_names or [],
        published_at=post.published_at.isoformat() if post.published_at else None,
        status=post.status,
        created_at=post.created_at.isoformat(),
    )


@router.post("/{slug}/publish", response_model=BlogPostResponse)
async def admin_publish_post(
    slug: str,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    await _require_admin(user_id, db)

    post = (await db.execute(select(BlogPost).where(BlogPost.slug == slug))).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    post.status = "published"
    post.published_at = datetime.now(timezone.utc)
    post.updated_at = post.published_at
    await db.commit()

    return BlogPostResponse(
        slug=post.slug,
        title=post.title,
        subtitle=post.subtitle,
        excerpt=post.excerpt,
        content_markdown=post.content_markdown,
        hero_image_url=post.hero_image_url,
        author_name=post.author_name,
        author_role=post.author_role,
        tags=post.tags or [],
        related_patent_doc_ids=post.related_patent_doc_ids or [],
        related_theme_slugs=post.related_theme_slugs or [],
        related_company_names=post.related_company_names or [],
        published_at=post.published_at.isoformat(),
        status=post.status,
        created_at=post.created_at.isoformat(),
    )


# ── seed from markdown files ─────────────────────────────────────


async def seed_blog_posts() -> int:
    """Load content/blog/*.md into blog_posts if not already present.
    Called at app startup. Returns count of posts seeded."""
    from pathlib import Path

    blog_dir = Path(__file__).resolve().parent.parent.parent.parent / "content" / "blog"
    if not blog_dir.exists():
        logger.info("No content/blog directory; skipping blog seed")
        return 0

    seeded = 0
    async for db in get_db():
        for md_file in sorted(blog_dir.glob("*.md")):
            content = md_file.read_text()
            slug = md_file.stem

            # Check if already exists
            existing = (
                await db.execute(select(BlogPost).where(BlogPost.slug == slug))
            ).scalar_one_or_none()
            if existing:
                continue

            # Parse frontmatter (simple YAML-like --- blocks)
            fm = _parse_frontmatter(content)
            if not fm or "title" not in fm:
                logger.warning("Skipping %s: no frontmatter", md_file)
                continue

            post = BlogPost(
                slug=slug,
                title=fm.get("title", slug),
                subtitle=fm.get("subtitle"),
                excerpt=fm.get("excerpt"),
                content_markdown=fm.get("body", content),
                hero_image_url=fm.get("hero_image_url"),
                author_name=fm.get("author_name", "Invention Index 8"),
                author_role=fm.get("author_role"),
                tags=fm.get("tags", []),
                related_patent_doc_ids=fm.get("related_patent_doc_ids", []),
                related_theme_slugs=fm.get("related_theme_slugs", []),
                related_company_names=fm.get("related_company_names", []),
                status=fm.get("status", "draft"),
            )
            db.add(post)
            seeded += 1
            logger.info("Seeded blog post: %s", slug)

        if seeded:
            await db.commit()
    return seeded


def _parse_frontmatter(text: str) -> dict | None:
    """Parse YAML-like frontmatter between --- markers (simple key: value)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return None
    fm_str = match.group(1)
    body = text[match.end() :]

    fm: dict = {}
    current_key = None
    current_list: list = []

    for line in fm_str.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # List continuation: - item
        if line.startswith("- ") and current_key:
            current_list.append(line[2:].strip().strip('"').strip("'"))
            continue

        # Key: value
        kv_match = re.match(r"^(\w[\w_]*):\s*(.*)", line)
        if kv_match:
            # Flush previous list
            if current_key and current_list:
                fm[current_key] = current_list
                current_list = []
            current_key = kv_match.group(1)
            val = kv_match.group(2).strip()

            # List start: [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
                fm[current_key] = items
                current_key = None
            elif val:
                fm[current_key] = val.strip('"').strip("'")
                current_key = None
            else:
                # Value on next lines
                pass

    # Flush final list
    if current_key and current_list:
        fm[current_key] = current_list

    fm["body"] = body.strip()
    return fm
