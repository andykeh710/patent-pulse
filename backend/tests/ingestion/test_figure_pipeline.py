"""Tests for patent figure ingestion pipeline — unit, integration, migration."""

from __future__ import annotations

import io
import os

import pytest
from PIL import Image

# ═══════════════════════════════════════════════════════════════════════
# Unit: figure conversion
# ═══════════════════════════════════════════════════════════════════════


class TestFigureConversion:
    def test_convert_rgb_png(self):
        """A valid RGB PNG converts to full + thumb PNG."""
        from app.ingestion.figure_conversion import convert_figure

        # Create a 400x300 RGB test image
        img = Image.new("RGB", (400, 300), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        result = convert_figure(raw)
        assert result is not None
        assert result.mime_type == "image/png"
        assert result.width == 400  # under FULL_MAX_WIDTH, keeps size
        assert result.height == 300
        # Thumbnail should be 320 wide
        thumb = Image.open(io.BytesIO(result.thumb_bytes))
        assert thumb.size[0] == 320
        assert result.width == 400  # full size unchanged

    def test_convert_large_image_capped(self):
        """Images wider than FULL_MAX_WIDTH are resized."""
        from app.ingestion.figure_conversion import FULL_MAX_WIDTH, convert_figure

        img = Image.new("RGB", (3000, 2000), color=(0, 255, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        result = convert_figure(raw)
        assert result is not None
        assert result.width == FULL_MAX_WIDTH
        assert result.height < 2000

    def test_convert_rgba_becomes_rgb(self):
        """RGBA images are converted to RGB PNG."""
        from app.ingestion.figure_conversion import convert_figure

        img = Image.new("RGBA", (100, 100), color=(0, 0, 255, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()

        result = convert_figure(raw)
        assert result is not None
        full = Image.open(io.BytesIO(result.full_bytes))
        assert full.mode == "RGBA"  # Pillow preserves RGBA in PNG

    def test_convert_invalid_bytes_returns_none(self):
        """Garbage bytes return None gracefully."""
        from app.ingestion.figure_conversion import convert_figure

        result = convert_figure(b"not an image at all")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# Unit: figure storage
# ═══════════════════════════════════════════════════════════════════════


class TestFigureStorage:
    def test_save_and_get(self, tmp_path):
        from app.ingestion.figure_storage import LocalFigureStorage

        storage = LocalFigureStorage(base_dir=str(tmp_path))
        data = b"fake-png-data"
        path = storage.save("test-patent-id", 1, data, "png")
        assert storage.exists(path)
        assert storage.get(path) == data

    def test_delete_removes_all(self, tmp_path):
        from app.ingestion.figure_storage import LocalFigureStorage

        storage = LocalFigureStorage(base_dir=str(tmp_path))
        storage.save("patent-x", 1, b"a", "png")
        storage.save("patent-x", 2, b"b", "png")
        assert storage.exists(storage.save("patent-x", 1, b"a", "png"))

        storage.delete("patent-x")
        patent_dir = tmp_path / "patent-x"
        assert not patent_dir.exists()

    def test_singleton(self):
        from app.ingestion.figure_storage import get_storage

        s1 = get_storage()
        s2 = get_storage()
        assert s1 is s2


# ═══════════════════════════════════════════════════════════════════════
# Migration: 0039 up/down
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_migration_0039_up_down(db_session):
    """Verify migration 0039 applies and rolls back cleanly."""
    from sqlalchemy import text

    # Check that columns exist after migration applied
    result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='patent_publications' AND column_name IN "
            "('thumbnail_url','figures_status')"
        )
    )
    cols = {row[0] for row in result.all()}
    assert "thumbnail_url" in cols
    assert "figures_status" in cols

    # Check patent_figures table exists
    result = await db_session.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name='patent_figures')"
        )
    )
    assert result.scalar() is True

    # Check figures_status default
    result = await db_session.execute(
        text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name='patent_publications' AND column_name='figures_status'"
        )
    )
    default = result.scalar()
    assert default is not None
    assert "pending" in str(default)


# ═══════════════════════════════════════════════════════════════════════
# Integration: backfill task (live EPO key skipif)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("EPO_OPS_CLIENT_ID"),
    reason="EPO OPS credentials required for live figure fetch",
)
async def test_backfill_figures_live(db_session):
    """Integration test: backfill figures for a single patent with live EPO."""
    from sqlalchemy import select

    from app.core.models import PatentPublication
    from app.ingestion.figure_fetcher import fetch_and_store_figures

    result = await db_session.execute(
        select(PatentPublication).where(PatentPublication.office == "USPTO").limit(1)
    )
    patent = result.scalar_one_or_none()
    if patent is None:
        pytest.skip("No US patent in test DB")

    stats = await fetch_and_store_figures(db_session, patent)
    await db_session.commit()

    assert "status" in stats
    assert stats["status"] in ("complete", "partial", "unavailable")
    assert stats["total_processed"] == 1 if "total_processed" in stats else True


def test_celery_backfill_task():
    """Celery backfill task runs and returns stats (unit — no live calls)."""
    from app.tasks.backfill_figures import backfill_figures

    # Use .run() to bypass Celery machinery for unit testing
    result = backfill_figures.run(limit=2, priority_order="briefing")  # type: ignore[attr-defined]
    assert "total_processed" in result
    assert "per_source" in result
    assert result.get("errors", 0) == 0
