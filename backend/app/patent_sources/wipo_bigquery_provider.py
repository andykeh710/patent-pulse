"""
WIPO provider via Google Patents BigQuery public dataset.

Uses `patents-public-data.patents.publications` (free up to 1TB/mo).
This is the PRIMARY WIPO acquisition path for V1.

Requires:
- GOOGLE_CLOUD_PROJECT env var (must be set with billing enabled)
- GOOGLE_APPLICATION_CREDENTIALS pointing to a service account JSON
- BigQuery API enabled on the project

WIPO acquisition ladder (V1):
  1. Google Patents BigQuery (this provider — main path)
  2. EPO OPS family lookup for WO records in EP families
  3. Known-record fetch by WO publication number
  4. (V1.1, Enterprise-gated) ScrapeGraphAI fallback
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date, datetime, timezone
from typing import Any

from app.config import settings
from app.patent_sources.base import BasePatentProvider
from app.patent_sources.registry import register

logger = logging.getLogger(__name__)

# Table references in the public dataset
WIPO_TABLE = "patents-public-data.patents.publications"

# Columns we fetch from BigQuery for each WO publication
WIPO_COLUMNS = [
    "publication_number",
    "title_localized",
    "abstract_localized",
    "claims_localized",
    "ipc",
    "cpc",
    "family_id",
    "publication_date",
    "filing_date",
    "priority_date",
    "assignee",
    "inventor",
    "country_code",
    "kind_code",
    "application_number",
]


class BigQueryWIPOProvider(BasePatentProvider):
    """WIPO acquisition via Google Patents BigQuery public dataset."""

    name = "wipo_bigquery"

    def __init__(self):
        self._client = None
        self._project: str | None = None
        self._ready: bool | None = None  # tri-state: None=unchecked

    def _ensure_client(self) -> bool:
        """Lazy-init BigQuery client. Returns True if ready."""
        if self._ready is True:
            return True
        if self._ready is False:
            return False

        project = getattr(settings, "google_cloud_project", None)
        if not project:
            logger.warning(
                "BigQueryWIPOProvider: GOOGLE_CLOUD_PROJECT not set. "
                "Set this env var to a GCP project ID with BigQuery API enabled."
            )
            self._ready = False
            return False

        try:
            from google.cloud import bigquery
        except ImportError:
            logger.warning(
                "BigQueryWIPOProvider: google-cloud-bigquery not installed."
            )
            self._ready = False
            return False

        try:
            self._client = bigquery.Client(project=project)
            self._project = project
            self._ready = True
            logger.info("BigQueryWIPOProvider initialized for project %s", project)
            return True
        except Exception as e:
            logger.warning(
                "BigQueryWIPOProvider: failed to create BigQuery client — "
                "check GOOGLE_APPLICATION_CREDENTIALS and project billing: %s", e
            )
            self._ready = False
            return False

    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        if not self._ensure_client():
            return None

        clean = publication_number.replace("WO", "").replace("/", "").strip()
        query = f"""
            SELECT {', '.join(WIPO_COLUMNS)}
            FROM `{WIPO_TABLE}`
            WHERE country_code = 'WO'
              AND publication_number = @pub_num
            LIMIT 1
        """

        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pub_num", "STRING", clean)]
        )

        try:
            rows = list(self._client.query(query, job_config=job_config).result())
            if not rows:
                return None
            return self._row_to_dict(rows[0])
        except Exception as e:
            logger.warning("BigQueryWIPO fetch_by_publication_number failed: %s", e)
            return None

    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        if not self._ensure_client():
            return

        date_str = publication_date.isoformat()
        query = f"""
            SELECT {', '.join(WIPO_COLUMNS)}
            FROM `{WIPO_TABLE}`
            WHERE country_code = 'WO'
              AND publication_date >= TIMESTAMP(@start_date)
              AND publication_date < TIMESTAMP_ADD(TIMESTAMP(@start_date), INTERVAL 1 DAY)
            ORDER BY publication_date DESC
            LIMIT @limit
        """

        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "STRING", date_str),
                bigquery.ScalarQueryParameter("limit", "INT64", max_results),
            ]
        )

        try:
            rows = self._client.query(query, job_config=job_config).result()
            for row in rows:
                yield self._row_to_dict(row)
        except Exception as e:
            logger.warning("BigQueryWIPO search_by_date failed: %s", e)

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Normalize a BigQuery row to the standard provider dict format."""
        pub_num = getattr(row, "publication_number", "")
        if pub_num and not pub_num.startswith("WO"):
            pub_num = f"WO{pub_num}"

        title = getattr(row, "title_localized", None)
        abstract = getattr(row, "abstract_localized", None)
        if isinstance(title, list):
            title = next((t.get("text", "") for t in title if t.get("language") == "en"), str(title))
        elif isinstance(title, dict):
            title = title.get("text", str(title))
        if isinstance(abstract, list):
            abstract = next((a.get("text", "") for a in abstract if a.get("language") == "en"), "")
        elif isinstance(abstract, dict):
            abstract = abstract.get("text", "")

        ipc = getattr(row, "ipc", None) or []
        if isinstance(ipc, list) and ipc and isinstance(ipc[0], dict):
            ipc = [c.get("code", str(c)) for c in ipc]
        cpc = getattr(row, "cpc", None) or []
        if isinstance(cpc, list) and cpc and isinstance(cpc[0], dict):
            cpc = [c.get("code", str(c)) for c in cpc]

        assignees = getattr(row, "assignee", None) or []
        if isinstance(assignees, list) and assignees and isinstance(assignees[0], dict):
            assignees = [a.get("name", str(a)) for a in assignees]
        inventors = getattr(row, "inventor", None) or []
        if isinstance(inventors, list) and inventors and isinstance(inventors[0], dict):
            inventors = [i.get("name", str(i)) for i in inventors]

        pub_date = getattr(row, "publication_date", None)
        if isinstance(pub_date, datetime):
            pub_date = pub_date.date()
        filing_date = getattr(row, "filing_date", None)
        if isinstance(filing_date, datetime):
            filing_date = filing_date.date()
        priority_date = getattr(row, "priority_date", None)
        if isinstance(priority_date, datetime):
            priority_date = priority_date.date()

        return {
            "publication_number": pub_num,
            "application_number": getattr(row, "application_number", ""),
            "kind_code": getattr(row, "kind_code", ""),
            "office": "WIPO",
            "title": str(title) if title else None,
            "abstract": str(abstract) if abstract else None,
            # claims_localized can be a complex nested dict — skip for now
            "claims_text": None,
            "ipc_codes": [{"code": str(c)} for c in ipc] if ipc else [],
            "cpc_codes": [{"code": str(c)} for c in cpc] if cpc else [],
            "assignees": assignees if isinstance(assignees, list) else [],
            "inventors": inventors if isinstance(inventors, list) else [],
            "family_id": str(getattr(row, "family_id", "")) or None,
            "publication_date": pub_date.isoformat() if pub_date else None,
            "filing_date": filing_date.isoformat() if filing_date else None,
            "priority_date": priority_date.isoformat() if priority_date else None,
            "country_code": getattr(row, "country_code", "WO"),
        }


# Auto-register if GCP seems configured (checked at first fetch time).
# The provider itself will log warnings if GCP isn't ready.
register(BigQueryWIPOProvider.name, BigQueryWIPOProvider())
