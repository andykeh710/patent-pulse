"""
Backfill forward citations (Sprint 5 prerequisite).

Derives citations_forward from citations_backward. For each patent A
that lists B in its backward citations, append A.doc_id to
B.citations_forward (dedup by doc_id). Pure SQL — no API calls.

Run once; idempotent.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.database import async_session_maker

logger = logging.getLogger(__name__)


async def backfill_forward_citations(
    *,
    batch_size: int = 5000,
) -> dict[str, Any]:
    """Derive citations_forward from citations_backward across the corpus.

    For each patent A that has B in its citations_backward:
        Append A.doc_id to B.citations_forward (dedup).

    Returns dict with keys: processed, updated, skipped.
    """
    stats: dict[str, int] = {"processed": 0, "updated": 0, "skipped": 0}

    async with async_session_maker() as session:
        # Fetch all patents that have backward citations.
        result = await session.execute(
            text(
                """
                SELECT id, doc_id, citations_backward
                FROM patent_publications
                WHERE citations_backward IS NOT NULL
                  AND jsonb_array_length(citations_backward) > 0
                ORDER BY id
                LIMIT :limit OFFSET :offset
                """
            ),
            {"limit": batch_size, "offset": 0},
        )
        rows = result.fetchall()
        stats["processed"] = len(rows)

        for row in rows:
            citing_id, citing_doc_id, backward = row
            if not backward:
                stats["skipped"] += 1
                continue

            # For each cited patent, append the citing patent's doc_id
            # to its citations_forward.
            for cited_doc_id in backward:
                await session.execute(
                    text(
                        """
                        UPDATE patent_publications
                        SET citations_forward = (
                            SELECT jsonb_agg(DISTINCT elem ORDER BY elem)
                            FROM jsonb_array_elements_text(
                                COALESCE(citations_forward, '[]'::jsonb)
                            ) AS elem
                            UNION ALL
                            SELECT :citing_doc_id
                        )
                        WHERE doc_id = :cited_doc_id
                        """
                    ),
                    {
                        "citing_doc_id": citing_doc_id,
                        "cited_doc_id": cited_doc_id,
                    },
                )
                stats["updated"] += 1

        await session.commit()
        logger.info(
            "Forward citation backfill: processed=%d updated=%d skipped=%d",
            stats["processed"],
            stats["updated"],
            stats["skipped"],
        )

    return stats


async def backfill_forward_citations_for_session(
    session,
    *,
    batch_size: int = 5000,
) -> dict[str, Any]:
    """Session-aware variant (testable)."""
    stats: dict[str, int] = {"processed": 0, "updated": 0, "skipped": 0}

    result = await session.execute(
        text(
            """
            SELECT id, doc_id, citations_backward
            FROM patent_publications
            WHERE citations_backward IS NOT NULL
              AND jsonb_array_length(citations_backward) > 0
            ORDER BY id
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": batch_size, "offset": 0},
    )
    rows = result.fetchall()
    stats["processed"] = len(rows)

    for row in rows:
        citing_id, citing_doc_id, backward = row
        if not backward:
            stats["skipped"] += 1
            continue

        for cited_doc_id in backward:
            await session.execute(
                text(
                    """
                    UPDATE patent_publications
                    SET citations_forward = (
                        SELECT jsonb_agg(DISTINCT elem ORDER BY elem)
                        FROM jsonb_array_elements_text(
                            COALESCE(citations_forward, '[]'::jsonb)
                        ) AS elem
                        UNION ALL
                        SELECT :citing_doc_id
                    )
                    WHERE doc_id = :cited_doc_id
                    """
                ),
                {
                    "citing_doc_id": citing_doc_id,
                    "cited_doc_id": cited_doc_id,
                },
            )
            stats["updated"] += 1

    await session.commit()
    return stats
