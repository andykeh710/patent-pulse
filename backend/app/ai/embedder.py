"""
Patent Embedding Generator.

Uses OpenAI's text-embedding-3-small model to generate vector embeddings
for semantic search and novelty scoring.
"""

import logging
from typing import Any

import httpx

from app.config import settings
from app.core.exceptions import PatentPulseError
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingError(PatentPulseError):
    """Error generating embeddings."""

    pass


class PatentEmbedder:
    """
    Generates vector embeddings for patents.

    Embeddings are used for:
    - Semantic search (find similar patents)
    - Novelty scoring (distance from existing patents)
    - Clustering and visualization
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        self._http_client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._http_client.close()

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (max ~8000 tokens)

        Returns:
            1536-dimensional embedding vector
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        text = text[:32000]

        try:
            response = self._http_client.post(
                OPENAI_EMBEDDING_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text,
                    "dimensions": EMBEDDING_DIMENSIONS,
                },
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]

            return embedding

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI embedding API error: {e}")
            raise EmbeddingError(f"Embedding API error: {e}") from e
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(str(e)) from e

    def generate_patent_embedding(self, patent: PatentPublication) -> list[float]:
        """
        Generate embedding for a patent.

        Combines title, abstract, and independent claims for embedding.

        Args:
            patent: PatentPublication instance

        Returns:
            1536-dimensional embedding vector
        """
        text_parts = []

        if patent.title:
            text_parts.append(f"Title: {patent.title}")

        if patent.abstract:
            text_parts.append(f"Abstract: {patent.abstract}")

        if patent.claims_text:
            independent_claims = self._extract_independent_claims(patent.claims_text)
            if independent_claims:
                text_parts.append(f"Claims: {independent_claims}")

        if patent.cpc:
            text_parts.append(f"Classifications: {', '.join(patent.cpc[:5])}")

        combined_text = "\n\n".join(text_parts)

        if not combined_text.strip():
            raise EmbeddingError(f"Patent {patent.doc_id} has no embeddable content")

        return self.generate_embedding(combined_text)

    def generate_batch_embeddings(
        self, texts: list[str], batch_size: int = 20
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch = [t[:32000] for t in batch if t and t.strip()]

            if not batch:
                continue

            try:
                response = self._http_client.post(
                    OPENAI_EMBEDDING_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": EMBEDDING_MODEL,
                        "input": batch,
                        "dimensions": EMBEDDING_DIMENSIONS,
                    },
                )
                response.raise_for_status()

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(embeddings)

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                all_embeddings.extend([None] * len(batch))

        return all_embeddings

    def _extract_independent_claims(self, claims_text: str, max_length: int = 2000) -> str:
        """Extract independent claims from full claims text."""
        import re

        lines = claims_text.split("\n")
        independent = []
        current_claim = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            claim_start = re.match(r"^(\d+)\.\s*", line)
            if claim_start:
                if current_claim:
                    claim_text = " ".join(current_claim)
                    if not self._references_other_claim(claim_text):
                        independent.append(claim_text)
                current_claim = [line]
            else:
                current_claim.append(line)

        if current_claim:
            claim_text = " ".join(current_claim)
            if not self._references_other_claim(claim_text):
                independent.append(claim_text)

        result = "\n".join(independent[:3])
        return result[:max_length]

    def _references_other_claim(self, claim_text: str) -> bool:
        """Check if claim references another claim."""
        import re

        first_100 = claim_text[:100].lower()
        patterns = [
            r"claim\s+\d+",
            r"according to claim",
            r"as (claimed|defined) in claim",
        ]
        return any(re.search(p, first_100) for p in patterns)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def cosine_distance(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine distance (1 - similarity) between two vectors."""
    return 1.0 - cosine_similarity(vec1, vec2)
