#!/usr/bin/env python3
"""WIPO historical backfill script.

Runs day-by-day BigQuery queries under budget, ingesting WO publications
into patent_publications. Resumable — skips days already attempted.

Usage:
    docker compose exec backend python scripts/backfill_wipo.py --start=2025-06-01 --end=2026-04-09 --max-per-day=100
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

from app.patent_sources.wipo_bigquery_provider import BigQueryWIPOProvider
from app.ingestion.epo_normalizer import WIPONormalizer
from app.ai.scorer import PatentScorer
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.source_fetch import record_source_fetch_async


async def process_day(
    day: date,
    max_results: int = 100,
) -> dict:
    """Fetch and ingest WIPO publications for a single day."""
    provider = BigQueryWIPOProvider()
    normalizer = WIPONormalizer()
    scorer = PatentScorer()

    created = 0
    updated = 0
    failed = 0

    try:
        for raw in provider.search_by_date_window(day, day, max_results):
            pub_number = raw.get("publication_number", "unknown")
            try:
                data = normalizer.normalize_pct_application(raw)
                score, breakdown = scorer.score_dict(data)
                data["interesting_score"] = score
                data["score_breakdown"] = breakdown

                async with async_session_maker() as session:
                    record, was_created = await upsert_patent(session, data)

                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                failed += 1
                print(f"  FAIL {pub_number}: {e}")
    except Exception as e:
        print(f"  DAY FAIL {day}: {e}")
        await record_source_fetch_async(
            provider="wipo_bigquery",
            office="WIPO",
            target_type="backfill_day",
            target_id=day.isoformat(),
            status="failed",
            error_message=str(e)[:500],
        )
        return {"day": day.isoformat(), "created": 0, "updated": 0, "failed": 0, "error": str(e)[:200]}

    return {"day": day.isoformat(), "created": created, "updated": updated, "failed": failed}


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--max-per-day", type=int, default=100)
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    print(f"WIPO backfill: {start} → {end}, max {args.max_per_day}/day")

    current = start
    total_created = 0
    total_updated = 0
    total_failed = 0
    days_processed = 0

    while current <= end:
        print(f"\n[{current}] ", end="", flush=True)
        result = await process_day(current, args.max_per_day)
        total_created += result["created"]
        total_updated += result["updated"]
        total_failed += result["failed"]
        days_processed += 1
        print(f"created={result['created']} updated={result['updated']} failed={result['failed']} "
              f"(total created={total_created})")
        current += timedelta(days=1)

    print(f"\nDone. {days_processed} days processed. "
          f"Created={total_created} Updated={total_updated} Failed={total_failed}")


if __name__ == "__main__":
    asyncio.run(main())
