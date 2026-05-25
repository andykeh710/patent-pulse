import logging
from collections.abc import Iterator
from datetime import date, timedelta

from patent_client import PatentBiblio, PublishedApplicationBiblio

from app.config import settings
from app.core.exceptions import IngestionError, TransientIngestionError

logger = logging.getLogger(__name__)


class USPTOClient:
    """Client for fetching patent data from USPTO Open Data Portal."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.uspto_api_key

    def fetch_grants_by_date(self, grant_date: date) -> Iterator[dict]:
        """
        Fetch all patents granted on a specific date.

        Args:
            grant_date: The grant date to fetch (typically a Tuesday)

        Yields:
            Raw patent data dictionaries
        """
        logger.info(f"Fetching grants for date: {grant_date}")

        try:
            patents = PatentBiblio.objects.filter(issue_date=grant_date.strftime("%Y-%m-%d"))

            for patent in patents:
                try:
                    yield self._patent_to_dict(patent)
                except Exception as e:
                    logger.warning(f"Failed to process patent {getattr(patent, 'publication_number', '?')}: {e}")
                    continue

        except ConnectionError as e:
            raise TransientIngestionError(f"USPTO connection error: {e}") from e
        except Exception as e:
            raise IngestionError(f"Failed to fetch grants: {e}") from e

    def fetch_applications_by_date(self, publication_date: date) -> Iterator[dict]:
        """
        Fetch all published applications on a specific date.

        Args:
            publication_date: The publication date to fetch (typically a Thursday)

        Yields:
            Raw application data dictionaries
        """
        logger.info(f"Fetching applications for date: {publication_date}")

        try:
            apps = PublishedApplicationBiblio.objects.filter(
                publication_date=publication_date.strftime("%Y-%m-%d")
            )

            for app in apps:
                try:
                    yield self._application_to_dict(app)
                except Exception as e:
                    logger.warning(f"Failed to process application {getattr(app, 'publication_number', '?')}: {e}")
                    continue

        except ConnectionError as e:
            raise TransientIngestionError(f"USPTO connection error: {e}") from e
        except Exception as e:
            raise IngestionError(f"Failed to fetch applications: {e}") from e

    def fetch_grants_range(self, start_date: date, end_date: date) -> Iterator[dict]:
        """Fetch grants across a date range."""
        current = start_date
        while current <= end_date:
            yield from self.fetch_grants_by_date(current)
            current += timedelta(days=1)

    def fetch_applications_range(self, start_date: date, end_date: date) -> Iterator[dict]:
        """Fetch applications across a date range."""
        current = start_date
        while current <= end_date:
            yield from self.fetch_applications_by_date(current)
            current += timedelta(days=1)

    def _patent_to_dict(self, patent) -> dict:
        """Convert PatentBiblio object to dictionary."""
        pub_num = getattr(patent, "publication_number", None) or ""

        citations = []
        if settings.uspto_fetch_citations:
            citations = self._fetch_forward_citations(patent)

        return {
            "patent_number": pub_num,
            "publication_number": pub_num,
            "application_number": getattr(patent, "appl_id", None),
            "kind_code": "B2",
            "filing_date": self._format_date(getattr(patent, "app_filing_date", None)),
            "issue_date": self._format_date(getattr(patent, "publication_date", None)),
            "priority_date": None,
            "invention_title": getattr(patent, "patent_title", None),
            "abstract_text": None,
            "claims": None,
            "description": None,
            "assignees": [{"assignee_name": n} for n in (getattr(patent, "assignee_names", None) or [])],
            "inventors": [{"inventor_name": n} for n in (getattr(patent, "applicant_names", None) or [])],
            "cpc_codes": [{"code": c} for c in (getattr(patent, "cpc_additional", None) or [])],
            "ipc_codes": [{"code": c} for c in (getattr(patent, "ipc_code", None) or [])],
            # Sprint 6.5: populated when settings.uspto_fetch_citations=true.
            "citations": citations,
        }

    def _fetch_forward_citations(self, patent) -> list[str]:
        """Fetch forward citation doc IDs with rate-limit retry.

        Iterates PatentBiblio.forward_citations (lazy — 1 USPTO API call).
        Returns list of "USPTO:..." doc_id strings. On failure: logs and returns [].
        """
        import time
        from urllib.error import HTTPError

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                fwd = getattr(patent, "forward_citations", None)
                if fwd is None:
                    return []
                # Ensure rate-limit: 1 call/sec.
                if attempt > 0:
                    time.sleep(2 ** attempt)
                return [
                    f"USPTO:{getattr(c, 'publication_number', '')}"
                    for c in fwd
                    if getattr(c, "publication_number", None)
                ]
            except HTTPError as e:
                if e.code == 429 and attempt < max_retries:
                    backoff = 2 ** (attempt + 1)
                    logger.warning(
                        "Rate-limited fetching citations (429). "
                        "Retry %d/%d after %ds.",
                        attempt + 1, max_retries, backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "Failed to fetch citations for %s (attempt %d): %s",
                        getattr(patent, "publication_number", "?"),
                        attempt, e,
                    )
                    return []
            except Exception as e:
                logger.error(
                    "Failed to fetch citations for %s: %s",
                    getattr(patent, "publication_number", "?"), e,
                )
                return []

        return []

    def _application_to_dict(self, app) -> dict:
        """Convert PublishedApplicationBiblio object to dictionary."""
        pub_num = getattr(app, "publication_number", None) or ""
        return {
            "publication_number": pub_num,
            "application_number": getattr(app, "appl_id", None),
            "kind_code": "A1",
            "filing_date": self._format_date(getattr(app, "app_filing_date", None)),
            "publication_date": self._format_date(getattr(app, "publication_date", None)),
            "priority_date": None,
            "invention_title": getattr(app, "patent_title", None),
            "abstract_text": None,
            "claims": None,
            "assignees": [{"assignee_name": n} for n in (getattr(app, "assignee_names", None) or [])],
            "inventors": [{"inventor_name": n} for n in (getattr(app, "applicant_names", None) or [])],
            "cpc_codes": [{"code": c} for c in (getattr(app, "cpc_additional", None) or [])],
            "ipc_codes": [{"code": c} for c in (getattr(app, "ipc_code", None) or [])],
        }

    def _format_date(self, dt) -> str | None:
        """Format date to string."""
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        if hasattr(dt, "strftime"):
            return dt.strftime("%Y-%m-%d")
        return str(dt)


def get_last_tuesday(reference_date: date | None = None) -> date:
    """Get the most recent Tuesday before or on the reference date."""
    ref = reference_date or date.today()
    days_since_tuesday = (ref.weekday() - 1) % 7
    return ref - timedelta(days=days_since_tuesday)


def get_last_thursday(reference_date: date | None = None) -> date:
    """Get the most recent Thursday before or on the reference date."""
    ref = reference_date or date.today()
    days_since_thursday = (ref.weekday() - 3) % 7
    return ref - timedelta(days=days_since_thursday)
