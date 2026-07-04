"""Patent figure conversion — TIFF/GIF → PNG thumbnails via Pillow."""

from __future__ import annotations

import io
import logging
from typing import NamedTuple

from PIL import Image

logger = logging.getLogger(__name__)

THUMB_WIDTH = 320
FULL_MAX_WIDTH = 2000


class ConvertedFigure(NamedTuple):
    full_bytes: bytes
    thumb_bytes: bytes
    width: int
    height: int
    mime_type: str


def convert_figure(raw_bytes: bytes, source_format: str = "tiff") -> ConvertedFigure | None:
    """Convert raw figure bytes to full-size and thumbnail PNG.

    Args:
        raw_bytes: Raw image bytes from the patent office.
        source_format: Hint for Pillow ('tiff', 'gif', 'png', 'jpeg', None=auto).

    Returns:
        ConvertedFigure or None if conversion fails.
    """
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()
    except Exception:
        logger.warning("Failed to open figure image", exc_info=True)
        return None

    # Convert to RGB for safe PNG output (handles RGBA, P, L, CMYK)
    if img.mode not in ("RGB", "RGBA"):
        try:
            img = img.convert("RGB")
        except Exception:
            logger.warning("Failed to convert image mode %s", img.mode)
            return None

    orig_w, orig_h = img.size

    # Full size: cap at FULL_MAX_WIDTH
    if orig_w > FULL_MAX_WIDTH:
        ratio = FULL_MAX_WIDTH / orig_w
        full_img = img.resize((FULL_MAX_WIDTH, int(orig_h * ratio)), Image.Resampling.LANCZOS)
    else:
        full_img = img.copy()

    full_w, full_h = full_img.size

    # Thumbnail
    if full_w > THUMB_WIDTH:
        ratio = THUMB_WIDTH / full_w
        thumb_img = full_img.resize((THUMB_WIDTH, int(full_h * ratio)), Image.Resampling.LANCZOS)
    else:
        thumb_img = full_img.copy()

    # Encode both as PNG
    full_buf = io.BytesIO()
    thumb_buf = io.BytesIO()
    full_img.save(full_buf, format="PNG")
    thumb_img.save(thumb_buf, format="PNG")

    return ConvertedFigure(
        full_bytes=full_buf.getvalue(),
        thumb_bytes=thumb_buf.getvalue(),
        width=full_w,
        height=full_h,
        mime_type="image/png",
    )
