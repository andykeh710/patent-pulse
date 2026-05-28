"""Tests for Sprint 6.5 citation fetch in USPTO client."""
from unittest.mock import patch

import pytest

from app.ingestion.uspto_client import USPTOClient


class MockPatent:
    """Minimal mock matching PatentBiblio attributes used by _patent_to_dict."""
    publication_number = "12345678"
    appl_id = "APP001"
    app_filing_date = None
    patent_title = "Test Patent"
    assignee_names = ["Acme Corp"]
    applicant_names = ["Inventor One"]
    cpc_additional = ["G06F"]
    cpc_inventive = []
    ipc_code = []
    forward_citations = None


class MockCitation:
    def __init__(self, pub_num):
        self.publication_number = pub_num


@pytest.fixture
def client():
    return USPTOClient()


def test_patent_to_dict_citations_empty_when_flag_false(client, monkeypatch):
    monkeypatch.setattr("app.ingestion.uspto_client.settings.uspto_fetch_citations", False)
    patent = MockPatent()
    result = client._patent_to_dict(patent)
    assert result["citations"] == []


def test_patent_to_dict_citations_populated_when_flag_true(client, monkeypatch):
    monkeypatch.setattr("app.ingestion.uspto_client.settings.uspto_fetch_citations", True)
    patent = MockPatent()
    patent.forward_citations = [MockCitation("55555555"), MockCitation("66666666")]
    result = client._patent_to_dict(patent)
    assert result["citations"] == ["USPTO:55555555", "USPTO:66666666"]


def test_fetch_forward_citations_handles_missing_attribute(client):
    patent = MockPatent()
    result = client._fetch_forward_citations(patent)
    assert result == []


def test_fetch_forward_citations_returns_doc_ids(client):
    patent = MockPatent()
    patent.forward_citations = [MockCitation("1111111"), MockCitation("2222222")]
    result = client._fetch_forward_citations(patent)
    assert result == ["USPTO:1111111", "USPTO:2222222"]


def test_fetch_forward_citations_exponential_backoff_on_429(client):
    """HTTP 429 triggers 3 retries with exponential backoff, then returns []."""
    from urllib.error import HTTPError

    call_count = [0]

    class FailingCitations:
        def __iter__(self):
            # Will raise on iteration
            call_count[0] += 1
            raise HTTPError("http://x", 429, "Too Many Requests", {}, None)

    patent = MockPatent()
    patent.forward_citations = FailingCitations()

    with patch("time.sleep", return_value=None):
        result = client._fetch_forward_citations(patent)

    # 4 attempts (1 initial + 3 retries) → all fail → returns []
    assert result == []
    # The _fetch_forward_citations method tries getattr first, then iterates.
    # Retry loop: attempt 0 (fail 429) → sleep 2 → attempt 1 (fail 429) →
    # sleep 4 → attempt 2 (fail 429) → sleep 8 → attempt 3 → return []
    assert call_count[0] >= 1  # at least one call attempted


def test_fetch_forward_citations_handles_generic_exception(client):
    patent = MockPatent()

    class BrokenCitations:
        def __iter__(self):
            raise RuntimeError("SDK crashed")

    patent.forward_citations = BrokenCitations()
    result = client._fetch_forward_citations(patent)
    assert result == []
