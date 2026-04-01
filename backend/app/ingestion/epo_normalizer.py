"""
EPO and WIPO data normalizers.

Transforms raw EPO OPS and WIPO PatentScope data into the internal
PatentPublication schema.
"""

import logging
import re
from datetime import date, datetime

from app.core.enums import LegalStatus, PatentOffice
from app.core.exceptions import NormalizationError

logger = logging.getLogger(__name__)

EP_UTILITY_TERM_YEARS = 20


class EPONormalizer:
    """Normalizes raw EPO OPS data to the internal PatentPublication schema."""

    def normalize_publication(self, raw: dict) -> dict:
        """
        Normalize an EPO publication.

        Args:
            raw: Raw publication data from EPO client

        Returns:
            Dictionary matching PatentPublication schema
        """
        pub_number = raw.get("publication_number")
        if not pub_number:
            raise NormalizationError("EPO publication missing publication_number")

        kind_code = raw.get("kind_code", "")
        is_grant = kind_code.startswith("B")

        return {
            "doc_id": self._build_doc_id(PatentOffice.EPO, pub_number),
            "office": PatentOffice.EPO,
            "publication_number": pub_number,
            "application_number": raw.get("application_number"),
            "kind_code": kind_code,
            "filing_date": self._parse_date(raw.get("filing_date")),
            "priority_date": self._extract_priority_date(raw),
            "publication_date": self._parse_date(raw.get("publication_date")),
            "grant_date": self._parse_date(raw.get("publication_date")) if is_grant else None,
            "assignees": self._extract_names(raw.get("applicants", [])),
            "inventors": self._extract_names(raw.get("inventors", [])),
            "cpc": self._extract_codes(raw.get("cpc_codes", [])),
            "ipc": self._extract_codes(raw.get("ipc_codes", [])),
            "title": raw.get("title"),
            "abstract": raw.get("abstract"),
            "claims_text": None,
            "description_text": None,
            "citations_backward": [],
            "estimated_expiry_date": self._compute_expiry(raw),
            "legal_status": LegalStatus.GRANTED if is_grant else LegalStatus.PUBLISHED,
            "raw_data": raw.get("raw_data", raw),
        }

    def _build_doc_id(self, office: PatentOffice, number: str) -> str:
        """Build canonical document ID."""
        clean_number = re.sub(r"[^A-Z0-9]", "", str(number).upper())
        return f"{office}:{clean_number}"

    def _parse_date(self, value: str | date | None) -> date | None:
        """Parse EPO date format (YYYYMMDD)."""
        if value is None:
            return None
        if isinstance(value, date):
            return value

        value_str = str(value).strip()
        if not value_str:
            return None

        formats = ["%Y%m%d", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        return None

    def _extract_priority_date(self, raw: dict) -> date | None:
        """Extract earliest priority date from priority claims."""
        priority_claims = raw.get("priority_claims", [])
        if not priority_claims:
            return None

        dates = []
        for claim in priority_claims:
            date_val = claim.get("date")
            parsed = self._parse_date(date_val)
            if parsed:
                dates.append(parsed)

        return min(dates) if dates else None

    def _extract_names(self, parties: list[dict]) -> list[str]:
        """Extract names from party list."""
        return [p.get("name", "") for p in parties if p.get("name")]

    def _extract_codes(self, codes: list[dict]) -> list[str]:
        """Extract classification codes."""
        return [c.get("code", "") for c in codes if c.get("code")]

    def _compute_expiry(self, raw: dict) -> date | None:
        """Compute estimated expiry date (20 years from earliest filing)."""
        filing = self._parse_date(raw.get("filing_date"))
        priority = self._extract_priority_date(raw)

        base_date = priority or filing
        if not base_date:
            return None

        try:
            return base_date.replace(year=base_date.year + EP_UTILITY_TERM_YEARS)
        except ValueError:
            return date(base_date.year + EP_UTILITY_TERM_YEARS, base_date.month, 28)


class WIPONormalizer:
    """Normalizes raw WIPO PatentScope data to the internal PatentPublication schema."""

    def normalize_pct_application(self, raw: dict) -> dict:
        """
        Normalize a PCT application.

        Args:
            raw: Raw publication data from WIPO client

        Returns:
            Dictionary matching PatentPublication schema
        """
        pub_number = raw.get("publication_number")
        if not pub_number:
            raise NormalizationError("PCT application missing publication_number")

        return {
            "doc_id": self._build_doc_id(PatentOffice.WIPO, pub_number),
            "office": PatentOffice.WIPO,
            "publication_number": pub_number,
            "application_number": raw.get("application_number"),
            "kind_code": "A1",
            "filing_date": self._parse_date(raw.get("filing_date")),
            "priority_date": self._extract_priority_date(raw),
            "publication_date": self._parse_date(raw.get("publication_date")),
            "grant_date": None,
            "assignees": self._extract_names(raw.get("applicants", [])),
            "inventors": self._extract_names(raw.get("inventors", [])),
            "cpc": [],
            "ipc": self._extract_codes(raw.get("ipc_codes", [])),
            "title": raw.get("title"),
            "abstract": raw.get("abstract"),
            "claims_text": None,
            "description_text": None,
            "citations_backward": [],
            "estimated_expiry_date": None,
            "legal_status": LegalStatus.PUBLISHED,
            "family_members": raw.get("designated_states", []),
            "raw_data": raw,
        }

    def _build_doc_id(self, office: PatentOffice, number: str) -> str:
        """Build canonical document ID."""
        clean_number = re.sub(r"[^A-Z0-9]", "", str(number).upper())
        return f"{office}:{clean_number}"

    def _parse_date(self, value: str | date | None) -> date | None:
        """Parse WIPO date formats."""
        if value is None:
            return None
        if isinstance(value, date):
            return value

        value_str = str(value).strip()
        if not value_str:
            return None

        formats = ["%Y-%m-%d", "%Y%m%d", "%d.%m.%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        return None

    def _extract_priority_date(self, raw: dict) -> date | None:
        """Extract earliest priority date from priority claims."""
        priority_claims = raw.get("priority_claims", [])
        if not priority_claims:
            return None

        dates = []
        for claim in priority_claims:
            date_val = claim.get("date")
            parsed = self._parse_date(date_val)
            if parsed:
                dates.append(parsed)

        return min(dates) if dates else None

    def _extract_names(self, parties: list[dict] | list[str]) -> list[str]:
        """Extract names from party list."""
        result = []
        for p in parties:
            if isinstance(p, dict):
                name = p.get("name", "")
            else:
                name = str(p)
            if name:
                result.append(name)
        return result

    def _extract_codes(self, codes: list[dict] | list[str]) -> list[str]:
        """Extract classification codes."""
        result = []
        for c in codes:
            if isinstance(c, dict):
                code = c.get("code", "")
            else:
                code = str(c)
            if code:
                result.append(code)
        return result
