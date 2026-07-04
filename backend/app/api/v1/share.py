"""Phase 5 PR 3 — OG-image share cards + public sitemap."""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import text

from app.config import settings
from app.database import async_session_maker

logger = logging.getLogger(__name__)
router = APIRouter(tags=["share"])

# ── Share card generation ──────────────────────────────────────────


@router.get("/share/company/{normalized_name}.png")
async def share_card_company(normalized_name: str) -> Response:
    """Generate a 1200x630 OG-image PNG for a company."""
    async with async_session_maker() as session:
        row = (
            (
                await session.execute(
                    text("""
                SELECT assignee_val AS name, COUNT(*) AS patent_count
                FROM patent_publications p
                JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
                WHERE lower(assignee_val) = lower(:name)
                GROUP BY assignee_val
            """),
                    {"name": normalized_name},
                )
            )
            .mappings()
            .first()
        )

    display_name = normalized_name.replace("-", " ").title()
    count = row["patent_count"] if row else 0

    img_bytes = _generate_share_png(
        headline=f"{display_name}",
        subtext=f"{count:,} patents on Invention Index 8",
    )
    return Response(
        content=img_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/share/patent/{doc_id}.png")
async def share_card_patent(doc_id: str) -> Response:
    """Generate a 1200x630 OG-image PNG for a patent."""
    async with async_session_maker() as session:
        row = (
            (
                await session.execute(
                    text("""
                SELECT title, assignees
                FROM patent_publications
                WHERE doc_id = :doc_id
            """),
                    {"doc_id": doc_id},
                )
            )
            .mappings()
            .first()
        )

    title = row["title"] if row and row["title"] else doc_id
    assignee = (row["assignees"] or ["Unknown"])[0] if row else ""
    if len(title) > 80:
        title = title[:77] + "..."

    img_bytes = _generate_share_png(
        headline=title,
        subtext=f"Assignee: {assignee}" if assignee else "Patent on Invention Index 8",
    )
    return Response(
        content=img_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/share/trend/{cpc_prefix}.png")
async def share_card_trend(cpc_prefix: str) -> Response:
    """Generate a 1200x630 OG-image PNG for a CPC trend."""
    display_area = cpc_prefix.replace("-", " ").upper() if len(cpc_prefix) <= 8 else cpc_prefix[:8]

    img_bytes = _generate_share_png(
        headline=f"Patent Trend: {display_area}",
        subtext="Filing activity on Invention Index 8",
    )
    return Response(
        content=img_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"}
    )


def _generate_share_png(*, headline: str, subtext: str) -> bytes:
    """Generate a 1200x630 PNG share card with II8 branding."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#0B0E14")
    draw = ImageDraw.Draw(img)

    # Top-left logo
    draw.text((40, 40), "Invention Index 8", fill="#6B8CFF")

    # Headline (centered, bold)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_footer = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_footer = font_title

    # Word-wrap headline
    words = headline.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_title)
        if bbox[2] - bbox[0] > W - 80:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    y = 220
    for line in lines[:3]:  # Max 3 lines
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), line, fill="#F9FAFB", font=font_title)
        y += 60

    # Subtext
    bbox = draw.textbbox((0, 0), subtext, font=font_sub)
    sw = bbox[2] - bbox[0]
    draw.text(((W - sw) / 2, y + 20), subtext, fill="#9CA3AF", font=font_sub)

    # Bottom-right URL
    url = "inventionindex8.com"
    bbox = draw.textbbox((0, 0), url, font=font_footer)
    uw = bbox[2] - bbox[0]
    draw.text((W - uw - 40, H - 60), url, fill="#6B7280", font=font_footer)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Sitemap (index + sub-sitemaps) ─────────────────────────────────


MAX_SITEMAP_ENTRIES = 50_000
BASE_URL = settings.magic_link_base_url.rstrip("/")


async def _company_slugs(limit: int = MAX_SITEMAP_ENTRIES) -> list[str]:
    async with async_session_maker() as session:
        rows = (
            (
                await session.execute(
                    text("""
                SELECT DISTINCT lower(regexp_replace(assignee_val, '[^a-zA-Z0-9]', '-', 'g')) AS slug
                FROM patent_publications p
                JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
                WHERE assignee_val IS NOT NULL AND assignee_val != ''
                GROUP BY assignee_val
                ORDER BY COUNT(*) DESC
                LIMIT :limit
            """),
                    {"limit": limit},
                )
            )
            .mappings()
            .all()
        )
    return [r["slug"] for r in rows if r["slug"]]


async def _theme_slugs() -> list[str]:
    async with async_session_maker() as session:
        rows = (
            (
                await session.execute(
                    text("""
                SELECT regexp_replace(lower(name), '[^a-zA-Z0-9]+', '-', 'g') AS slug
                FROM themes
                WHERE is_active = true
                ORDER BY name
            """)
                )
            )
            .mappings()
            .all()
        )
    return [r["slug"] for r in rows if r["slug"]]


async def _top_patent_ids(limit: int = 5000) -> list[dict]:
    async with async_session_maker() as session:
        rows = (
            (
                await session.execute(
                    text("""
                SELECT id, doc_id
                FROM patent_publications
                WHERE opportunity_score IS NOT NULL
                ORDER BY opportunity_score DESC
                LIMIT :limit
            """),
                    {"limit": limit},
                )
            )
            .mappings()
            .all()
        )
    return [{"id": str(r["id"]), "doc_id": r["doc_id"]} for r in rows]


def _urlset_element(urls: list[dict]) -> Element:
    """Build a <urlset> with entries."""
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    urlset = Element("urlset", xmlns=ns)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for u in urls:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = u["loc"]
        SubElement(url_el, "lastmod").text = u.get("lastmod", today)
        chf = u.get("changefreq", "weekly")
        if chf:
            SubElement(url_el, "changefreq").text = chf
        pri = u.get("priority", "0.5")
        if pri:
            SubElement(url_el, "priority").text = pri

    return urlset


def _sitemap_response(urlset: Element) -> Response:
    xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(urlset, encoding="unicode").encode(
        "utf-8"
    )
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/sitemap.xml")
async def sitemap_index() -> Response:
    """Sitemap index pointing to sub-sitemaps."""
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    idx = Element("sitemapindex", xmlns=ns)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for name in ["companies", "themes", "patents", "pages"]:
        sm = SubElement(idx, "sitemap")
        SubElement(sm, "loc").text = f"{BASE_URL}/sitemap-{name}.xml"
        SubElement(sm, "lastmod").text = today

    return _sitemap_response(idx)


@router.get("/sitemap-companies.xml")
async def sitemap_companies() -> Response:
    slugs = await _company_slugs()
    urls = [{"loc": f"{BASE_URL}/c/{s}", "priority": "0.6"} for s in slugs]
    return _sitemap_response(_urlset_element(urls[:MAX_SITEMAP_ENTRIES]))


@router.get("/sitemap-themes.xml")
async def sitemap_themes() -> Response:
    slugs = await _theme_slugs()
    urls = [{"loc": f"{BASE_URL}/t/{s}", "priority": "0.5"} for s in slugs]
    return _sitemap_response(_urlset_element(urls[:MAX_SITEMAP_ENTRIES]))


@router.get("/sitemap-patents.xml")
async def sitemap_patents() -> Response:
    patents = await _top_patent_ids()
    urls = [{"loc": f"{BASE_URL}/patents/{p['id']}", "priority": "0.4"} for p in patents]
    return _sitemap_response(_urlset_element(urls[:MAX_SITEMAP_ENTRIES]))


@router.get("/sitemap-pages.xml")
async def sitemap_pages() -> Response:
    urls = [
        {"loc": f"{BASE_URL}/", "priority": "0.8", "changefreq": "daily"},
        {"loc": f"{BASE_URL}/pricing", "priority": "0.5"},
        {"loc": f"{BASE_URL}/about", "priority": "0.5"},
        {"loc": f"{BASE_URL}/terms", "priority": "0.3"},
        {"loc": f"{BASE_URL}/privacy", "priority": "0.3"},
        {"loc": f"{BASE_URL}/contact", "priority": "0.3"},
        {"loc": f"{BASE_URL}/refund", "priority": "0.3"},
    ]
    return _sitemap_response(_urlset_element(urls))


# ── robots.txt ─────────────────────────────────────────────────────


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt() -> Response:
    txt = f"""User-agent: *
Allow: /
Allow: /c/
Allow: /t/
Allow: /patents/
Allow: /trends/
Disallow: /admin/
Disallow: /account/
Disallow: /api/
Disallow: /login
Sitemap: {BASE_URL}/sitemap.xml
"""
    return Response(
        content=txt, media_type="text/plain", headers={"Cache-Control": "public, max-age=86400"}
    )
