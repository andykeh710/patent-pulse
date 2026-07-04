"""
Safely re-run system-theme matching.

Why: the original "AI" assignee keyword substring-matched company names
(e.g. "HyundAI"), and the matcher previously used substring (`in`) matching.
This script:
  1. Syncs the 3 system themes' keyword config to the corrected seed.
  2. Clears their existing (possibly false-positive) theme_matches.
  3. Re-runs matching with the whole-word matcher.
  4. Prints before/after counts and sample matches per theme.

Safe: only touches theme config + derived theme_matches rows (which are
regenerable). It never deletes patent data. Idempotent — safe to re-run.

Usage:
  docker compose exec backend python scripts/rematch_themes.py
  # optionally target only specific themes by name:
  docker compose exec backend python scripts/rematch_themes.py "AI / Machine Learning"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select  # noqa: E402

from app.core.models import PatentPublication  # noqa: E402
from app.core.theme_models import Theme, ThemeMatch  # noqa: E402
from app.database import async_session_maker  # noqa: E402
from app.tasks.theme_matcher import _match_single_theme  # noqa: E402
from scripts.seed_default_themes import DEFAULT_THEMES  # noqa: E402


async def _count(session, theme_id) -> int:
    return (
        await session.execute(
            select(func.count(ThemeMatch.id)).where(ThemeMatch.theme_id == theme_id)
        )
    ).scalar() or 0


async def rematch_system_themes(only: list[str] | None = None) -> None:
    async with async_session_maker() as session:
        for spec in DEFAULT_THEMES:
            if only and spec["name"] not in only:
                continue

            theme = (
                await session.execute(
                    select(Theme).where(Theme.name == spec["name"], Theme.user_id.is_(None))
                )
            ).scalar_one_or_none()
            if theme is None:
                print(f"[skip] system theme not found: {spec['name']!r}")
                continue

            before = await _count(session, theme.id)

            # 1. Sync config to the corrected seed definition.
            theme.cpc_prefixes = spec.get("cpc_prefixes", [])
            theme.assignee_keywords = spec.get("assignee_keywords", [])
            theme.title_keywords = spec.get("title_keywords", [])
            theme.keywords = spec.get("keywords")

            # 2. Clear stale matches for this theme.
            await session.execute(delete(ThemeMatch).where(ThemeMatch.theme_id == theme.id))
            await session.flush()

            # 3. Re-match with the whole-word matcher.
            stats = await _match_single_theme(session, theme, limit=500)
            await session.commit()

            after = await _count(session, theme.id)
            print(f"\n=== {theme.name} ===")
            print(
                f"  matches before: {before}  after: {after}  "
                f"(matched={stats['matched']}, skipped={stats['skipped']})"
            )

            # 4. Sample matches for eyeballing relevance.
            rows = (
                await session.execute(
                    select(
                        PatentPublication.publication_number,
                        PatentPublication.title,
                        PatentPublication.cpc,
                        ThemeMatch.match_score,
                        ThemeMatch.match_reasons,
                    )
                    .join(ThemeMatch, ThemeMatch.patent_id == PatentPublication.id)
                    .where(ThemeMatch.theme_id == theme.id)
                    .order_by(ThemeMatch.match_score.desc())
                    .limit(5)
                )
            ).all()
            for r in rows:
                title = (r[1] or "")[:48]
                print(f"   - {r[0]} | {title} | score={r[3]:.2f} | {r[4]}")


if __name__ == "__main__":
    targets = sys.argv[1:] or None
    asyncio.run(rematch_system_themes(targets))
