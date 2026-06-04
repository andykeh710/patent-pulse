"""
PatentsView API Provider (USPTO).

Fetches patent abstracts and claims from the USPTO's PatentsView API.
Free, no authentication required. Rate limit: 45 requests/minute.

API docs: https://api.patentsview.org/patent/
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.ingestion.source_fetch import record_source_fetch_async

logger = logging.getLogger(__name__)

PATENTSVIEW_BASE = "https://api.patentsview.org/patent"
RATE_LIMIT_RPS = 45 / 60  # 45 requests per minute = 0.75 req/sec
MIN_DELAY = 1.0 / RATE_LIMIT_RPS  # ~1.33 seconds between requests

_request_times: list[float] = []


def _rate_limit() -> None:
    """Sleep if needed to stay within the 45 req/min rate limit."""
    global _request_times
    now = time.monotonic()
    _request_times = [t for t in _request_times if now - t < 60]
    if len(_request_times) >= 45:
        sleep_for = _request_times[0] + 60 - now + 0.5
        if sleep_for > 0:
            time.sleep(sleep_for)
            _request_times = [t for t in _request_times if time.monotonic() - t < 60]
    _request_times.append(time.monotonic())


@dataclass
class PatentData:
    abstract: str | None = None
    claims: str | None = None
    title: str | None = None


class PatentsViewClient:
    """HTTP client for the PatentsView API with rate limiting and retries."""

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def fetch_abstract(self, patent_number: str) -> str | None:
        """Fetch the abstract for a single patent by publication number."""
        data = self._get_patent(patent_number, fields=["patent_abstract"])
        if not data:
            return None
        return data[0].get("patent_abstract") or None

    def fetch_claims(self, patent_number: str) -> str | None:
        """Fetch claims text for a single patent."""
        data = self._get_patent(patent_number, fields=["patent_claims"])
        if not data:
            return None
        claims_list = data[0].get("patent_claims") or []
        if not claims_list:
            return None
        return "\n\n".join(
            f"{c.get('claim_sequence', '')}. {c.get('claim_text', '')}"
            for c in claims_list
            if c.get("claim_text")
        )

    def fetch_bulk(self, patent_numbers: list[str]) -> dict[str, PatentData]:
        """Fetch abstracts and claims for multiple patents in one request."""
        results: dict[str, PatentData] = {}
        if not patent_numbers:
            return results

        query = {
            "q": {"patent_number": patent_numbers},
            "f": ["patent_number", "patent_title", "patent_abstract", "patent_claims"],
            "o": {"page": 1, "per_page": min(len(patent_numbers), 1000)},
        }

        start = time.monotonic()
        _rate_limit()

        try:
            resp = self._client.post(
                f"{PATENTSVIEW_BASE}/query",
                json=query,
                headers={"Content-Type": "application/json"},
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            if resp.status_code != 200:
                asyncio.run(
                    record_source_fetch_async(
                        provider="patentsview",
                        target_type="bulk",
                        status="failed",
                        http_status=resp.status_code,
                        error_message=resp.text[:500],
                        duration_ms=duration_ms,
                    )
                )
                logger.warning(
                    "PatentsView bulk query failed: %s — %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return results

            data = resp.json()
            patents = data.get("patents") or []

            asyncio.run(
                record_source_fetch_async(
                    provider="patentsview",
                    target_type="bulk",
                    status="success",
                    http_status=resp.status_code,
                    records_found=len(patents),
                    duration_ms=duration_ms,
                )
            )

            for p in patents:
                pn = p.get("patent_number", "")
                claims_list = p.get("patent_claims") or []
                claims_text = (
                    "\n\n".join(
                        f"{c.get('claim_sequence', '')}. {c.get('claim_text', '')}"
                        for c in claims_list
                        if c.get("claim_text")
                    )
                    or None
                )
                results[pn] = PatentData(
                    abstract=p.get("patent_abstract") or None,
                    claims=claims_text,
                    title=p.get("patent_title") or None,
                )
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            asyncio.run(
                record_source_fetch_async(
                    provider="patentsview",
                    target_type="bulk",
                    status="failed",
                    error_message=str(e)[:500],
                    duration_ms=duration_ms,
                )
            )
            logger.exception("PatentsView bulk query exception")

        return results

    def _get_patent(
        self, patent_number: str, fields: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch a single patent by number."""
        all_fields = ["patent_number"] + fields
        query = {
            "q": {"patent_number": patent_number},
            "f": all_fields,
            "o": {"page": 1, "per_page": 1},
        }

        start = time.monotonic()
        _rate_limit()

        try:
            resp = self._client.post(
                f"{PATENTSVIEW_BASE}/query",
                json=query,
                headers={"Content-Type": "application/json"},
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            if resp.status_code != 200:
                asyncio.run(
                    record_source_fetch_async(
                        provider="patentsview",
                        target_type="abstract" if "abstract" in fields else "claims",
                        target_id=patent_number,
                        status="failed",
                        http_status=resp.status_code,
                        error_message=resp.text[:500],
                        duration_ms=duration_ms,
                    )
                )
                return []

            data = resp.json()
            patents = data.get("patents") or []

            asyncio.run(
                record_source_fetch_async(
                    provider="patentsview",
                    target_type="abstract" if "abstract" in fields else "claims",
                    target_id=patent_number,
                    status="success",
                    http_status=resp.status_code,
                    records_found=len(patents),
                    duration_ms=duration_ms,
                )
            )

            return patents
        except Exception as e:
            logger.debug("PatentsView fetch error for %s: %s", patent_number, e)
            return []


# ── Bulk convenience ─────────────────────────────────────────────


def fetch_patentsview_bulk(
    patent_numbers: list[str],
) -> dict[str, PatentData]:
    """Fetch abstracts and claims for a batch of patents from PatentsView."""
    with PatentsViewClient() as client:
        return client.fetch_bulk(patent_numbers)
