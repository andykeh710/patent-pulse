import pytest

from app.ai.scorer import PatentScorer, get_score_color, get_score_label
from app.core.models import PatentPublication


@pytest.fixture
def scorer() -> PatentScorer:
    return PatentScorer()


@pytest.fixture
def google_patent() -> PatentPublication:
    return PatentPublication(
        doc_id="USPTO:GOOGLE001",
        office="USPTO",
        publication_number="GOOGLE001",
        assignees=["Google LLC"],
        cpc=["G06F 21/00"],
        claims_text="1. A method comprising machine learning and neural network processing.",
    )


@pytest.fixture
def unknown_patent() -> PatentPublication:
    return PatentPublication(
        doc_id="USPTO:UNKNOWN001",
        office="USPTO",
        publication_number="UNKNOWN001",
        assignees=["Random Startup Inc"],
        cpc=["B01D 53/00"],
        claims_text="1. A filter comprising a mesh.",
    )


class TestPatentScorer:
    def test_score_returns_tuple(
        self, scorer: PatentScorer, google_patent: PatentPublication
    ) -> None:
        score, breakdown = scorer.score(google_patent)

        assert isinstance(score, float)
        assert isinstance(breakdown, dict)
        assert 0.0 <= score <= 1.0

    def test_notable_assignee_high_score(
        self, scorer: PatentScorer, google_patent: PatentPublication
    ) -> None:
        _, breakdown = scorer.score(google_patent)

        assert breakdown["assignee_notoriety"] == 1.0

    def test_unknown_assignee_nonzero_score(
        self, scorer: PatentScorer, unknown_patent: PatentPublication
    ) -> None:
        _, breakdown = scorer.score(unknown_patent)

        assert breakdown["assignee_notoriety"] == 0.2
        assert breakdown["assignee_notoriety"] > 0

    def test_high_value_cpc_section(self, scorer: PatentScorer) -> None:
        patent = PatentPublication(
            doc_id="USPTO:CPC001",
            office="USPTO",
            publication_number="CPC001",
            cpc=["G06N 3/08"],
        )
        _, breakdown = scorer.score(patent)

        assert breakdown["cpc_relevance"] >= 0.3

    def test_tracked_cpc_prefix_max_relevance(self) -> None:
        scorer = PatentScorer(tracked_cpc_prefixes=["G06N 3/"])
        patent = PatentPublication(
            doc_id="USPTO:TRACKED001",
            office="USPTO",
            publication_number="TRACKED001",
            cpc=["G06N 3/08"],
        )
        _, breakdown = scorer.score(patent)

        assert breakdown["cpc_relevance"] == 1.0

    def test_broad_claims_high_score(self, scorer: PatentScorer) -> None:
        patent = PatentPublication(
            doc_id="USPTO:BROAD001",
            office="USPTO",
            publication_number="BROAD001",
            claims_text="1. A system comprising one or more processors configured to "
            "execute machine learning algorithms wherein the plurality of "
            "neural network layers process real-time data.",
        )
        _, breakdown = scorer.score(patent)

        assert breakdown["claim_breadth"] >= 0.5

    def test_narrow_claims_low_score(self, scorer: PatentScorer) -> None:
        patent = PatentPublication(
            doc_id="USPTO:NARROW001",
            office="USPTO",
            publication_number="NARROW001",
            claims_text="1. A bolt with threads.",
        )
        _, breakdown = scorer.score(patent)

        assert breakdown["claim_breadth"] <= 0.3

    def test_score_from_dict(self, scorer: PatentScorer) -> None:
        data = {
            "assignees": ["Microsoft Corporation"],
            "cpc": ["G06F 21/00", "H04L 9/32"],
            "claims_text": "1. A method comprising neural network processing.",
        }
        score, breakdown = scorer.score_dict(data)

        assert 0.0 <= score <= 1.0
        assert breakdown["assignee_notoriety"] == 1.0

    def test_empty_patent_returns_valid_score(self, scorer: PatentScorer) -> None:
        patent = PatentPublication(
            doc_id="USPTO:EMPTY001",
            office="USPTO",
            publication_number="EMPTY001",
        )
        score, breakdown = scorer.score(patent)

        assert 0.0 <= score <= 1.0
        assert all(0.0 <= v <= 1.0 for v in breakdown.values())


class TestScoreHelpers:
    @pytest.mark.parametrize(
        "score,expected_label",
        [
            (0.9, "high"),
            (0.7, "high"),
            (0.5, "medium"),
            (0.4, "medium"),
            (0.3, "low"),
            (0.1, "low"),
        ],
    )
    def test_get_score_label(self, score: float, expected_label: str) -> None:
        assert get_score_label(score) == expected_label

    @pytest.mark.parametrize(
        "score,expected_color",
        [
            (0.9, "#22c55e"),
            (0.5, "#eab308"),
            (0.2, "#6b7280"),
        ],
    )
    def test_get_score_color(self, score: float, expected_color: str) -> None:
        assert get_score_color(score) == expected_color
