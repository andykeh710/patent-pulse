"""
WIPO provider via Google Patents BigQuery public dataset.

Uses `patents-public-data.patents.publications` (free up to 1TB/mo).
This is the PRIMARY WIPO acquisition path for V1.

BigQuery Row schema (positional):
  0:  publication_number    str  "WO-2026075437-A1"
  1:  application_number    str  "KR-2025015308-W"
  2:  country_code          str  "WO"
  3:  kind_code             str  "A1"
  8:  publication_number_v2 str  "WO2026075437A1"
  10: title_localized       list [{text, language, truncated}]
  11: abstract_localized    list [{text, language, truncated}]
  12: claims_localized      list [{text, language, truncated}]
  16: publication_date      int  20260409 (YYYYMMDD)
  17: filing_date           int  20250929 (YYYYMMDD)
  19: priority_date         int  20241002 (YYYYMMDD)
  23: inventor_harmonized   list [str] (names as strings)
  25: assignee_harmonized   list [str] (names as strings)
  28: ipc                   list [{code, inventive, first}]
  29: cpc                   list [{code, inventive, first}]
  36: family_id             int

Requires:
- GOOGLE_CLOUD_PROJECT env var
- GOOGLE_APPLICATION_CREDENTIALS service account JSON
- BigQuery API enabled
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

from app.config import settings
from app.patent_sources.base import BasePatentProvider
from app.patent_sources.registry import register

logger = logging.getLogger(__name__)

WIPO_TABLE = "patents-public-data.patents.publications"

# Hard ceiling: 100 GB billed bytes per query (free tier allows 1TB/month)
MAX_BYTES_BILLED = 100_000_000_000


def _int_date_to_str(d: int | None) -> str | None:
    """Convert YYYYMMDD int to ISO date string."""
    if not d:
        return None
    s = str(d)
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return None


def _localized_text(items: list[dict] | None, lang: str = "en") -> str | None:
    """Extract text in a given language from a localized-text list."""
    if not items:
        return None
    for item in items:
        if isinstance(item, dict) and item.get("language") == lang:
            return item.get("text")
    return None


class BigQueryWIPOProvider(BasePatentProvider):
    """WIPO acquisition via Google Patents BigQuery public dataset."""

    name = "wipo_bigquery"

    def __init__(self):
        self._client = None
        self._project: str | None = None
        self._ready: bool | None = None

    def _ensure_client(self) -> bool:
        if self._ready is True:
            return True
        if self._ready is False:
            return False

        project = getattr(settings, "google_cloud_project", None)
        if not project:
            logger.warning(
                "BigQueryWIPOProvider: GOOGLE_CLOUD_PROJECT not set."
            )
            self._ready = False
            return False

        try:
            from google.cloud import bigquery
        except ImportError:
            logger.warning("BigQueryWIPOProvider: google-cloud-bigquery not installed.")
            self._ready = False
            return False

        try:
            self._client = bigquery.Client(project=project)
            self._project = project
            self._ready = True
            logger.info("BigQueryWIPOProvider initialized for project %s", project)
            return True
        except Exception as e:
            logger.warning("BigQueryWIPOProvider: client init failed: %s", e)
            self._ready = False
            return False

    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        if not self._ensure_client():
            return None
        from google.cloud import bigquery

        clean = publication_number.replace("WO", "").replace("-", "").replace("/", "").strip()
        query = f"""
            SELECT
                publication_number, application_number, country_code, kind_code,
                spif_publication_number, title_localized,
                publication_date, filing_date, priority_date, family_id
            FROM `{WIPO_TABLE}`
            WHERE country_code = 'WO'
              AND REGEXP_REPLACE(publication_number, r'[^0-9A-Z]', '') = @pn
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("pn", "STRING", f"WO{clean}A1")],
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )
        try:
            rows = list(self._client.query(query, job_config=job_config).result())
            if not rows:
                return None
            return self._row_to_dict(list(rows[0]))
        except Exception as e:
            logger.warning("BigQueryWIPO fetch_by_number failed for %s: %s", publication_number, e)
            return None

    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Base interface — delegates to date window for a single day."""
        yield from self.search_by_date_window(
            publication_date, publication_date, max_results
        )

    def search_by_date_window(
        self,
        start_date: date,
        end_date: date,
        max_results: int = 100,
    ) -> Iterator[dict[str, Any]]:
        """Fetch WIPO publications within a date window.

        Iterates one day at a time to keep per-query bytes under 5 GB.
        Yields normalized dicts suitable for the dedup/upsert pipeline.
        Each day records to source_fetches.
        """
        if not self._ensure_client():
            return

        import asyncio
        import time as _time

        from google.cloud import bigquery

        current = start_date
        total_yielded = 0

        while current <= end_date and total_yielded < max_results:
            day_int = int(current.strftime("%Y%m%d"))
            remaining = max_results - total_yielded

            query = f"""
                SELECT
                    publication_number, application_number, country_code, kind_code,
                    spif_publication_number, title_localized,
                    publication_date, filing_date, priority_date, family_id
                FROM `{WIPO_TABLE}`
                WHERE country_code = 'WO'
                  AND publication_date = @day
                ORDER BY publication_date DESC
                LIMIT @limit
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("day", "INT64", day_int),
                    bigquery.ScalarQueryParameter("limit", "INT64", remaining),
                ],
                maximum_bytes_billed=MAX_BYTES_BILLED,
            )

            _start = _time.monotonic()
            records_found = 0
            status = "success"
            error_msg = None

            try:
                job = self._client.query(query, job_config=job_config)
                rows = list(job.result())
                records_found = len(rows)
                for row in rows:
                    yield self._row_to_dict(list(row))
                    total_yielded += 1
            except Exception as e:
                status = "failed"
                error_msg = str(e)[:2000]
                logger.warning(
                    "BigQueryWIPO day %s failed: %s", current.isoformat(), e
                )
            finally:
                _dur = int((_time.monotonic() - _start) * 1000)
                try:
                    asyncio.ensure_future(self._record_fetch(
                        target_type="search_by_date",
                        target_id=current.isoformat(),
                        status=status,
                        records_found=records_found,
                        error_message=error_msg,
                        duration_ms=_dur,
                    ))
                except RuntimeError:
                    pass

            if status == "failed":
                break  # stop on first fatal error
            current += timedelta(days=1)

    async def _record_fetch(self, **kwargs):
        try:
            from app.ingestion.source_fetch import record_source_fetch_async
            await record_source_fetch_async(
                provider=self.name,
                office="WIPO",
                **kwargs,
            )
        except Exception:
            logger.debug("Failed to record WIPO source fetch", exc_info=True)

    def _row_to_dict(self, row: list) -> dict[str, Any]:
        """Normalize a BigQuery row (as list) to the standard provider dict.

        Row indices from narrowed SELECT:
          0: publication_number       (WO-2026075437-A1)
          1: application_number
          2: country_code
          3: kind_code
          4: spif_publication_number  (WO2026075437A1 — no hyphens)
          5: title_localized          list[{text, language, truncated}]
          6: publication_date         int (YYYYMMDD)
          7: filing_date              int (YYYYMMDD)
          8: priority_date            int (YYYYMMDD)
          9: family_id                str or int
        """
        pub_num = row[4] if row[4] else row[0]
        if isinstance(pub_num, str):
            pub_num = pub_num.replace("-", "").strip()

        title = _localized_text(row[5] if len(row) > 5 else None)

        pub_date = _int_date_to_str(row[6] if len(row) > 6 else None)
        filing_date = _int_date_to_str(row[7] if len(row) > 7 else None)
        priority_date = _int_date_to_str(row[8] if len(row) > 8 else None)

        family_id = None
        if len(row) > 9 and row[9]:
            family_id = f"bigquery:{row[9]}"

        return {
            "publication_number": pub_num or "",
            "application_number": row[1] if len(row) > 1 else "",
            "kind_code": row[3] if len(row) > 3 else "",
            "office": "WIPO",
            "title": title,
            "abstract": None,
            "claims_text": None,
            "ipc_codes": [],
            "cpc_codes": [],
            "applicants": [],
            "inventors": [],
            "family_id": family_id,
            "publication_date": pub_date,
            "filing_date": filing_date,
            "priority_date": priority_date,
        }


# Auto-register
register(BigQueryWIPOProvider.name, BigQueryWIPOProvider())
