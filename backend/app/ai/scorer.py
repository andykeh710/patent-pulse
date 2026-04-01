import logging
import re
from typing import Any

from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

NOTABLE_ASSIGNEES = {
    "apple",
    "google",
    "alphabet",
    "microsoft",
    "amazon",
    "meta",
    "facebook",
    "nvidia",
    "qualcomm",
    "intel",
    "ibm",
    "samsung",
    "sony",
    "tesla",
    "spacex",
    "openai",
    "anthropic",
    "deepmind",
    "boston dynamics",
}

HIGH_VALUE_CPC_SECTIONS = {
    "A61": 0.3,  # Medical/veterinary
    "G06": 0.3,  # Computing
    "H04": 0.3,  # Electric communication
    "C12": 0.3,  # Biochemistry/genetic engineering
    "B60": 0.2,  # Vehicles
    "G16": 0.3,  # Healthcare informatics
    "H01": 0.2,  # Basic electric elements
    "F03": 0.2,  # Machines/engines (wind, hydro)
}

BROAD_CLAIM_SIGNALS = [
    "comprising",
    "configured to",
    "wherein",
    "any of",
    "one or more",
    "plurality",
    "at least one",
    "system",
    "method",
    "apparatus",
    "device",
    "machine learning",
    "artificial intelligence",
    "neural network",
    "blockchain",
    "autonomous",
    "real-time",
]


class PatentScorer:
    """
    Computes composite interest scores for patents.

    Score ranges from 0.0 to 1.0, combining multiple signals:
    - CPC taxonomy relevance to tracked themes
    - Assignee notoriety (major tech companies)
    - Claim breadth (platform-like language)
    - Family breadth (Phase 2+)
    - Semantic novelty (Phase 3+)
    """

    WEIGHTS = {
        "cpc_relevance": 0.30,
        "assignee_notoriety": 0.25,
        "claim_breadth": 0.25,
        "family_breadth": 0.10,
        "semantic_novelty": 0.10,
    }

    TRACKED_CPC_PREFIXES: list[str] = []

    def __init__(self, tracked_cpc_prefixes: list[str] | None = None):
        if tracked_cpc_prefixes:
            self.TRACKED_CPC_PREFIXES = tracked_cpc_prefixes

    def score(self, patent: PatentPublication) -> tuple[float, dict[str, float]]:
        """
        Compute interest score for a patent.

        Args:
            patent: PatentPublication instance

        Returns:
            Tuple of (total_score, breakdown_dict)
        """
        breakdown = {
            "cpc_relevance": self._cpc_relevance(patent.cpc or []),
            "assignee_notoriety": self._assignee_notoriety(patent.assignees or []),
            "claim_breadth": self._claim_breadth(patent.claims_text),
            "family_breadth": 0.5,
            "semantic_novelty": 0.5,
        }

        total = sum(self.WEIGHTS[k] * v for k, v in breakdown.items())
        return round(total, 4), breakdown

    def score_dict(self, patent_data: dict[str, Any]) -> tuple[float, dict[str, float]]:
        """
        Compute interest score from a patent data dictionary.

        Args:
            patent_data: Normalized patent data dict

        Returns:
            Tuple of (total_score, breakdown_dict)
        """
        breakdown = {
            "cpc_relevance": self._cpc_relevance(patent_data.get("cpc", [])),
            "assignee_notoriety": self._assignee_notoriety(patent_data.get("assignees", [])),
            "claim_breadth": self._claim_breadth(patent_data.get("claims_text")),
            "family_breadth": 0.5,
            "semantic_novelty": 0.5,
        }

        total = sum(self.WEIGHTS[k] * v for k, v in breakdown.items())
        return round(total, 4), breakdown

    def _cpc_relevance(self, cpc_codes: list[str]) -> float:
        """
        Score CPC relevance.

        Returns 1.0 if any code matches a tracked prefix,
        section-based score for high-value sections,
        0.1 otherwise.
        """
        if not cpc_codes:
            return 0.1

        for code in cpc_codes:
            code_upper = code.upper()
            for prefix in self.TRACKED_CPC_PREFIXES:
                if code_upper.startswith(prefix.upper()):
                    return 1.0

        max_section_score = 0.1
        for code in cpc_codes:
            for section, score in HIGH_VALUE_CPC_SECTIONS.items():
                if code.upper().startswith(section):
                    max_section_score = max(max_section_score, score)

        return max_section_score

    def _assignee_notoriety(self, assignees: list[str]) -> float:
        """
        Score assignee notoriety.

        Returns 1.0 for known notable assignees,
        0.2 for unknown (startups matter too).
        """
        for assignee in assignees:
            assignee_lower = assignee.lower()
            for notable in NOTABLE_ASSIGNEES:
                if notable in assignee_lower:
                    return 1.0

        return 0.2

    def _claim_breadth(self, claims_text: str | None) -> float:
        """
        Score claim breadth based on platform/functional language.

        More broad signal words = higher score.
        """
        if not claims_text:
            return 0.2

        claims_lower = claims_text[:1000].lower()

        hits = sum(1 for signal in BROAD_CLAIM_SIGNALS if signal in claims_lower)

        score = min(hits / 8.0, 1.0)
        return max(score, 0.1)


def get_score_label(score: float) -> str:
    """Get human-readable label for a score."""
    if score >= 0.7:
        return "high"
    elif score >= 0.4:
        return "medium"
    else:
        return "low"


def get_score_color(score: float) -> str:
    """Get color code for a score (for UI)."""
    if score >= 0.7:
        return "#22c55e"
    elif score >= 0.4:
        return "#eab308"
    else:
        return "#6b7280"
