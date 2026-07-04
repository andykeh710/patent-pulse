"""
Citation & Family Diagnostic Script.

Tests 5 diverse patent types (US-A1, US-B1, EP-A1, EP-B1, WO-A1)
against EPO OPS citation + family endpoints and the USPTO patent_client
SDK. Captures raw HTTP responses to source_fetches for debugging.

Usage:
    cd /opt/invention-index-8
    docker compose exec backend python -m app.tools.diagnose_citations
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from app.config import settings
from app.ingestion.source_fetch import record_source_fetch_async

logger = logging.getLogger(__name__)

# One of each major patent type
TEST_PATENTS = [
    {"number": "US12000000B2", "office": "USPTO", "kind": "B2", "label": "US-B2 (grant)"},
    {"number": "US20240144033A1", "office": "USPTO", "kind": "A1", "label": "US-A1 (application)"},
    {"number": "EP4000000B1", "office": "EPO", "kind": "B1", "label": "EP-B1 (grant)"},
    {"number": "EP4250000A1", "office": "EPO", "kind": "A1", "label": "EP-A1 (application)"},
    {"number": "WO2024000000A1", "office": "WIPO", "kind": "A1", "label": "WO-A1 (PCT)"},
]


async def diagnose_all() -> dict:
    """Run full diagnostic and return results."""
    results = {"citations": {}, "family": {}}

    for patent in TEST_PATENTS:
        label = patent["label"]
        pub = patent["number"]

        # ── Citation test ──
        print(f"\n{'=' * 60}")
        print(f"Testing citations: {label} ({pub})")
        print(f"{'=' * 60}")

        try:
            cit_result = await _test_citations(pub, label)
            results["citations"][label] = cit_result
            print(f"  Result: {json.dumps(cit_result, indent=2)}")
        except Exception as e:
            results["citations"][label] = {"error": str(e)}
            print(f"  ERROR: {e}")

        # ── Family test ──
        print(f"\nTesting family: {label} ({pub})")

        try:
            fam_result = await _test_family(pub, label)
            results["family"][label] = fam_result
            print(f"  Result: {json.dumps(fam_result, indent=2)}")
        except Exception as e:
            results["family"][label] = {"error": str(e)}
            print(f"  ERROR: {e}")

        time.sleep(1.0)  # Rate limit

    return results


async def _test_citations(pub_number: str, label: str) -> dict:
    """Test the patent_client SDK for forward citations."""
    start = time.monotonic()
    try:
        from patent_client import PatentBiblio

        patent = PatentBiblio.objects.get(pub_number)

        citations = []
        for cit in getattr(patent, "forward_citations", []) or []:
            num = getattr(cit, "publication_number", None)
            if num:
                citations.append(f"USPTO:{num}")

        duration_ms = int((time.monotonic() - start) * 1000)

        # Record raw response summary to source_fetches
        raw = f"patent_client response: found={len(citations)} forward_citations"
        await record_source_fetch_async(
            provider="uspto_patent_client",
            target_type="citation_test",
            target_id=pub_number,
            status="success",
            records_found=len(citations),
            duration_ms=duration_ms,
            error_message=raw[:500],
        )

        return {"count": len(citations), "sample": citations[:5], "label": label}

    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        error_str = str(e)[:2000]

        await record_source_fetch_async(
            provider="uspto_patent_client",
            target_type="citation_test",
            target_id=pub_number,
            status="failed",
            duration_ms=duration_ms,
            error_message=error_str[:2000],
        )

        return {"error": type(e).__name__, "message": error_str[:500], "label": label}


async def _test_family(pub_number: str, label: str) -> dict:
    """Test EPO OPS family endpoint."""
    start = time.monotonic()

    if not settings.epo_ops_client_id:
        return {"error": "EPO credentials not configured", "label": label}

    try:
        from app.ingestion.epo_client import EPOClient

        with EPOClient() as client:
            family_data = client.fetch_family(pub_number)

        duration_ms = int((time.monotonic() - start) * 1000)

        # Extract family ID and member count
        family_id = None
        member_count = 0
        if isinstance(family_data, dict):
            patent_family = family_data.get("ops:world-patent-data", {}).get(
                "ops:patent-family", {}
            )
            family_id = patent_family.get("@family-id")
            members = patent_family.get("ops:family-member", [])
            member_count = len(members) if isinstance(members, list) else 1

        raw_summary = (
            f"family_id={family_id}, members={member_count}, "
            f"keys={list(family_data.keys())[:5] if isinstance(family_data, dict) else 'not_dict'}"
        )

        await record_source_fetch_async(
            provider="epo_ops",
            target_type="family_test",
            target_id=pub_number,
            status="success" if family_id else "empty",
            records_found=member_count,
            duration_ms=duration_ms,
            error_message=raw_summary[:2000],
        )

        return {
            "family_id": family_id,
            "member_count": member_count,
            "label": label,
        }

    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        error_str = str(e)[:2000]

        await record_source_fetch_async(
            provider="epo_ops",
            target_type="family_test",
            target_id=pub_number,
            status="failed",
            duration_ms=duration_ms,
            error_message=error_str[:2000],
        )

        return {"error": type(e).__name__, "message": error_str[:500], "label": label}


if __name__ == "__main__":
    print("Citation & Family Diagnostic")
    print("=" * 60)
    results = asyncio.run(diagnose_all())

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    citation_ok = sum(
        1 for r in results["citations"].values() if "error" not in r and r.get("count", 0) > 0
    )
    family_ok = sum(
        1 for r in results["family"].values() if "error" not in r and r.get("family_id")
    )

    print(f"Citations working: {citation_ok}/{len(TEST_PATENTS)}")
    print(f"Family working: {family_ok}/{len(TEST_PATENTS)}")

    if citation_ok == 0:
        print("\n⚠️  ALL citation tests failed. Likely causes:")
        print("   1. patent_client library not installed in container")
        print("   2. USPTO API endpoint changed or requires auth")
        print("   3. Network/SSL issue in container")

    if family_ok == 0:
        print("\n⚠️  ALL family tests failed. Likely causes:")
        print("   1. EPO OPS credentials not configured (EPO_OPS_CLIENT_ID)")
        print("   2. EPO OPS API endpoint changed")
        print("   3. XML response format changed (parser bug)")
