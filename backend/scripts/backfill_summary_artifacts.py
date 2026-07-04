"""
Backfill existing ``PatentPublication.summary`` rows into ``AIArtifact``.

For every patent that already has a non-null summary but no
``latest_summary_artifact_id``, create an AIArtifact(summary, version=1)
record so the cache layer is consistent and the durable artifact log is
complete from day one of Phase 0.

Usage::

    python -m scripts.backfill_summary_artifacts
    python -m scripts.backfill_summary_artifacts --dry-run
    python -m scripts.backfill_summary_artifacts --batch-size 200
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select, update

from app.ai.llm_client import compute_input_hash
from app.ai.prompts import get_prompt
from app.ai.summarizer import (
    SUMMARY_PROMPT_NAME,
    SUMMARY_PROMPT_VERSION,
    build_summary_payload,
)
from app.core.ai_models import AIArtifact
from app.core.models import PatentPublication
from app.database import async_session_maker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")


async def _backfill(batch_size: int, dry_run: bool) -> dict[str, int]:
    stats = {"considered": 0, "skipped_existing": 0, "skipped_no_summary": 0, "created": 0}
    prompt = get_prompt(SUMMARY_PROMPT_NAME, SUMMARY_PROMPT_VERSION)

    async with async_session_maker() as session:
        offset = 0
        while True:
            stmt = (
                select(PatentPublication)
                .order_by(PatentPublication.id)
                .offset(offset)
                .limit(batch_size)
            )
            result = await session.execute(stmt)
            patents = list(result.scalars().all())
            if not patents:
                break

            for patent in patents:
                stats["considered"] += 1
                if patent.summary is None:
                    stats["skipped_no_summary"] += 1
                    continue
                if patent.latest_summary_artifact_id is not None:
                    stats["skipped_existing"] += 1
                    continue

                payload = build_summary_payload(patent)
                input_hash = compute_input_hash(
                    {
                        "payload": payload,
                        "subject_key": None,
                        "model": "claude-sonnet-4-20250514",
                    }
                )
                # Existing artifact for the same key? Skip create.
                exists_stmt = (
                    select(AIArtifact.id)
                    .where(AIArtifact.prompt_hash == prompt.prompt_hash)
                    .where(AIArtifact.input_hash == input_hash)
                    .where(AIArtifact.artifact_type == "summary")
                    .where(AIArtifact.status == "complete")
                    .limit(1)
                )
                existing = (await session.execute(exists_stmt)).scalar_one_or_none()
                if existing is not None:
                    if not dry_run:
                        await session.execute(
                            update(PatentPublication)
                            .where(PatentPublication.id == patent.id)
                            .values(latest_summary_artifact_id=existing)
                        )
                    stats["skipped_existing"] += 1
                    continue

                if dry_run:
                    stats["created"] += 1
                    continue

                artifact = AIArtifact(
                    patent_publication_id=patent.id,
                    artifact_type="summary",
                    artifact_version=1,
                    model="claude-sonnet-4-20250514",
                    prompt_name=prompt.name,
                    prompt_version=prompt.version,
                    prompt_hash=prompt.prompt_hash,
                    input_hash=input_hash,
                    content_json=patent.summary,
                    input_tokens=0,
                    output_tokens=0,
                    estimated_cost_usd=0.0,
                    actual_cost_usd=0.0,
                    status="complete",
                )
                session.add(artifact)
                await session.flush()
                await session.execute(
                    update(PatentPublication)
                    .where(PatentPublication.id == patent.id)
                    .values(latest_summary_artifact_id=artifact.id)
                )
                stats["created"] += 1

            await session.commit()
            offset += batch_size
            logger.info(
                "progress: considered=%d created=%d skipped_existing=%d skipped_no_summary=%d",
                stats["considered"],
                stats["created"],
                stats["skipped_existing"],
                stats["skipped_no_summary"],
            )

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count what would be created/linked without writing rows.",
    )
    args = parser.parse_args()

    stats = asyncio.run(_backfill(args.batch_size, args.dry_run))
    logger.info("done: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
