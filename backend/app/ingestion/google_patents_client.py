"""
Google Patents Scraper.

Fetches full patent text (abstract, claims, description) from Google Patents.
Google Patents provides free access to patent full text for most patent offices.

This is used as a supplementary data source when EPO OPS doesn't have claims/description
for US patents. EPO OPS remains the primary source for abstracts.

Rate limiting: We add delays between requests to be respectful.
"""

import logging
import re
import time

import httpx

logger = logging.getLogger(__name__)

GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"
REQUEST_TIMEOUT = 20
THROTTLE_DELAY = 1.0  # seconds between requests to be respectful


class GooglePatentsClient:
    """Scrapes patent full text from Google Patents."""

    def __init__(self):
        self._client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()

    def close(self):
        self._client.close()

    def fetch_patent_fulltext(
        self, publication_number: str, kind_code: str = "B2"
    ) -> dict:
        """
        Fetch abstract, claims, and description for a US patent from Google Patents.

        Args:
            publication_number: US publication number (e.g., "12586484")
            kind_code: Kind code (B1, B2 for grants; A1 for applications)

        Returns:
            Dict with 'abstract', 'claims_text', 'description_text' keys.
            Values are None if not found.
        """
        result = {
            "abstract": None,
            "claims_text": None,
            "description_text": None,
        }

        clean_number = publication_number.replace(",", "").strip()

        # Try the given kind code first, then fallback alternatives
        if kind_code and kind_code.startswith("B"):
            kind_codes_to_try = [kind_code, "B1", "B2"]
        elif kind_code and kind_code.startswith("A"):
            kind_codes_to_try = [kind_code, "A1", "A2"]
        else:
            kind_codes_to_try = ["B2", "B1", "A1"]

        # Deduplicate while preserving order
        seen = set()
        kind_codes_to_try = [
            k for k in kind_codes_to_try if not (k in seen or seen.add(k))
        ]

        html = None
        for kind in kind_codes_to_try:
            url = f"{GOOGLE_PATENTS_BASE}/US{clean_number}{kind}/en"
            try:
                response = self._client.get(url)
                if response.status_code == 200 and len(response.text) > 5000:
                    html = response.text
                    logger.debug(
                        f"Found patent US{clean_number}{kind} on Google Patents"
                    )
                    break
            except Exception as e:
                logger.debug(f"Error fetching US{clean_number}{kind}: {e}")
                continue

        if not html:
            logger.debug(f"Patent US{clean_number} not found on Google Patents")
            return result

        # Extract abstract
        result["abstract"] = self._extract_section(html, "abstract")

        # Extract claims
        result["claims_text"] = self._extract_section(html, "claims")

        # Extract description
        result["description_text"] = self._extract_section(html, "description")

        return result

    def _extract_section(self, html: str, section_name: str) -> str | None:
        """Extract a named section from Google Patents HTML."""
        pattern = rf'<section\s+itemprop="{section_name}"[^>]*>(.*?)</section>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            return None

        section_html = match.group(1)

        # Remove HTML tags but preserve paragraph breaks
        text = re.sub(r"<br\s*/?>", "\n", section_html)
        text = re.sub(r"</p>", "\n", text)
        text = re.sub(r"</div>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean up whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        text = text.strip()

        # Remove the section title if it starts with it (e.g., "Abstract\n\n...")
        title_pattern = rf"^{section_name}\s*\n+"
        text = re.sub(title_pattern, "", text, flags=re.IGNORECASE)
        text = text.strip()

        return text if text else None

    def fetch_batch(
        self, patents: list[tuple[str, str]], delay: float = THROTTLE_DELAY
    ) -> list[dict]:
        """
        Fetch full text for a batch of patents.

        Args:
            patents: List of (publication_number, kind_code) tuples
            delay: Seconds between requests

        Returns:
            List of result dicts, same order as input
        """
        results = []
        for pub_num, kind_code in patents:
            result = self.fetch_patent_fulltext(pub_num, kind_code)
            results.append(result)
            time.sleep(delay)
        return results
