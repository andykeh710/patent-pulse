"""
WIPO PatentScope Client.

Implements patent data retrieval from WIPO PatentScope.
WIPO PCT publications are typically published on Thursdays.

IMPORTANT: WIPO PatentScope Terms of Use prohibit bulk scraping.
This client is designed for targeted discovery only, not bulk downloads.
https://www.wipo.int/patentscope/en/data/terms_patentscope.html

Rate limits:
- Respect robots.txt
- No more than 1 request per second
- Targeted queries only
"""

import logging
import time
from collections.abc import Iterator
from datetime import date, timedelta
from xml.etree import ElementTree

import httpx

from app.core.exceptions import IngestionError, TransientIngestionError

logger = logging.getLogger(__name__)

PATENTSCOPE_API_BASE = "https://patentscope.wipo.int/search/en"
REQUEST_DELAY_SECONDS = 1.0


class WIPOClient:
    """
    Client for fetching PCT patent data from WIPO PatentScope.

    Designed for targeted discovery of PCT applications, NOT bulk scraping.
    Always respect WIPO's Terms of Use.
    """

    def __init__(self):
        self._http_client = httpx.Client(timeout=30.0)
        self._last_request_time: float = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._http_client.close()

    def _throttle(self):
        """Ensure minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _request(
        self,
        path: str,
        params: dict | None = None,
    ) -> httpx.Response:
        """Make throttled request to PatentScope."""
        self._throttle()

        url = f"{PATENTSCOPE_API_BASE}{path}"

        try:
            response = self._http_client.get(url, params=params)
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise IngestionError(
                    "WIPO rate limit exceeded. Please reduce request frequency."
                ) from e
            if e.response.status_code in (500, 502, 503, 504):
                raise TransientIngestionError(f"WIPO server error: {e}") from e
            raise IngestionError(f"WIPO request failed: {e}") from e
        except httpx.RequestError as e:
            raise TransientIngestionError(f"WIPO connection error: {e}") from e

    def fetch_pct_publication(self, publication_number: str) -> dict:
        """
        Fetch data for a specific PCT publication.

        Args:
            publication_number: WO publication number (e.g., "WO2024001234")

        Returns:
            Parsed publication data
        """
        logger.info(f"Fetching PCT publication: {publication_number}")

        response = self._request(
            "/detail.jsf",
            params={"docId": publication_number, "format": "xml"},
        )

        return self._parse_pct_xml(response.text, publication_number)

    def search_pct_by_date(
        self,
        publication_date: date,
        max_results: int = 100,
    ) -> Iterator[dict]:
        """
        Search for PCT publications by date.

        Note: This is for targeted discovery only. Do not use for bulk scraping.

        Args:
            publication_date: Publication date to search
            max_results: Maximum number of results to return

        Yields:
            Basic publication metadata for further retrieval
        """
        date_str = publication_date.strftime("%Y-%m-%d")
        logger.info(f"Searching PCT publications for {publication_date}")

        response = self._request(
            "/search.jsf",
            params={
                "query": f"DP:{date_str}",
                "rows": min(max_results, 100),
                "format": "json",
            },
        )

        try:
            data = response.json()
            results = data.get("response", {}).get("docs", [])

            for doc in results:
                yield {
                    "publication_number": doc.get("applicationId", ""),
                    "title": doc.get("title", ""),
                    "applicants": doc.get("applicants", []),
                    "publication_date": doc.get("publicationDate", ""),
                    "ipc_codes": doc.get("ipcClasses", []),
                }

        except Exception as e:
            logger.warning(f"Failed to parse WIPO search results: {e}")

    def fetch_pct_by_week(
        self,
        week_date: date,
        max_results: int = 500,
    ) -> Iterator[dict]:
        """
        Fetch PCT publications for a specific week.

        Args:
            week_date: Any date in the target week (Thursday)
            max_results: Maximum total results

        Yields:
            Publication data dictionaries
        """
        thursday = get_last_thursday(week_date)

        count = 0
        for basic_info in self.search_pct_by_date(thursday, max_results):
            if count >= max_results:
                break

            pub_number = basic_info.get("publication_number")
            if pub_number:
                try:
                    full_data = self.fetch_pct_publication(pub_number)
                    full_data.update(basic_info)
                    yield full_data
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch {pub_number}: {e}")

    def _parse_pct_xml(self, xml_content: str, publication_number: str) -> dict:
        """Parse PCT publication XML to dictionary."""
        try:
            root = ElementTree.fromstring(xml_content)

            ns = {
                "wo": "http://www.wipo.int/standards/XMLSchema/ST96/Common",
                "pat": "http://www.wipo.int/standards/XMLSchema/ST96/Patent",
            }

            def find_text(xpath: str, default: str = "") -> str:
                elem = root.find(xpath, ns)
                return elem.text if elem is not None and elem.text else default

            def find_all_text(xpath: str) -> list[str]:
                return [elem.text for elem in root.findall(xpath, ns) if elem.text]

            return {
                "publication_number": publication_number,
                "application_number": find_text(".//pat:ApplicationNumber"),
                "filing_date": find_text(".//pat:ApplicationFilingDate"),
                "publication_date": find_text(".//pat:PublicationDate"),
                "title": find_text(".//pat:InventionTitle[@lang='EN']")
                or find_text(".//pat:InventionTitle"),
                "abstract": find_text(".//pat:Abstract[@lang='EN']")
                or find_text(".//pat:Abstract"),
                "applicants": [{"name": name} for name in find_all_text(".//pat:ApplicantName")],
                "inventors": [{"name": name} for name in find_all_text(".//pat:InventorName")],
                "ipc_codes": [{"code": code} for code in find_all_text(".//pat:IPCClassification")],
                "designated_states": find_all_text(".//pat:DesignatedState"),
                "priority_claims": self._extract_priority_claims(root, ns),
            }

        except ElementTree.ParseError as e:
            logger.warning(f"Failed to parse PCT XML for {publication_number}: {e}")
            return {
                "publication_number": publication_number,
                "parse_error": str(e),
            }

    def _extract_priority_claims(self, root: ElementTree.Element, ns: dict) -> list[dict]:
        """Extract priority claim information."""
        claims = []
        for claim in root.findall(".//pat:PriorityClaim", ns):
            country = claim.findtext("pat:PriorityCountry", "", ns)
            number = claim.findtext("pat:PriorityNumber", "", ns)
            date_elem = claim.findtext("pat:PriorityDate", "", ns)
            if number:
                claims.append(
                    {
                        "country": country,
                        "number": number,
                        "date": date_elem,
                    }
                )
        return claims


def get_last_thursday(reference_date: date | None = None) -> date:
    """Get the most recent Thursday before or on the reference date."""
    ref = reference_date or date.today()
    days_since_thursday = (ref.weekday() - 3) % 7
    return ref - timedelta(days=days_since_thursday)
