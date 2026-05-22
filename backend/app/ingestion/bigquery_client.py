import logging
from collections.abc import Iterator
from datetime import date, timedelta

from google.cloud import bigquery

from app.ai.scorer import PatentScorer
from app.config import settings
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.normalizer import USPTONormalizer

logger = logging.getLogger(__name__)

PATENTS_DATASET = "patents-public-data.patents.publications"
BATCH_SIZE = 1000


class BigQueryClient:
    """
    Client for fetching historical patent data from Google BigQuery public datasets.

    Uses the patents-public-data.patents.publications table for backfill operations.
    Not intended for real-time ingestion.
    """

    def __init__(self, project: str | None = None):
        self.project = project or settings.google_cloud_project
        if not self.project:
            raise ValueError("Google Cloud project not configured")
        self.client = bigquery.Client(project=self.project)

    def fetch_us_patents(
        self,
        start_date: date,
        end_date: date,
        batch_size: int = BATCH_SIZE,
    ) -> Iterator[dict]:
        """
        Fetch US patents from BigQuery within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            batch_size: Number of records per batch

        Yields:
            Raw patent data dictionaries
        """
        query = f"""
        SELECT
            publication_number,
            application_number,
            filing_date,
            publication_date,
            grant_date,
            priority_date,
            title_localized,
            abstract_localized,
            inventor,
            assignee,
            cpc,
            ipc,
            citation,
            family_id
        FROM `{PATENTS_DATASET}`
        WHERE country_code = 'US'
          AND publication_date >= @start_date
          AND publication_date <= @end_date
        ORDER BY publication_date DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "start_date", "INT64", int(start_date.strftime("%Y%m%d"))
                ),
                bigquery.ScalarQueryParameter(
                    "end_date", "INT64", int(end_date.strftime("%Y%m%d"))
                ),
            ]
        )

        logger.info(f"Querying BigQuery for US patents from {start_date} to {end_date}")

        query_job = self.client.query(query, job_config=job_config)

        for row in query_job:
            yield self._row_to_dict(row)

    def _row_to_dict(self, row: bigquery.Row) -> dict:
        """Convert BigQuery row to patent data dictionary."""
        title = self._extract_localized_text(row.get("title_localized"), "en")
        abstract = self._extract_localized_text(row.get("abstract_localized"), "en")

        pub_date_int = row.get("publication_date")
        filing_date_int = row.get("filing_date")
        grant_date_int = row.get("grant_date")
        priority_date_int = row.get("priority_date")

        return {
            "patent_number": row.get("publication_number"),
            "publication_number": row.get("publication_number"),
            "application_number": row.get("application_number"),
            "filing_date": self._int_to_date_str(filing_date_int),
            "publication_date": self._int_to_date_str(pub_date_int),
            "issue_date": self._int_to_date_str(grant_date_int),
            "priority_date": self._int_to_date_str(priority_date_int),
            "invention_title": title,
            "abstract_text": abstract,
            "assignees": self._extract_parties(row.get("assignee"), "name"),
            "inventors": self._extract_parties(row.get("inventor"), "name"),
            "cpc_codes": self._extract_codes(row.get("cpc")),
            "ipc_codes": self._extract_codes(row.get("ipc")),
            "citations": self._extract_citations(row.get("citation")),
            "family_id": row.get("family_id"),
        }

    def _extract_localized_text(
        self, localized_list: list | None, language: str = "en"
    ) -> str | None:
        """Extract text for a specific language from localized array."""
        if not localized_list:
            return None
        for item in localized_list:
            if isinstance(item, dict) and item.get("language") == language:
                return item.get("text")
        if localized_list and isinstance(localized_list[0], dict):
            return localized_list[0].get("text")
        return None

    def _extract_parties(self, parties: list | None, name_field: str) -> list[dict]:
        """Extract party information (assignees or inventors)."""
        if not parties:
            return []
        result = []
        for party in parties:
            if isinstance(party, dict):
                name = party.get(name_field)
                if name:
                    result.append({f"{name_field.replace('name', 'assignee_name')}": name})
        return result

    def _extract_codes(self, codes: list | None) -> list[dict]:
        """Extract classification codes."""
        if not codes:
            return []
        result = []
        for code in codes:
            if isinstance(code, dict):
                code_str = code.get("code")
                if code_str:
                    result.append({"code": code_str})
        return result

    def _extract_citations(self, citations: list | None) -> list[dict]:
        """Extract citation information."""
        if not citations:
            return []
        result = []
        for citation in citations:
            if isinstance(citation, dict):
                cited = citation.get("publication_number")
                if cited:
                    result.append({"cited_document": cited})
        return result

    def _int_to_date_str(self, date_int: int | None) -> str | None:
        """Convert YYYYMMDD integer to date string."""
        if not date_int:
            return None
        date_str = str(date_int)
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return None


async def run_bigquery_backfill(
    years: int = 5,
    batch_size: int = 100,
) -> dict:
    """
    Run historical backfill from BigQuery.

    Args:
        years: Number of years to backfill
        batch_size: Number of records to process before committing

    Returns:
        Stats dict with processed, created, updated, failed counts
    """
    if not settings.google_cloud_project:
        logger.error("GOOGLE_CLOUD_PROJECT not set, cannot run backfill")
        return {"error": "GOOGLE_CLOUD_PROJECT not configured"}

    client = BigQueryClient(project=settings.google_cloud_project)
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    end_date = date.today()
    start_date = end_date - timedelta(days=years * 365)

    stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0}

    logger.info(f"Starting BigQuery backfill from {start_date} to {end_date}")

    batch = []

    for raw in client.fetch_us_patents(start_date, end_date):
        try:
            kind_code = raw.get("publication_number", "")[-2:]
            if kind_code.startswith("B"):
                data = normalizer.normalize_grant(raw)
            else:
                data = normalizer.normalize_application(raw)

            score, breakdown = scorer.score_dict(data)
            data["interesting_score"] = score
            data["score_breakdown"] = breakdown
            data["family_id"] = raw.get("family_id")

            batch.append(data)

            if len(batch) >= batch_size:
                results = await _process_batch(batch)
                stats["created"] += results["created"]
                stats["updated"] += results["updated"]
                stats["failed"] += results["failed"]
                stats["processed"] += len(batch)
                batch = []

                logger.info(f"Backfill progress: {stats['processed']} processed")

        except Exception as e:
            stats["failed"] += 1
            logger.warning(f"Failed to process record: {e}")

    if batch:
        results = await _process_batch(batch)
        stats["created"] += results["created"]
        stats["updated"] += results["updated"]
        stats["failed"] += results["failed"]
        stats["processed"] += len(batch)

    logger.info(f"BigQuery backfill complete: {stats}")
    return stats


async def _process_batch(batch: list[dict]) -> dict:
    """Process a batch of patents."""
    results = {"created": 0, "updated": 0, "failed": 0}

    async with async_session_maker() as session:
        for data in batch:
            try:
                _, created = await upsert_patent(session, data)
                if created:
                    results["created"] += 1
                else:
                    results["updated"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"Failed to upsert: {e}")

    return results
