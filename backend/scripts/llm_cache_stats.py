"""
AIArtifact / AIRun cache statistics CLI.

Reports cache hit-rate, USD spent, and per-task counts over a window.

Usage::

    python -m scripts.llm_cache_stats          # last 7 days
    python -m scripts.llm_cache_stats --days 30
    python -m scripts.llm_cache_stats --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.ai_models import AIArtifact, AIRun
from app.database import async_session_maker


async def _gather(days: int) -> dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with async_session_maker() as session:
        # Per-type artifact counts.
        artifact_stmt = (
            select(
                AIArtifact.artifact_type,
                AIArtifact.status,
                func.count().label("count"),
                func.coalesce(func.sum(AIArtifact.actual_cost_usd), 0).label("usd"),
                func.coalesce(func.sum(AIArtifact.input_tokens), 0).label("in_tok"),
                func.coalesce(func.sum(AIArtifact.output_tokens), 0).label("out_tok"),
            )
            .where(AIArtifact.created_at >= cutoff)
            .group_by(AIArtifact.artifact_type, AIArtifact.status)
        )
        rows = (await session.execute(artifact_stmt)).all()
        artifact_breakdown: dict[str, dict[str, Any]] = {}
        for r in rows:
            entry = artifact_breakdown.setdefault(
                r.artifact_type,
                {
                    "complete": 0,
                    "failed": 0,
                    "pending": 0,
                    "usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            )
            entry[r.status] = entry.get(r.status, 0) + r.count
            if r.status == "complete":
                entry["usd"] += float(r.usd or 0)
                entry["input_tokens"] += int(r.in_tok or 0)
                entry["output_tokens"] += int(r.out_tok or 0)

        # Run-level cache hit rate.
        run_stmt = (
            select(
                AIRun.task_type,
                func.coalesce(func.sum(AIRun.cached_count), 0).label("cached"),
                func.coalesce(func.sum(AIRun.uncached_count), 0).label("uncached"),
                func.count().label("runs"),
            )
            .where(AIRun.created_at >= cutoff)
            .group_by(AIRun.task_type)
        )
        run_rows = (await session.execute(run_stmt)).all()
        run_breakdown: dict[str, dict[str, Any]] = {}
        for r in run_rows:
            total = int(r.cached or 0) + int(r.uncached or 0)
            hit_rate = (int(r.cached or 0) / total) if total else 0.0
            run_breakdown[r.task_type] = {
                "runs": int(r.runs),
                "cached": int(r.cached or 0),
                "uncached": int(r.uncached or 0),
                "cache_hit_rate": round(hit_rate, 4),
            }

        total_usd = sum(v["usd"] for v in artifact_breakdown.values())
        total_complete = sum(v["complete"] for v in artifact_breakdown.values())
        total_failed = sum(v["failed"] for v in artifact_breakdown.values())

        return {
            "window_days": days,
            "since": cutoff.isoformat(),
            "total_completed_artifacts": total_complete,
            "total_failed_artifacts": total_failed,
            "total_actual_cost_usd": round(total_usd, 4),
            "by_artifact_type": artifact_breakdown,
            "by_run_task_type": run_breakdown,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = asyncio.run(_gather(args.days))

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print(f"Window:     last {data['window_days']} days (since {data['since'][:10]})")
    print(
        f"Artifacts:  {data['total_completed_artifacts']:,} complete, "
        f"{data['total_failed_artifacts']:,} failed"
    )
    print(f"Total spend: ${data['total_actual_cost_usd']:.4f}")
    print()
    print("Per artifact type:")
    print(
        f"  {'type':28s} {'complete':>8s} {'failed':>7s} "
        f"{'in_tok':>10s} {'out_tok':>10s} {'usd':>10s}"
    )
    for atype, v in sorted(data["by_artifact_type"].items()):
        print(
            f"  {atype:28s} {v['complete']:>8d} {v['failed']:>7d} "
            f"{v['input_tokens']:>10,d} {v['output_tokens']:>10,d} "
            f"${v['usd']:>8.4f}"
        )
    print()
    print("Per run task type (cache hit rate):")
    print(f"  {'type':28s} {'runs':>5s} {'cached':>8s} {'uncached':>8s} {'hit_rate':>9s}")
    for atype, v in sorted(data["by_run_task_type"].items()):
        print(
            f"  {atype:28s} {v['runs']:>5d} {v['cached']:>8d} "
            f"{v['uncached']:>8d} {v['cache_hit_rate']:>8.1%}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
