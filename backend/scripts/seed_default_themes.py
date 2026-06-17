"""
Seed 3 default themes into the database so the subscribe flow can be
exercised in dev / test environments. Idempotent: skips if themes exist.
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text

from app.core.theme_models import Theme
from app.database import async_session_maker

logger = logging.getLogger(__name__)

DEFAULT_THEMES = [
    {
        "name": "AI / Machine Learning",
        "description": "Patents related to artificial intelligence, neural networks, and ML systems",
        "cpc_prefixes": ["G06N"],
        # No assignee keywords: "AI" is a 2-letter substring that matched
        # company names like "HyundAI" via ILIKE/`in`, producing false-positive
        # theme matches. The honest signal for this theme is CPC G06N plus the
        # title/abstract keywords below.
        "assignee_keywords": [],
        "title_keywords": ["neural network", "transformer", "LLM", "deep learning"],
        "keywords": ["artificial intelligence", "deep learning", "model training"],
        "is_active": True,
    },
    {
        "name": "Semiconductor / Chip Design",
        "description": "Patents related to semiconductor manufacturing, chip architecture, and fabrication",
        "cpc_prefixes": ["H01L"],
        "assignee_keywords": ["Intel", "AMD", "TSMC", "NVIDIA"],
        "title_keywords": ["semiconductor", "transistor", "gate", "finfet"],
        "keywords": ["chip", "wafer", "lithography", "die"],
        "is_active": True,
    },
    {
        "name": "Medical Devices",
        "description": "Patents related to medical devices, surgical instruments, and diagnostic equipment",
        "cpc_prefixes": ["A61B", "A61M"],
        "assignee_keywords": ["Medtronic", "Stryker"],
        "title_keywords": ["implant", "surgical", "catheter", "stent"],
        "keywords": ["biopsy", "imaging", "prosthetic"],
        "is_active": True,
    },
]


async def seed_default_themes() -> int:
    """Insert default themes. Returns number created. Skips if themes exist."""
    async with async_session_maker() as session:
        existing = await session.execute(select(text("1")).where(
            select(Theme.id).exists()
        ))
        if existing.scalar():
            logger.info("Themes already exist — skipping seed.")
            return 0

        created = 0
        for data in DEFAULT_THEMES:
            theme = Theme(**data)
            session.add(theme)
            created += 1

        await session.commit()
        logger.info("Seeded %d default themes.", created)
        return created


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = asyncio.run(seed_default_themes())
    print(f"Seeded {count} themes")
