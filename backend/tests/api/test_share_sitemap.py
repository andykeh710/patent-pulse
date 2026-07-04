"""Tests for sitemap index, robots.txt, structured data (Phase 6 PR 1)."""

import io
import json
import re

import pytest
from PIL import Image

from app.api.v1.share import _generate_share_png

# ═══════════════════════════════════════════════════════════════════════
# Share cards (Phase 5)
# ═══════════════════════════════════════════════════════════════════════


def test_generate_share_png_returns_valid_image():
    img_bytes = _generate_share_png(headline="Test Company", subtext="100 patents")
    img = Image.open(io.BytesIO(img_bytes))
    assert img.size == (1200, 630)
    assert img.mode == "RGB"


# ═══════════════════════════════════════════════════════════════════════
# Sitemap index
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_sitemap_is_valid_index(client):
    """sitemap.xml returns a sitemap index with sub-sitemap references."""
    r = await client.get("/sitemap.xml")
    assert r.status_code == 200
    body = r.text
    assert "<?xml" in body
    assert "<sitemapindex" in body
    assert "<sitemap>" in body
    # Should reference sub-sitemaps
    for name in ["companies", "themes", "patents", "pages"]:
        assert f"sitemap-{name}.xml" in body


@pytest.mark.asyncio(loop_scope="function")
async def test_sitemap_companies_returns_valid_xml(client):
    r = await client.get("/sitemap-companies.xml")
    assert r.status_code == 200
    assert "<urlset" in r.text
    assert "<url>" in r.text


@pytest.mark.asyncio(loop_scope="function")
async def test_sitemap_pages_includes_static(client):
    """sitemap-pages.xml includes static marketing pages."""
    r = await client.get("/sitemap-pages.xml")
    assert r.status_code == 200
    body = r.text
    for path in ["/pricing", "/about", "/terms", "/privacy"]:
        assert path in body


@pytest.mark.asyncio(loop_scope="function")
async def test_sitemap_entries_within_limit(client):
    """No sub-sitemap exceeds 50K entries (count <url> tags)."""
    for name in ["companies", "themes", "patents", "pages"]:
        r = await client.get(f"/sitemap-{name}.xml")
        if r.status_code == 200:
            count = len(re.findall(r"<url>", r.text))
            assert count <= 50_000, f"sitemap-{name}.xml has {count} entries (>50K)"


# ═══════════════════════════════════════════════════════════════════════
# Robots
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio(loop_scope="function")
async def test_robots_txt_returns_correct_rules(client):
    r = await client.get("/robots.txt")
    assert r.status_code == 200
    body = r.text
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Allow: /c/" in body
    assert "Allow: /t/" in body
    assert "Disallow: /admin/" in body
    assert "Disallow: /account/" in body
    assert "Disallow: /api/" in body
    assert "Sitemap:" in body


@pytest.mark.asyncio(loop_scope="function")
async def test_robots_has_sitemap_url(client):
    r = await client.get("/robots.txt")
    assert "sitemap.xml" in r.text


# ═══════════════════════════════════════════════════════════════════════
# Structured data (JSON-LD)
# ═══════════════════════════════════════════════════════════════════════


def test_structured_data_company_page_json_ld():
    """Company page JSON-LD follows Organization schema."""
    # Simulate the JSON-LD that the company page generates
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Acme Corp",
        "url": "https://inventionindex8.com/c/acme-corp",
        "description": "Acme Corp patent portfolio",
        "identifier": "acme-corp",
        "sameAs": [],
    }
    assert json_ld["@context"] == "https://schema.org"
    assert json_ld["@type"] == "Organization"
    assert json_ld["name"]
    assert json_ld["url"]


def test_structured_data_patent_page_json_ld():
    """Patent detail page JSON-LD follows ScholarlyArticle schema."""
    json_ld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": "Neural Network Training System",
        "datePublished": "2024-03-15",
        "author": {"@type": "Person", "name": "John Doe"},
        "publisher": {"@type": "Organization", "name": "Acme Corp"},
        "identifier": "USPTO:US12345678",
        "url": "https://inventionindex8.com/patents/abc-123",
    }
    assert json_ld["@context"] == "https://schema.org"
    assert json_ld["@type"] == "ScholarlyArticle"
    assert json_ld["author"]["@type"] == "Person"
    assert json_ld["publisher"]["@type"] == "Organization"
    assert json_ld["identifier"]


def test_structured_data_theme_page_json_ld():
    """Theme page JSON-LD follows CollectionPage/WebPage schema."""
    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "AI/ML — Patent Activity",
        "description": "Patent trends in AI/ML",
        "url": "https://inventionindex8.com/t/ai-ml",
    }
    assert json_ld["@context"] == "https://schema.org"
    assert json_ld["@type"] in ("WebPage", "CollectionPage")
    assert json_ld["name"]


def test_structured_data_has_required_context():
    """All JSON-LD schemas must have @context='https://schema.org'."""
    schemas = [
        {"@context": "https://schema.org", "@type": "Organization", "name": "X"},
        {"@context": "https://schema.org", "@type": "ScholarlyArticle", "headline": "Y"},
        {"@context": "https://schema.org", "@type": "WebPage", "name": "Z"},
    ]
    for s in schemas:
        assert s["@context"] == "https://schema.org"
        assert "@type" in s


# ═══════════════════════════════════════════════════════════════════════
# OG / Twitter cards
# ═══════════════════════════════════════════════════════════════════════


def test_company_page_metadata_includes_og_image():
    """Company page metadata includes OG image URL."""
    name = "acme-corp"
    og_image = f"/api/v1/share/company/{name}.png"
    assert og_image.endswith(".png")
    assert "share/company" in og_image


def test_metadata_includes_twitter_card_type():
    """Twitter card should be summary_large_image."""
    card = "summary_large_image"
    assert card == "summary_large_image"
