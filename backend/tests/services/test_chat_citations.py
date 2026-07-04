"""Tests for Phase 3 PR 4 — citation extraction and verification."""

from app.services.chat_citations import extract_citations, verify_citations

# ── extract_citations ──────────────────────────────────────────────────


class TestExtractCitations:
    def test_no_citations_returns_empty(self):
        assert extract_citations("Just some text with no patent references.") == []

    def test_empty_string(self):
        assert extract_citations("") == []

    def test_single_citation(self):
        result = extract_citations("See [USPTO:US12345678] for details.")
        assert result == ["USPTO:US12345678"]

    def test_multiple_citations(self):
        text = "[USPTO:US12345] describes method A, while [EPO:EP67890B1] covers method B."
        result = extract_citations(text)
        assert result == ["USPTO:US12345", "EPO:EP67890B1"]

    def test_duplicates_deduplicated(self):
        text = "[USPTO:US12345] and [USPTO:US12345] again."
        result = extract_citations(text)
        assert result == ["USPTO:US12345"]

    def test_preserves_first_appearance_order(self):
        text = "[EPO:EP2] came after [USPTO:US1] but [EPO:EP2] repeats."
        result = extract_citations(text)
        assert result == ["EPO:EP2", "USPTO:US1"]

    def test_wipo_prefix_accepted(self):
        result = extract_citations("See [WIPO:WO2024/123456] for the PCT filing.")
        assert result == ["WIPO:WO2024/123456"]

    def test_wipo_with_hyphen_accepted(self):
        result = extract_citations("[WIPO:WO2024-123456] is a PCT application.")
        assert result == ["WIPO:WO2024-123456"]

    # ── Rejected patterns ─────────────────────────────────────────────

    def test_rejects_bare_prefix_no_doc_id(self):
        """[USPTO] without colon+doc_id is NOT a citation."""
        assert extract_citations("The [USPTO] says nothing.") == []

    def test_rejects_bare_numbers(self):
        """Plain numbers in brackets are not citations."""
        assert extract_citations("Reference [12345] is not a patent.") == []

    def test_rejects_lowercase_prefix(self):
        """Only uppercase prefixes match."""
        assert extract_citations("[uspto:US12345] is lowercase.") == []

    def test_rejects_unknown_prefix(self):
        """Only USPTO, EPO, WIPO are accepted."""
        assert extract_citations("[OTHER:ABC123] is unknown.") == []

    def test_rejects_bare_text_in_brackets(self):
        """Arbitrary text in brackets is not a citation."""
        assert extract_citations("[some random text]") == []

    def test_rejects_partial_match_without_colon(self):
        """Must have colon between prefix and doc_id."""
        assert extract_citations("[USPTO US12345] without colon.") == []

    def test_accepts_underscore_in_doc_id(self):
        result = extract_citations("[EPO:EP_12345_B1] with underscores.")
        assert result == ["EPO:EP_12345_B1"]


# ── verify_citations ───────────────────────────────────────────────────


class TestVerifyCitations:
    def test_all_verified(self):
        known = {"USPTO:US1", "EPO:EP2", "WIPO:WO3"}
        result = verify_citations(["USPTO:US1", "EPO:EP2"], known)
        assert result["verified"] == ["USPTO:US1", "EPO:EP2"]
        assert result["unverified"] == []

    def test_all_unverified(self):
        known = {"USPTO:US1"}
        result = verify_citations(["USPTO:US99", "EPO:EP88"], known)
        assert result["verified"] == []
        assert result["unverified"] == ["USPTO:US99", "EPO:EP88"]

    def test_mixed_verified_and_unverified(self):
        known = {"USPTO:US1", "EPO:EP2"}
        result = verify_citations(
            ["USPTO:US1", "USPTO:US99", "EPO:EP2", "WIPO:WO88"],
            known,
        )
        assert result["verified"] == ["USPTO:US1", "EPO:EP2"]
        assert result["unverified"] == ["USPTO:US99", "WIPO:WO88"]

    def test_empty_cited_list(self):
        known = {"USPTO:US1"}
        result = verify_citations([], known)
        assert result["verified"] == []
        assert result["unverified"] == []

    def test_empty_known_set(self):
        result = verify_citations(["USPTO:US1", "EPO:EP2"], set())
        assert result["verified"] == []
        assert result["unverified"] == ["USPTO:US1", "EPO:EP2"]

    def test_both_empty(self):
        result = verify_citations([], set())
        assert result == {"verified": [], "unverified": []}

    def test_prefix_agnostic_cited_has_prefix_known_does_not(self):
        """USPTO:US12345 in citations matches US12345 in known set."""
        known = {"US12345", "EP67890B1"}
        result = verify_citations(["USPTO:US12345", "EPO:EP67890B1"], known)
        assert result["verified"] == ["USPTO:US12345", "EPO:EP67890B1"]
        assert result["unverified"] == []

    def test_prefix_agnostic_known_has_prefix_cited_does_not(self):
        """US12345 in citations matches USPTO:US12345 in known set."""
        known = {"USPTO:US12345", "EPO:EP67890B1"}
        result = verify_citations(["US12345", "EP67890B1"], known)
        assert result["verified"] == ["US12345", "EP67890B1"]
        assert result["unverified"] == []

    def test_prefix_agnostic_mixed_forms(self):
        """Mix of prefixed and unprefixed on both sides."""
        known = {"USPTO:US1", "EP2"}  # one with prefix, one without
        result = verify_citations(
            ["US1", "EPO:EP2", "WIPO:WO99"],  # opposite forms
            known,
        )
        assert result["verified"] == ["US1", "EPO:EP2"]
        assert result["unverified"] == ["WIPO:WO99"]
