"""USPTO patent figure fetcher — downloads patent PDFs and extracts page 1.

Source: patentimages.storage.googleapis.com (USPTO official image hosting).
This is a public government resource, not Google Patents scraping.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import fitz  # pymupdf
import httpx
from PIL import Image

logger = logging.getLogger(__name__)

USPTO_PDF_URL = "https://patentimages.storage.googleapis.com/pdfs/US{pub_num}.pdf"


def fetch_uspto_figures(publication_number: str, timeout: int = 30) -> list[dict[str, Any]]:
    """Fetch patent figures from USPTO's official image storage.

    Downloads the full patent PDF and extracts page 1 (the front page
    drawing). Returns a list of image metadata dicts compatible with
    the existing figure_fetcher pipeline.

    Args:
        publication_number: Clean numeric patent number (e.g. '8925299')
        timeout: HTTP request timeout in seconds.

    Returns:
        List of dicts with 'raw_bytes', 'source_url', 'figure_label'.
        Returns empty list on any failure.
    """
    # Clean the publication number — strip kind codes and prefixes
    clean_num = _clean_patent_number(publication_number)

    url = USPTO_PDF_URL.format(pub_num=clean_num)

    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        if r.status_code != 200 or len(r.content) < 1000:
            logger.debug("USPTO PDF %s: HTTP %d, len=%d", clean_num, r.status_code, len(r.content))
            return []
    except Exception as e:
        logger.debug("USPTO PDF download failed for %s: %s", clean_num, e)
        return []

    try:
        doc = fitz.open(stream=r.content, filetype="pdf")
        if doc.page_count == 0:
            doc.close()
            return []

        # Extract page 1 (representative drawing)
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        # Convert to PNG bytes
        buf = io.BytesIO()
        img.save(buf, "PNG")
        png_bytes = buf.getvalue()

        doc.close()

        return [
            {
                "raw_bytes": png_bytes,
                "source_url": url,
                "figure_label": f"US {clean_num} — page 1",
            }
        ]
    except Exception as e:
        logger.warning("USPTO PDF extraction failed for %s: %s", clean_num, e)
        return []


def _clean_patent_number(pub_num: str) -> str:
    """Extract clean numeric patent number from publication_number.

    Handles formats like:
        '8925299', 'US8925299B2', 'US 8,925,299 B2', 'US2024/0123456A1'
    """
    import re

    # Remove everything that isn't a digit
    digits = re.sub(r"[^0-9]", "", pub_num)
    return digits
