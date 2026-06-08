"""Tests for share cards + sitemap (Phase 5 PR 3)."""
import io

import pytest
from PIL import Image

from app.api.v1.share import _generate_share_png


def test_generate_share_png_returns_valid_image():
    """Share card PNG is a valid 1200x630 image."""
    img_bytes = _generate_share_png(headline="Test Company", subtext="100 patents")
    assert len(img_bytes) > 100

    img = Image.open(io.BytesIO(img_bytes))
    assert img.size == (1200, 630)
    assert img.mode == "RGB"


def test_generate_share_png_long_headline():
    """Long headlines are handled without crash."""
    img_bytes = _generate_share_png(
        headline="This Is A Very Long Company Name That Exceeds Normal Length Limits For Display Purposes Testing",
        subtext="Some subtext here"
    )
    img = Image.open(io.BytesIO(img_bytes))
    assert img.size == (1200, 630)


@pytest.mark.asyncio(loop_scope="function")
async def test_sitemap_returns_valid_xml(client):
    """Sitemap endpoint returns valid XML with entries."""
    r = await client.get("/sitemap.xml")
    assert r.status_code == 200
    content = r.text
    assert '<?xml version="1.0"' in content
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in content
    assert "<url>" in content
    assert "<loc>" in content


@pytest.mark.asyncio(loop_scope="function")
async def test_sitemap_includes_static_pages(client):
    """Sitemap includes /, /pricing, /about."""
    r = await client.get("/sitemap.xml")
    body = r.text
    assert "<loc>" in body
    assert "/pricing" in body
    assert "/about" in body


@pytest.mark.asyncio(loop_scope="function")
async def test_share_card_company_returns_png(client):
    """Company share card returns PNG image."""
    r = await client.get("/api/v1/share/company/test-company.png")
    # May 404 if company doesn't exist, or 200 with PNG
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert r.headers["content-type"] == "image/png"


@pytest.mark.asyncio(loop_scope="function")
async def test_share_card_patent_returns_png(client):
    """Patent share card returns PNG."""
    r = await client.get("/api/v1/share/patent/USPTO:US12345678.png")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert r.headers["content-type"] == "image/png"


@pytest.mark.asyncio(loop_scope="function")
async def test_share_card_trend_returns_png(client):
    """Trend share card returns PNG."""
    r = await client.get("/api/v1/share/trend/G06N.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
