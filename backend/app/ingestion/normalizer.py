import logging
import re
from datetime import date, datetime

from app.core.enums import LegalStatus, PatentOffice
from app.core.exceptions import NormalizationError

logger = logging.getLogger(__name__)

US_UTILITY_TERM_YEARS = 20


class USPTONormalizer:
    """Normalizes raw USPTO data to the internal PatentPublication schema."""

    def normalize_grant(self, raw: dict) -> dict:
        """
        Normalize a granted patent from USPTO.

        Args:
            raw: Raw patent data from USPTO client

        Returns:
            Dictionary matching PatentPublication schema
        """
        patent_number = raw.get("patent_number")
        if not patent_number:
            raise NormalizationError("Grant missing patent_number")

        return {
            "doc_id": self._build_doc_id(PatentOffice.USPTO, patent_number),
            "office": PatentOffice.USPTO,
            "publication_number": patent_number,
            "application_number": raw.get("application_number"),
            "kind_code": raw.get("kind_code", "B2"),
            "filing_date": self._parse_date(raw.get("filing_date")),
            "priority_date": self._parse_date(raw.get("priority_date")),
            "publication_date": self._parse_date(raw.get("issue_date")),
            "grant_date": self._parse_date(raw.get("issue_date")),
            "assignees": self._extract_list(raw, "assignees", "assignee_name"),
            "inventors": self._extract_list(raw, "inventors", "inventor_name"),
            "cpc": self._extract_codes(raw, "cpc_codes"),
            "ipc": self._extract_codes(raw, "ipc_codes"),
            "title": raw.get("invention_title"),
            "abstract": raw.get("abstract_text"),
            "claims_text": raw.get("claims"),
            "description_text": raw.get("description"),
            "citations_backward": self._extract_citations(raw),
            "estimated_expiry_date": self._compute_expiry(raw),
            "legal_status": LegalStatus.GRANTED,
            "raw_data": raw,
        }

    def normalize_application(self, raw: dict) -> dict:
        """
        Normalize a published application from USPTO.

        Args:
            raw: Raw application data from USPTO client

        Returns:
            Dictionary matching PatentPublication schema
        """
        pub_number = raw.get("publication_number")
        app_number = raw.get("application_number")

        if not pub_number and not app_number:
            raise NormalizationError("Application missing publication_number and application_number")

        identifier = pub_number or app_number

        return {
            "doc_id": self._build_doc_id(PatentOffice.USPTO, identifier),
            "office": PatentOffice.USPTO,
            "publication_number": pub_number,
            "application_number": app_number,
            "kind_code": raw.get("kind_code", "A1"),
            "filing_date": self._parse_date(raw.get("filing_date")),
            "priority_date": self._parse_date(raw.get("priority_date")),
            "publication_date": self._parse_date(raw.get("publication_date")),
            "grant_date": None,
            "assignees": self._extract_list(raw, "assignees", "assignee_name"),
            "inventors": self._extract_list(raw, "inventors", "inventor_name"),
            "cpc": self._extract_codes(raw, "cpc_codes"),
            "ipc": self._extract_codes(raw, "ipc_codes"),
            "title": raw.get("invention_title"),
            "abstract": raw.get("abstract_text"),
            "claims_text": raw.get("claims"),
            "description_text": None,
            "citations_backward": [],
            "estimated_expiry_date": self._compute_expiry(raw),
            "legal_status": LegalStatus.PUBLISHED,
            "raw_data": raw,
        }

    def _build_doc_id(self, office: PatentOffice, number: str) -> str:
        """Build canonical document ID."""
        if not number:
            raise NormalizationError("Cannot build doc_id: no number provided")
        clean_number = re.sub(r"[^A-Z0-9]", "", str(number).upper())
        return f"{office}:{clean_number}"

    def _parse_date(self, value: str | date | None) -> date | None:
        """Parse various date formats to date object."""
        if value is None:
            return None
        if isinstance(value, date):
            return value

        value_str = str(value).strip()
        if not value_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%Y%m%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {value}")
        return None

    def _extract_list(self, raw: dict, key: str, name_field: str) -> list[str]:
        """Extract list of names from nested structure."""
        items = raw.get(key, [])
        if not items:
            return []

        result = []
        for item in items:
            if isinstance(item, dict):
                name = item.get(name_field) or item.get("name")
            else:
                name = str(item)
            if name:
                result.append(name)

        return result

    def _extract_codes(self, raw: dict, key: str) -> list[str]:
        """Extract classification codes."""
        items = raw.get(key, [])
        if not items:
            return []

        codes = []
        for item in items:
            if isinstance(item, dict):
                code = item.get("code") or item.get("classification")
            else:
                code = str(item)
            if code:
                codes.append(self._normalize_cpc(code))

        return codes

    def _normalize_cpc(self, code: str) -> str:
        """Normalize CPC code format."""
        code = str(code).strip().upper()
        code = re.sub(r"\s+", " ", code)
        return code

    def _extract_citations(self, raw: dict) -> list[str]:
        """Extract backward citations as document IDs."""
        citations = raw.get("citations", [])
        if not citations:
            return []

        result = []
        for citation in citations:
            if isinstance(citation, dict):
                doc = citation.get("cited_document") or citation.get("patent_number")
            else:
                doc = str(citation)
            if doc:
                result.append(doc)

        return result

    def _compute_expiry(self, raw: dict) -> date | None:
        """
        Compute estimated expiry date.

        For US utility patents: 20 years from earliest filing date.
        Does not account for PTA/PTE - that's Phase 3 complexity.
        """
        filing_date = self._parse_date(raw.get("filing_date"))
        priority_date = self._parse_date(raw.get("priority_date"))

        base_date = priority_date or filing_date
        if not base_date:
            return None

        try:
            return base_date.replace(year=base_date.year + US_UTILITY_TERM_YEARS)
        except ValueError:
            return date(base_date.year + US_UTILITY_TERM_YEARS, base_date.month, 28)
