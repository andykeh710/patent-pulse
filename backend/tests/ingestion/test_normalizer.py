from datetime import date

import pytest

from app.core.enums import LegalStatus, PatentOffice
from app.core.exceptions import NormalizationError
from app.ingestion.normalizer import USPTONormalizer


@pytest.fixture
def normalizer() -> USPTONormalizer:
    return USPTONormalizer()


class TestUSPTONormalizerGrant:
    def test_normalize_grant_full_record(
        self, normalizer: USPTONormalizer, sample_uspto_raw_grant: dict
    ) -> None:
        result = normalizer.normalize_grant(sample_uspto_raw_grant)

        assert result["doc_id"] == "USPTO:12345678"
        assert result["office"] == PatentOffice.USPTO
        assert result["publication_number"] == "12345678"
        assert result["application_number"] == "17/123456"
        assert result["kind_code"] == "B2"
        assert result["filing_date"] == date(2022, 1, 15)
        assert result["grant_date"] == date(2024, 3, 15)
        assert result["title"] == "System and Method for Secure Authentication"
        assert result["legal_status"] == LegalStatus.GRANTED
        assert "Acme Corporation" in result["assignees"]
        assert "John Doe" in result["inventors"]
        assert len(result["cpc"]) == 2

    def test_normalize_grant_missing_patent_number_raises(
        self, normalizer: USPTONormalizer
    ) -> None:
        with pytest.raises(NormalizationError, match="missing patent_number"):
            normalizer.normalize_grant({})

    def test_normalize_grant_missing_abstract(self, normalizer: USPTONormalizer) -> None:
        raw = {
            "patent_number": "99999999",
            "filing_date": "2022-01-15",
        }
        result = normalizer.normalize_grant(raw)
        assert result["abstract"] is None
        assert result["doc_id"] == "USPTO:99999999"


class TestUSPTONormalizerApplication:
    def test_normalize_application(self, normalizer: USPTONormalizer) -> None:
        raw = {
            "publication_number": "20240001234",
            "application_number": "17/123456",
            "kind_code": "A1",
            "filing_date": "2022-01-15",
            "publication_date": "2024-01-04",
            "invention_title": "Test Application",
            "assignees": [{"assignee_name": "Test Corp"}],
        }
        result = normalizer.normalize_application(raw)

        assert result["doc_id"] == "USPTO:20240001234"
        assert result["legal_status"] == LegalStatus.PUBLISHED
        assert result["grant_date"] is None
        assert result["assignees"] == ["Test Corp"]

    def test_normalize_application_missing_both_numbers_raises(
        self, normalizer: USPTONormalizer
    ) -> None:
        with pytest.raises(NormalizationError, match="missing publication_number"):
            normalizer.normalize_application({})


class TestDateParsing:
    @pytest.mark.parametrize(
        "date_str,expected",
        [
            ("2022-01-15", date(2022, 1, 15)),
            ("20220115", date(2022, 1, 15)),
            ("01/15/2022", date(2022, 1, 15)),
            ("2022/01/15", date(2022, 1, 15)),
            (None, None),
            ("", None),
        ],
    )
    def test_parse_date_formats(
        self, normalizer: USPTONormalizer, date_str: str | None, expected: date | None
    ) -> None:
        result = normalizer._parse_date(date_str)
        assert result == expected

    def test_parse_date_already_date(self, normalizer: USPTONormalizer) -> None:
        d = date(2022, 1, 15)
        assert normalizer._parse_date(d) == d


class TestExpiryComputation:
    def test_compute_expiry_from_filing_date(self, normalizer: USPTONormalizer) -> None:
        raw = {"filing_date": "2022-01-15"}
        result = normalizer._compute_expiry(raw)
        assert result == date(2042, 1, 15)

    def test_compute_expiry_from_priority_date(self, normalizer: USPTONormalizer) -> None:
        raw = {
            "filing_date": "2023-01-15",
            "priority_date": "2022-01-15",
        }
        result = normalizer._compute_expiry(raw)
        assert result == date(2042, 1, 15)

    def test_compute_expiry_leap_year(self, normalizer: USPTONormalizer) -> None:
        raw = {"filing_date": "2024-02-29"}
        result = normalizer._compute_expiry(raw)
        assert result == date(2044, 2, 29)  # 2044 is also a leap year

    def test_compute_expiry_no_date(self, normalizer: USPTONormalizer) -> None:
        assert normalizer._compute_expiry({}) is None


class TestCodeExtraction:
    def test_extract_cpc_codes(self, normalizer: USPTONormalizer) -> None:
        raw = {
            "patent_number": "12345678",
            "cpc_codes": [{"code": "G06F 21/00"}, {"code": "h04l 9/32"}],
        }
        result = normalizer.normalize_grant(raw)
        assert "G06F 21/00" in result["cpc"]
        assert "H04L 9/32" in result["cpc"]

    def test_extract_list_items(self, normalizer: USPTONormalizer) -> None:
        raw = {
            "patent_number": "12345678",
            "assignees": [
                {"assignee_name": "Company A"},
                {"name": "Company B"},
            ],
        }
        result = normalizer.normalize_grant(raw)
        assert result["assignees"] == ["Company A", "Company B"]
