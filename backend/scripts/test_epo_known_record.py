"""
Test script: fetch a known EP publication via EPO OPS to diagnose ingestion.

Usage: docker compose exec backend python scripts/test_epo_known_record.py
"""
from __future__ import annotations

import asyncio
import json
import sys

from app.ingestion.epo_client import EPOClient
from app.ingestion.epo_normalizer import EPONormalizer
from app.ingestion.source_fetch import record_source_fetch_async

KNOWN_EP = "EP4000000A1"  # A real, recent EP publication


async def main():
    print(f"Testing EPO OPS fetch for: {KNOWN_EP}")

    # 1. Fetch raw biblio
    try:
        with EPOClient() as client:
            raw = client.fetch_publication(KNOWN_EP)
            print("\n--- Raw response keys ---")
            if isinstance(raw, dict):
                print(json.dumps(list(raw.keys()), indent=2))
                # Show a snippet of the structure
                wpd = raw.get("ops:world-patent-data", {})
                biblio = wpd.get("exchange-documents", wpd.get("exchange-document", {}))
                if isinstance(biblio, list):
                    biblio = biblio[0] if biblio else {}
                bd = biblio.get("bibliographic-data", {})
                pub_ref = bd.get("publication-reference", {})
                print("\n--- Publication reference ---")
                print(json.dumps(pub_ref, indent=2)[:500])
            else:
                print(f"Unexpected response type: {type(raw)}")

            # 2. Normalize
            normalizer = EPONormalizer()
            if isinstance(raw, dict):
                data = normalizer.normalize_publication(raw)
                print("\n--- Normalized fields ---")
                for k in sorted(data.keys()):
                    v = data[k]
                    if isinstance(v, str) and len(v) > 100:
                        v = v[:100] + "..."
                    elif isinstance(v, list) and len(v) > 3:
                        v = v[:3]
                    print(f"  {k}: {v}")

            # 3. Log source fetch
            await record_source_fetch_async(
                provider="epo_ops",
                office="EP",
                target_type="publication",
                target_id=KNOWN_EP,
                source_url=f"https://ops.epo.org/3.2/rest-services/published-data/publication/epodoc/{KNOWN_EP}/biblio",
                status="success",
                http_status=200,
                records_found=1,
            )
            print("\nSource fetch logged successfully")

            # 4. Test search by date
            from datetime import date, timedelta
            yesterday = date.today() - timedelta(days=1)
            print(f"\n--- Testing search by date: {yesterday} ---")
            with EPOClient() as client:
                count = 0
                for pub in client.fetch_publications_by_date(yesterday):
                    count += 1
                    if count == 1:
                        print(f"  First result: {pub.get('publication_number', '?')}")
                    if count >= 3:
                        break
                print(f"  Total results in first page: {count}")

            # 5. Test last Wednesday
            from app.ingestion.epo_client import get_last_wednesday
            lw = get_last_wednesday()
            print(f"\n--- Testing last Wednesday: {lw} ---")
            with EPOClient() as client:
                count = 0
                for pub in client.fetch_publications_by_date(lw):
                    count += 1
                    if count == 1:
                        print(f"  First result: {pub.get('publication_number', '?')}")
                    if count >= 5:
                        break
                print(f"  Total results in first page: {count}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        await record_source_fetch_async(
            provider="epo_ops",
            office="EP",
            target_type="publication",
            target_id=KNOWN_EP,
            status="failed",
            error_message=str(e)[:500],
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
