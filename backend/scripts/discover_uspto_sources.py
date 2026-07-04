#!/usr/bin/env python3
"""
V3.8C ODP Endpoint Enumerator — exhaustive patent-related endpoint discovery.
Tests all plausible endpoint patterns since Swagger is not accessible.
"""

import json
import os
from datetime import datetime, timezone

import httpx

API_KEY = os.environ.get("USPTO_ODP_API_KEY", "")
BASE = "https://api.uspto.gov"
HEADERS = {"X-API-Key": API_KEY, "User-Agent": "InventionIndex8/1.0 (V3.8C)"}

# Exhaustive endpoint patterns to test
ENDPOINTS = [
    # File Wrapper
    "/api/v1/patent/applications/search",
    "/api/v1/patent/applications/{id}",
    "/api/v1/patent/applications/{id}/documents",
    "/api/v1/patent/applications/{id}/application-data",
    "/api/v1/patent/applications/{id}/bibliographic-data",
    "/api/v1/patent/applications/{id}/biblio",
    "/api/v1/patent/applications/{id}/metadata",
    "/api/v1/patent/applications/{id}/assignments",
    "/api/v1/patent/applications/{id}/events",
    "/api/v1/patent/applications/{id}/continuity",
    "/api/v1/patent/applications/{id}/foreign-priority",
    "/api/v1/patent/applications/{id}/attorney",
    "/api/v1/patent/applications/{id}/pta",
    "/api/v1/patent/applications/{id}/patent-term",
    "/api/v1/patent/applications/{id}/status",
    # Grants
    "/api/v1/patent/grants",
    "/api/v1/patent/grants/search",
    "/api/v1/patent/grants/{id}",
    "/api/v1/patent/grants/{id}/documents",
    "/api/v1/patent/grants/{id}/metadata",
    "/api/v1/patent/grants/{id}/bibliographic-data",
    # Published Applications
    "/api/v1/patent/published-applications",
    "/api/v1/patent/published-applications/search",
    "/api/v1/patent/publications",
    "/api/v1/patent/publications/search",
    "/api/v1/patent/publications/{id}",
    # Assignments
    "/api/v1/patent/assignments",
    "/api/v1/patent/assignments/search",
    "/api/v1/patent/assignments/{id}",
    # Bulk Datasets
    "/api/v1/datasets",
    "/api/v1/datasets/search",
    "/api/v1/datasets/{id}",
    "/api/v1/datasets/products",
    "/api/v1/datasets/products/search",
    "/api/v1/datasets/products/{id}",
    "/api/v1/datasets/products/{id}/files",
    "/api/v1/datasets/products/{id}/download",
    "/api/v1/datasets/products/files/{productId}/{year}/{zipName}",
    "/api/v1/datasets/products/files/{productId}/{year}/{zipName}/{fileName}",
    # Products
    "/api/v1/products",
    "/api/v1/products/search",
    "/api/v1/products/{id}",
    "/api/v1/products/files/{productId}/{year}/{zipName}",
    # Download
    "/api/v1/download/applications/{id}",
    "/api/v1/download/datasets/{productId}",
    "/api/v1/download/products/{productId}",
    # Search (alternative paths)
    "/api/v1/search/patents",
    "/api/v1/search/applications",
    "/api/v1/search/grants",
    # Maintenance / Fees
    "/api/v1/patent/maintenance-fees",
    "/api/v1/patent/maintenance-fees/{id}",
    # Bulk
    "/api/v1/bulk/patents",
    "/api/v1/bulk/grants",
    "/api/v1/bulk/applications",
    # PatentsView (ODP-hosted)
    "/api/v1/patentsview",
    "/api/v1/patentsview/patents",
    "/api/v1/patentsview/patents/query",
    "/api/v1/patentsview/applications",
    "/api/v1/patents-view/patents/query",
    # Weekly
    "/api/v1/weekly/grants",
    "/api/v1/weekly/applications",
    "/api/v1/weekly/publications",
    # Bibliographic
    "/api/v1/bibliographic/patents",
    "/api/v1/bibliographic/grants",
    "/api/v1/bibliographic/applications",
]


def test_all():
    results = []
    working = []
    auth_blocked = []
    unavailable = []

    test_params = {
        "search": {"searchText": "patent", "page": 1, "size": 2},
        "date": {"dateFrom": "2026-06-01", "dateTo": "2026-06-21"},
        "bare": {},
    }

    for i, path in enumerate(ENDPOINTS):
        # Replace {id} with a known working application number
        test_path = path.replace("{id}", "18045436")
        test_path = test_path.replace("{productId}", "PTGRXML-SPLT")
        test_path = test_path.replace("{year}", "2026")
        test_path = test_path.replace("{zipName}", "ipg06182026")
        test_path = test_path.replace("{fileName}", "test.xml")
        url = f"{BASE}{test_path}"

        # Determine which params to use
        if "search" in path.lower():
            params = test_params["search"]
        elif "dateFrom" in path.lower() or "grant" in path.lower() and "search" not in path.lower():
            params = test_params["date"]
        else:
            params = None

        result = {
            "path": path,
            "tested_url": url,
            "status": None,
            "content_type": None,
            "response_keys": None,
            "response_sample": None,
            "has_date_params": "date" in path.lower(),
        }

        try:
            r = httpx.get(url, params=params, headers=HEADERS, timeout=15, follow_redirects=True)
            result["status"] = r.status_code
            ct = r.headers.get("content-type", "")
            result["content_type"] = ct[:100]

            if r.status_code == 200:
                if "json" in ct:
                    try:
                        data = r.json()
                        result["response_keys"] = list(data.keys())[:20]
                        result["response_sample"] = json.dumps(data, default=str)[:500]
                    except:
                        result["response_sample"] = r.text[:500]
                else:
                    result["response_sample"] = r.text[:300]
                working.append(result)
            elif r.status_code in (403, 401):
                result["error"] = r.text[:150]
                auth_blocked.append(result)
            elif r.status_code in (503, 502):
                result["error"] = r.text[:150]
                unavailable.append(result)
            else:
                result["error"] = r.text[:150]

        except Exception as e:
            result["status"] = -1
            result["error"] = str(e)[:200]

        status_icon = (
            "✅" if result["status"] == 200 else "❌" if result["status"] in (403, 401) else "⚠️"
        )
        print(
            f"[{i + 1:02d}/{len(ENDPOINTS)}] {status_icon} {result['status']} {result['path'][:70]}"
        )

    return {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "total_tested": len(results),
        "working_200": len(working),
        "auth_blocked": len(auth_blocked),
        "unavailable": len(unavailable),
        "working_endpoints": [w["path"] for w in working],
        "auth_blocked_endpoints": [a["path"] for a in auth_blocked],
        "endpoints": results,
    }


if __name__ == "__main__":
    summary = test_all()
    os.makedirs("docs/artifacts", exist_ok=True)
    with open("docs/artifacts/uspto_source_discovery.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n=== Summary ===")
    print(f"Total: {summary['total_tested']}")
    print(f"Working: {summary['working_200']}")
    print(f"Auth blocked: {summary['auth_blocked']}")
    print(f"Unavailable: {summary['unavailable']}")
    print(f"\nWorking: {json.dumps(summary['working_endpoints'], indent=2)}")
