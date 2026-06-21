"""
USPTO ODP v2 Bulk Dataset Ingestion Client — V3.8C.

Uses the ODP datasets/products API to discover and download weekly patent grant
and application bibliographic XML files.

Products:
- PTGRXML: Patent Grant Full-Text Data (XML) — weekly, every Tuesday
- APPXML:  Patent Application Full-Text Data (XML) — weekly, every Thursday
- PTBLXML: Patent Grant Bibliographic Data (XML)
- APPBLXML: Patent Application Bibliographic Data (XML)

Workflow:
1. Query /datasets/products/PTGRXML to get file listing
2. Filter files by date range (fileDataFromDate / fileDataToDate)
3. Download each ZIP via fileDownloadURI
4. Extract XML, parse USPTO grant/application bibliographic data
5. Feed into existing USPTONormalizer + upsert pipeline
"""

import json
import logging
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class USPTOBulkDatasetClient:
    """
    Client for ODP v2 Bulk Dataset product ingestion.

    Discovers weekly grant/application ZIP files via the datasets/products API
    and downloads/parses bibliographic XML.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "uspto_odp_api_key", None)
        self.base = "https://api.uspto.gov/api/v1"
        self.stats = {
            "files_discovered": 0,
            "files_downloaded": 0,
            "files_failed": 0,
            "records_parsed": 0,
            "records_skipped": 0,
        }

    # ── Product file discovery ──────────────────────────────────────────

    def get_grant_files(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Discover PTGRXML (Patent Grant XML) files in the date range."""
        return self._get_product_files("PTGRXML", start_date, end_date)

    def get_application_files(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Discover APPXML (Patent Application XML) files in the date range."""
        return self._get_product_files("APPXML", start_date, end_date)

    def _get_product_files(
        self, product_id: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Get file listing for a bulk data product within a date range."""
        headers = {
            "X-API-Key": self.api_key,
            "User-Agent": "InventionIndex8/1.0 (V3.8C)",
        }

        url = f"{self.base}/datasets/products/{product_id}"
        r = httpx.get(url, headers=headers, timeout=30)

        if r.status_code != 200:
            logger.error(f"Product {product_id}: HTTP {r.status_code}")
            return []

        data = r.json()
        bag = data.get("bulkDataProductBag", [])
        if not bag:
            return []

        product = bag[0]
        file_bag = product.get("productFileBag", {}).get("fileDataBag", [])
        if not file_bag:
            return []

        # Filter by date range
        matched = []
        for f in file_bag:
            file_from = f.get("fileDataFromDate", "")
            file_to = f.get("fileDataToDate", "")
            # File must overlap with our date range
            if file_to >= str(start_date) and file_from <= str(end_date):
                matched.append({
                    "fileName": f["fileName"],
                    "fileSize": f.get("fileSize", 0),
                    "fileDownloadURI": f["fileDownloadURI"],
                    "fileDataFromDate": file_from,
                    "fileDataToDate": file_to,
                    "productIdentifier": product_id,
                })

        self.stats["files_discovered"] += len(matched)
        return matched

    # ── File download + parsing ─────────────────────────────────────────

    def download_and_parse(
        self, file_info: dict[str, Any]
    ) -> Iterator[dict[str, Any]]:
        """
        Download a ZIP file containing patent XML and yield parsed records.

        Each ZIP contains concatenated XML with multiple <us-patent-grant> or
        <us-patent-application> documents.
        """
        headers = {
            "X-API-Key": self.api_key,
            "User-Agent": "InventionIndex8/1.0 (V3.8C)",
        }

        url = file_info["fileDownloadURI"]
        logger.info(f"Downloading {file_info['fileName']} ({file_info.get('fileSize', 0)} bytes)")

        try:
            r = httpx.get(url, headers=headers, timeout=300, follow_redirects=True)
            if r.status_code != 200:
                logger.error(f"Download failed: HTTP {r.status_code}")
                self.stats["files_failed"] += 1
                return

            self.stats["files_downloaded"] += 1
            content = r.content
        except Exception as e:
            logger.error(f"Download error: {e}")
            self.stats["files_failed"] += 1
            return

        # Parse ZIP
        try:
            with zipfile.ZipFile(BytesIO(content)) as zf:
                xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
                for xml_name in xml_files:
                    xml_data = zf.read(xml_name)
                    try:
                        for record in self._parse_xml(xml_data, file_info):
                            self.stats["records_parsed"] += 1
                            yield record
                    except Exception as e:
                        logger.warning(f"Failed to parse {xml_name}: {e}")
                        self.stats["records_skipped"] += 1
        except Exception as e:
            logger.error(f"ZIP parse failed: {e}")
            self.stats["files_failed"] += 1

    def _parse_xml(
        self, content: bytes, file_info: dict
    ) -> Iterator[dict[str, Any]]:
        """
        Parse USPTO grant/application XML into bibliographic records.
        Handles concatenated XML (multiple root elements).
        """
        # Try full XML parse first
        try:
            root = ET.fromstring(content)
            yield from self._extract_records(root)
            return
        except ET.ParseError:
            pass

        # Handle concatenated XML by splitting on document boundaries
        text = content.decode("utf-8", errors="replace")
        # Split on <?xml or <!DOCTYPE or <us-patent- tags
        parts = text.split("<?xml")
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            xml_str = "<?xml" + part if i > 0 else part
            xml_str = xml_str.strip()
            if not xml_str:
                continue
            try:
                root = ET.fromstring(xml_str)
                yield from self._extract_records(root)
            except ET.ParseError:
                continue

    def _extract_records(self, root: ET.Element) -> Iterator[dict[str, Any]]:
        """Extract patent records from XML root element."""
        tag = root.tag.lower()

        if "patent-grant" in tag:
            yield from self._extract_grant_data(root)
        elif "patent-application" in tag:
            yield from self._extract_application_data(root)
        elif "us-patent-grant" in tag:
            yield from self._extract_grant_data(root)
        elif "us-patent-application" in tag:
            yield from self._extract_application_data(root)

    def _extract_grant_data(self, root: ET.Element) -> Iterator[dict[str, Any]]:
        """Extract bibliographic data from a patent grant XML."""
        biblio = root.find("us-bibliographic-data-grant")
        if biblio is None:
            for child in root:
                if "bibliographic-data-grant" in child.tag:
                    biblio = child
                    break
        if biblio is None:
            return

        yield self._extract_biblio_common(biblio, kind_default="B2")

    def _extract_application_data(self, root: ET.Element) -> Iterator[dict[str, Any]]:
        """Extract bibliographic data from a published application XML."""
        biblio = root.find("us-bibliographic-data-application")
        if biblio is None:
            for child in root:
                if "bibliographic-data-application" in child.tag:
                    biblio = child
                    break
        if biblio is None:
            return

        yield self._extract_biblio_common(biblio, kind_default="A1")

    def _extract_biblio_common(
        self, biblio: ET.Element, kind_default: str
    ) -> dict[str, Any]:
        """Extract common bibliographic fields from any USPTO XML bibliographic data."""

        # Publication reference
        pub_ref = biblio.find("publication-reference")
        pub_num = ""
        pub_date = ""
        kind = kind_default
        country = "US"
        if pub_ref is not None:
            doc_id = pub_ref.find(".//doc-number")
            pub_num = (
                doc_id.text.strip() if doc_id is not None and doc_id.text else ""
            )
            date_elem = pub_ref.find(".//date")
            pub_date = (
                date_elem.text.strip()
                if date_elem is not None and date_elem.text
                else ""
            )
            kind_elem = pub_ref.find(".//kind")
            if kind_elem is not None and kind_elem.text:
                kind = kind_elem.text.strip()
            country_elem = pub_ref.find(".//country")
            if country_elem is not None and country_elem.text:
                country = country_elem.text.strip()

        # Application reference
        app_num = ""
        filing_date = ""
        app_ref = biblio.find("application-reference")
        if app_ref is not None:
            app_doc = app_ref.find(".//doc-number")
            app_num = (
                app_doc.text.strip()
                if app_doc is not None and app_doc.text
                else ""
            )
            app_date = app_ref.find(".//date")
            filing_date = (
                app_date.text.strip()
                if app_date is not None and app_date.text
                else ""
            )

        # Title
        title = ""
        title_elem = biblio.find("invention-title")
        if title_elem is not None and title_elem.text:
            title = title_elem.text.strip()

        # Abstract
        abstract = ""
        abstract_elem = biblio.find("abstract")
        if abstract_elem is not None:
            for p in abstract_elem.iter():
                if p.text and p.tag == "p":
                    abstract += p.text.strip() + " "

        # Assignees
        assignees = []
        for assignee in biblio.iterfind(".//assignee"):
            orgname = assignee.find(".//orgname")
            if orgname is not None and orgname.text:
                assignees.append({"assignee_name": orgname.text.strip()})

        # Inventors
        inventors = []
        for inventor in biblio.iterfind(".//inventor"):
            last = inventor.find(".//last-name")
            first = inventor.find(".//first-name")
            if last is not None and last.text:
                name = last.text.strip()
                if first is not None and first.text:
                    name = f"{first.text.strip()} {name}"
                inventors.append({"inventor_name": name})

        # Format publication number
        pub_number = f"{country}{pub_num}{kind}"

        # Format dates
        pub_date_fmt = self._fmt_date(pub_date)
        filing_date_fmt = self._fmt_date(filing_date)

        return {
            "patent_number": pub_num,
            "publication_number": pub_number,
            "application_number": app_num,
            "kind_code": kind,
            "filing_date": filing_date_fmt,
            "publication_date": pub_date_fmt,
            "invention_title": title,
            "abstract_text": abstract.strip() if abstract else None,
            "assignees": assignees,
            "inventors": inventors,
            "cpc_codes": [],
            "office": country,
        }

    @staticmethod
    def _fmt_date(date_str: str) -> str | None:
        """Convert YYYYMMDD to YYYY-MM-DD."""
        if not date_str or len(date_str) != 8:
            return date_str or None
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except (ValueError, IndexError):
            return date_str
