"""
Pre-flight cost estimator CLI.

Usage::

    python -m scripts.estimate_cost \\
        --task-type summary \\
        --run-mode cohort \\
        --has-abstract true \\
        --grant-year-from 2018 \\
        --limit 500

Prints the same numbers ``/admin/ai-runs`` shows in the UI: cohort size,
cached vs uncached, est input/output tokens, est cost USD.

Exits with status 0 on success and 2 on argument errors so it composes
with shell pipelines.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import httpx

from app.api.v1.ai_runs import CohortFilter, EstimateRequest


def _build_cohort(args: argparse.Namespace) -> CohortFilter:
    kwargs: dict[str, Any] = {}
    if args.cpc_prefix:
        kwargs["cpc_prefix"] = args.cpc_prefix
    if args.grant_year_from is not None:
        kwargs["grant_year_from"] = args.grant_year_from
    if args.grant_year_to is not None:
        kwargs["grant_year_to"] = args.grant_year_to
    if args.expiry_within_days is not None:
        kwargs["expiry_within_days"] = args.expiry_within_days
    if args.has_abstract is not None:
        kwargs["has_abstract"] = args.has_abstract
    if args.has_summary is not None:
        kwargs["has_summary"] = args.has_summary
    if args.min_score is not None:
        kwargs["min_interesting_score"] = args.min_score
    if args.limit is not None:
        kwargs["limit"] = args.limit
    return CohortFilter(**kwargs)


def _bool(value: str) -> bool | None:
    if value is None:
        return None
    v = value.lower()
    if v in ("1", "true", "yes", "y"):
        return True
    if v in ("0", "false", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(f"invalid bool: {value}")


async def _post_estimate(api: str, body: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(base_url=api, timeout=30) as c:
        r = await c.post("/api/v1/ai-runs/estimate", json=body)
        r.raise_for_status()
        return r.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-type", default="summary")
    parser.add_argument(
        "--run-mode",
        default="cohort",
        choices=["dev_fixture", "sample", "cohort", "full_batch"],
    )
    parser.add_argument("--cpc-prefix")
    parser.add_argument("--grant-year-from", type=int)
    parser.add_argument("--grant-year-to", type=int)
    parser.add_argument("--expiry-within-days", type=int)
    parser.add_argument("--has-abstract", type=_bool)
    parser.add_argument("--has-summary", type=_bool)
    parser.add_argument("--min-score", type=float)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--api",
        default="http://localhost:8000",
        help="Base URL of the backend API (default: http://localhost:8000)",
    )
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    args = parser.parse_args()

    cohort = _build_cohort(args)
    request = EstimateRequest(
        task_type=args.task_type,
        run_mode=args.run_mode,
        cohort=cohort,
    )
    payload = request.model_dump(mode="json")

    try:
        data = asyncio.run(_post_estimate(args.api, payload))
    except httpx.HTTPStatusError as e:
        print(f"error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        return 1
    except httpx.HTTPError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print(f"task_type        {data['task_type']}")
    print(f"run_mode         {data['run_mode']}")
    print(f"model            {data['model']}")
    print(f"prompt           {data['prompt_name']} v{data['prompt_version']}")
    print(f"prompt_hash      {data['prompt_hash'][:12]}...")
    print(f"cohort_size      {data['cohort_size']}")
    print(f"  cached         {data['cached_count']}")
    print(f"  uncached       {data['uncached_count']}")
    print(f"est_input_tok    {data['est_input_tokens']:,}")
    print(f"est_output_tok   {data['est_output_tokens']:,}")
    print(f"est_cost_usd     ${data['est_cost_usd']:.4f}")
    print(f"7d hit_rate      {data['expected_cache_hit_rate_7d']:.1%}")
    print(
        f"approval         "
        f"auto<=${data['auto_approve_threshold_usd']:.0f}, "
        f"full-batch>${data['full_batch_threshold_usd']:.0f}"
    )
    if data["requires_full_batch_phrase"]:
        print("WARNING: this run requires typing 'RUN FULL BATCH' to confirm")
    elif data["requires_confirmation"]:
        print("note: this run will require explicit confirmation in the UI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
