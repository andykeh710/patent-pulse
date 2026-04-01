from datetime import date

import pytest

from app.core.enums import LegalStatus, PatentOffice
from app.core.exceptions import NormalizationError
from app.ingestion.epo_normalizer import EPONormalizer, WIPONormalizer


@pytest.fixture
def epo_normalizer() -> EPONormalizer:
    return EPONormalizer()


@pytest.fixture
def wipo_normalizer() -> WIPONormalizer:
    return WIPONormalizer()


@pytest.fixture
def sample_epo_publication() -> dict:
    return {
        "publication_number": "EP1234567A1",
        "application_number": "EP20210123456",
        "kind_code": "A1",
        "filing_date": "20210115",
        "publication_date": "20220720",
        "title": "Method for data processing",
        "abstract": "A method for efficiently processing data...",
        "applicants": [{"name": "Tech Corp GmbH"}],
        "inventors": [{"name": "Hans Mueller"}, {"name": "Anna Schmidt"}],
        "cpc_codes": [{"code": "G06F 16/00"}, {"code": "H04L 9/32"}],
        "ipc_codes": [{"code": "G06F 16/00"}],
        "priority_claims": [
            {"country": "DE", "doc_number": "102020001234", "date": "20200115"}
        ],
    }


@pytest.fixture
def sample_pct_application() -> dict:
    return {
        "publication_number": "WO2024001234",
        "application_number": "PCT/US2023/012345",
        "filing_date": "2023-03-15",
        "publication_date": "2024-01-04",
        "title": "System for machine learning inference",
        "abstract": "A system for performing ML inference...",
        "applicants": [{"name": "AI Startup Inc"}],
        "inventors": [{"name": "John Smith"}],
        "ipc_codes": [{"code": "G06N 3/08"}],
        "designated_states": ["US", "EP", "JP", "CN"],
        "priority_claims": [
            {"country": "US", "number": "63/123456", "date": "2022-03-15"}
        ],
    }


class TestEPONormalizer:
    def test_normalize_publication(
        self, epo_normalizer: EPONormalizer, sample_epo_publication: dict
    ) -> None:
        result = epo_normalizer.normalize_publication(sample_epo_publication)

        assert result["doc_id"] == "EPO:EP1234567A1"
        assert result["office"] == PatentOffice.EPO
        assert result["publication_number"] == "EP1234567A1"
        assert result["filing_date"] == date(2021, 1, 15)
        assert result["publication_date"] == date(2022, 7, 20)
        assert result["title"] == "Method for data processing"
        assert result["legal_status"] == LegalStatus.PUBLISHED
        assert "Tech Corp GmbH" in result["assignees"]
        assert len(result["inventors"]) == 2
        assert len(result["cpc"]) == 2

    def test_normalize_granted_publication(
        self, epo_normalizer: EPONormalizer, sample_epo_publication: dict
    ) -> None:
        sample_epo_publication["kind_code"] = "B1"
        sample_epo_publication["publication_number"] = "EP1234567B1"

        result = epo_normalizer.normalize_publication(sample_epo_publication)

        assert result["legal_status"] == LegalStatus.GRANTED
        assert result["grant_date"] is not None

    def test_normalize_missing_publication_number_raises(
        self, epo_normalizer: EPONormalizer
    ) -> None:
        with pytest.raises(NormalizationError, match="missing publication_number"):
            epo_normalizer.normalize_publication({})

    def test_extract_priority_date(
        self, epo_normalizer: EPONormalizer, sample_epo_publication: dict
    ) -> None:
        result = epo_normalizer.normalize_publication(sample_epo_publication)

        assert result["priority_date"] == date(2020, 1, 15)

    def test_compute_expiry(
        self, epo_normalizer: EPONormalizer, sample_epo_publication: dict
    ) -> None:
        result = epo_normalizer.normalize_publication(sample_epo_publication)

        assert result["estimated_expiry_date"] == date(2040, 1, 15)


class TestWIPONormalizer:
    def test_normalize_pct_application(
        self, wipo_normalizer: WIPONormalizer, sample_pct_application: dict
    ) -> None:
        result = wipo_normalizer.normalize_pct_application(sample_pct_application)

        assert result["doc_id"] == "WIPO:WO2024001234"
        assert result["office"] == PatentOffice.WIPO
        assert result["publication_number"] == "WO2024001234"
        assert result["filing_date"] == date(2023, 3, 15)
        assert result["publication_date"] == date(2024, 1, 4)
        assert result["title"] == "System for machine learning inference"
        assert result["legal_status"] == LegalStatus.PUBLISHED
        assert "AI Startup Inc" in result["assignees"]
        assert "G06N 3/08" in result["ipc"]
        assert "US" in result["family_members"]

    def test_normalize_missing_publication_number_raises(
        self, wipo_normalizer: WIPONormalizer
    ) -> None:
        with pytest.raises(NormalizationError, match="missing publication_number"):
            wipo_normalizer.normalize_pct_application({})

    def test_extract_priority_date(
        self, wipo_normalizer: WIPONormalizer, sample_pct_application: dict
    ) -> None:
        result = wipo_normalizer.normalize_pct_application(sample_pct_application)

        assert result["priority_date"] == date(2022, 3, 15)

    def test_handle_string_parties(self, wipo_normalizer: WIPONormalizer) -> None:
        data = {
            "publication_number": "WO2024999999",
            "applicants": ["Company A", "Company B"],
            "inventors": ["Inventor X"],
        }
        result = wipo_normalizer.normalize_pct_application(data)

        assert result["assignees"] == ["Company A", "Company B"]
        assert result["inventors"] == ["Inventor X"]

    def test_handle_string_ipc_codes(self, wipo_normalizer: WIPONormalizer) -> None:
        data = {
            "publication_number": "WO2024999999",
            "ipc_codes": ["G06F 21/00", "H04L 9/32"],
        }
        result = wipo_normalizer.normalize_pct_application(data)

        assert result["ipc"] == ["G06F 21/00", "H04L 9/32"]
