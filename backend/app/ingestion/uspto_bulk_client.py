"""
USPTO bulk data client for weekly patent XML ingestion.

Fetches official USPTO weekly grant and application publications from
the USPTO Open Data Portal (ODP) / bulk data service.

Sources:
- Grants: https://bulkdata.uspto.gov/data/patent/grant/redbook/full/{year}/
  Weekly files: ipg{MMDD}{YYYY}.zip containing XML
  Published every Tuesday.

- Applications: https://bulkdata.uspto.gov/data/patent/application/redbook/full/{year}/
  Weekly files: ipa{MMDD}{YYYY}.zip containing XML
  Published every Thursday.

When the bulkdata DNS is unavailable, falls back to ODP IBD API:
- https://developer.uspto.gov/ibd-api/v1/
  Requires USPTO_ODP_API_KEY.

The client handles XML parsing, field extraction, and normalization into
the standard patent data dictionary format used by USPTONormalizer.
"""

import logging
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from datetime import date
from io import BytesIO
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# XML namespaces used in USPTO bulk data
NS = {
    "us": "http://www.wipo.int/standards/XMLSchema/ST96/Patent",
    "com": "http://www.wipo.int/standards/XMLSchema/ST96/Common",
    "pat": "http://www.wipo.int/standards/XMLSchema/ST96/Patent",
}


def _ns(tag: str) -> str:
    """Resolve namespace-prefixed tag. Returns the tag unchanged if no ns."""
    if ":" not in tag:
        return tag
    prefix, local = tag.split(":", 1)
    uri = NS.get(prefix, "")
    return f"{{{uri}}}{local}" if uri else tag


class USPTOBulkClient:
    """
    Client for fetching USPTO weekly patent publications from bulk data.

    Supports:
    - Direct ZIP download from bulkdata.uspto.gov
    - ODP IBD API as fallback (developer.uspto.gov/ibd-api)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or getattr(settings, "uspto_odp_api_key", None)
        self.base_url = (
            base_url
            or getattr(settings, "uspto_odp_base_url", None)
            or "https://developer.uspto.gov/ibd-api/v1"
        )
        self.bulk_url = "https://bulkdata.uspto.gov/data/patent"

    def fetch_grant_week(self, issue_date: date) -> Iterator[dict[str, Any]]:
        """
        Fetch all patent grants for a given issue week.

        Args:
            issue_date: The grant issue date (typically a Tuesday)

        Yields:
            Raw patent data dictionaries
        """
        logger.info(f"Fetching USPTO grant week for {issue_date}")
        xml_content = self._download_week("grant", issue_date)
        if xml_content:
            yield from self._parse_grant_xml(xml_content)
        else:
            logger.warning(f"No grant data for week of {issue_date}")

    def fetch_application_week(self, pub_date: date) -> Iterator[dict[str, Any]]:
        """
        Fetch all published applications for a given publication week.

        Args:
            pub_date: The application publication date (typically a Thursday)

        Yields:
            Raw patent data dictionaries
        """
        logger.info(f"Fetching USPTO application week for {pub_date}")
        xml_content = self._download_week("application", pub_date)
        if xml_content:
            yield from self._parse_application_xml(xml_content)
        else:
            logger.warning(f"No application data for week of {pub_date}")

    def _download_week(self, kind: str, target_date: date) -> bytes | None:
        """
        Download the weekly XML ZIP for a given kind and date.

        Tries bulkdata.uspto.gov first, then ODP IBD API.
        """
        year = target_date.year
        date_str = target_date.strftime("%m%d%Y")

        if kind == "grant":
            url = f"{self.bulk_url}/grant/redbook/full/{year}/ipg{date_str}.zip"
        else:
            url = f"{self.bulk_url}/application/redbook/full/{year}/ipa{date_str}.zip"

        # Try bulkdata first
        try:
            logger.info(f"Downloading {url}")
            r = httpx.get(url, timeout=120, follow_redirects=True)
            if r.status_code == 200 and len(r.content) > 100:
                logger.info(f"Downloaded {len(r.content)} bytes from bulkdata")
                return r.content
            logger.warning(f"Bulkdata returned {r.status_code} len={len(r.content)}")
        except Exception as e:
            logger.warning(f"Bulkdata download failed: {e}")

        # Fallback to ODP IBD API
        try:
            odp_url = f"{self.base_url}/patent/{kind}s"
            params = {
                "dateFrom": target_date.isoformat(),
                "dateTo": target_date.isoformat(),
            }
            if self.api_key:
                params["api_key"] = self.api_key

            logger.info(f"Trying ODP: {odp_url}")
            r = httpx.get(odp_url, params=params, timeout=120)
            if r.status_code == 200 and len(r.content) > 100:
                logger.info(f"Downloaded {len(r.content)} bytes from ODP")
                return r.content
            logger.warning(f"ODP returned {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.warning(f"ODP download failed: {e}")

        return None

    def _parse_grant_xml(self, content: bytes) -> Iterator[dict[str, Any]]:
        """Parse USPTO grant XML content."""
        root = self._get_xml_root(content)
        if root is None:
            return

        for patent in root.iterfind(".//us:PatentGrant", NS) or root.iterfind(
            f".//{_ns('pat:PatentGrant')}"
        ):
            if patent is None:
                for patent in root.iterfind(".//PatentGrant"):
                    if patent is not None:
                        yield self._extract_patent_data(patent, kind_code="B2")
                        continue
                continue
            yield self._extract_patent_data(patent, kind_code="B2")

    def _parse_application_xml(self, content: bytes) -> Iterator[dict[str, Any]]:
        """Parse USPTO application XML content."""
        root = self._get_xml_root(content)
        if root is None:
            return

        for app in root.iterfind(".//us:PatentApplication") or root.iterfind(
            f".//{_ns('pat:PatentApplication')}"
        ):
            if app is None:
                for app in root.iterfind(".//PatentApplication"):
                    if app is not None:
                        yield self._extract_patent_data(app, kind_code="A1")
                        continue
                continue
            yield self._extract_patent_data(app, kind_code="A1")

    def _get_xml_root(self, content: bytes) -> ET.Element | None:
        """Get XML root element, handling ZIP wrapper."""
        # Try as ZIP first
        if content[:2] == b"PK":
            try:
                with zipfile.ZipFile(BytesIO(content)) as zf:
                    xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
                    if xml_files:
                        xml_data = zf.read(xml_files[0])
                        return ET.fromstring(xml_data)
            except Exception as e:
                logger.warning(f"ZIP parse failed: {e}")

        # Try as raw XML
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            logger.error("Failed to parse content as XML or ZIP")
            return None

    def _extract_patent_data(self, elem: ET.Element, kind_code: str) -> dict[str, Any]:
        """Extract patent fields from XML element."""
        pub_num = (
            self._text(elem, "us:PatentNumber")
            or self._text(elem, "pat:PatentNumber")
            or self._text(elem, "PatentNumber")
            or ""
        )
        title = (
            self._text(elem, "us:InventionTitle")
            or self._text(elem, "pat:InventionTitle")
            or self._text(elem, "InventionTitle")
            or ""
        )

        return {
            "patent_number": pub_num,
            "publication_number": pub_num,
            "application_number": self._text(elem, "us:ApplicationNumber")
            or self._text(elem, "ApplicationNumber"),
            "kind_code": kind_code,
            "filing_date": self._text(elem, "us:FilingDate") or self._text(elem, "FilingDate"),
            "issue_date": self._text(elem, "us:GrantDate") or self._text(elem, "GrantDate") or None,
            "publication_date": self._text(elem, "us:PublicationDate")
            or self._text(elem, "PublicationDate"),
            "invention_title": title,
            "abstract_text": self._text(elem, "us:Abstract") or self._text(elem, "Abstract"),
            "assignees": self._extract_parties(elem, "us:Assignee")
            or self._extract_parties(elem, "Assignee"),
            "inventors": self._extract_parties(elem, "us:Inventor")
            or self._extract_parties(elem, "Inventor"),
            "cpc_codes": self._extract_classifications(elem, "us:CPC")
            or self._extract_classifications(elem, "CPC"),
            "ipc_codes": self._extract_classifications(elem, "us:IPC")
            or self._extract_classifications(elem, "IPC"),
        }

    def _text(self, elem: ET.Element, tag: str) -> str | None:
        """Get text content of the first matching child element."""
        child = elem.find(_ns(tag))
        if child is None:
            # Try without namespace
            for c in elem:
                if c.tag.endswith(tag.split(":")[-1] if ":" in tag else tag):
                    text = c.text
                    return text.strip() if text else None
            return None
        text = child.text
        return text.strip() if text else None

    def _extract_parties(self, elem: ET.Element, tag: str) -> list[dict[str, str]]:
        """Extract assignee/inventor names."""
        parties = []
        for child in elem.iterfind(_ns(tag)):
            name = (
                self._text(child, "us:PartyName")
                or self._text(child, "PartyName")
                or self._text(child, "us:Name")
                or self._text(child, "Name")
            )
            if name:
                field = "assignee_name" if "assignee" in tag.lower() else "inventor_name"
                parties.append({field: name})
        return parties

    def _extract_classifications(self, elem: ET.Element, tag: str) -> list[dict[str, str]]:
        """Extract CPC/IPC codes."""
        codes = []
        for child in elem.iterfind(_ns(tag)):
            code = self._text(child, "us:Code") or self._text(child, "Code") or child.text
            if code:
                codes.append({"code": code.strip()})
        return codes
