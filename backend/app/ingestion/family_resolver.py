"""
INPADOC Family Resolver.

Resolves patent family relationships using EPO's INPADOC database.
Deduplicates patents by linking publications to their canonical family ID.

Key concepts:
- Simple family: Patents sharing the exact same priority
- Extended family: Patents sharing at least one priority (INPADOC)

We use INPADOC extended families for broader coverage.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication
from app.ingestion.epo_client import EPOClient

logger = logging.getLogger(__name__)


class FamilyResolver:
    """
    Resolves patent family relationships using INPADOC data.

    Links patent publications to their extended family ID for deduplication
    and cross-jurisdiction analysis.
    """

    def __init__(self, epo_client: EPOClient | None = None):
        self._epo_client = epo_client

    @property
    def epo_client(self) -> EPOClient:
        """Lazy initialization of EPO client."""
        if self._epo_client is None:
            self._epo_client = EPOClient()
        return self._epo_client

    def resolve_family(self, publication_number: str) -> dict:
        """
        Resolve family information for a publication.

        Args:
            publication_number: The publication number to look up

        Returns:
            Family data including family_id and member list
        """
        try:
            family_data = self.epo_client.fetch_family(publication_number)
            return self._parse_family_response(family_data)
        except Exception as e:
            logger.warning(f"Failed to resolve family for {publication_number}: {e}")
            return {
                "family_id": None,
                "members": [],
                "error": str(e),
            }

    def _parse_family_response(self, response: dict) -> dict:
        """Parse EPO family API response."""
        try:
            patent_family = response.get("ops:world-patent-data", {}).get("ops:patent-family", {})

            family_id = patent_family.get("@family-id")

            members = []
            family_members = patent_family.get("ops:family-member", [])
            if isinstance(family_members, dict):
                family_members = [family_members]

            for member in family_members:
                pub_ref = member.get("publication-reference", {})
                doc_id = pub_ref.get("document-id", {})

                if isinstance(doc_id, list):
                    doc_id = doc_id[0] if doc_id else {}

                country = doc_id.get("country", {}).get("$", "")
                doc_number = doc_id.get("doc-number", {}).get("$", "")
                kind = doc_id.get("kind", {}).get("$", "")

                if doc_number:
                    members.append(
                        {
                            "publication_number": f"{country}{doc_number}{kind}",
                            "country": country,
                            "kind_code": kind,
                        }
                    )

            return {
                "family_id": family_id,
                "members": members,
                "member_count": len(members),
            }

        except Exception as e:
            logger.warning(f"Failed to parse family response: {e}")
            return {
                "family_id": None,
                "members": [],
                "error": str(e),
            }

    async def update_patent_family(
        self,
        session: AsyncSession,
        patent_id: str,
    ) -> dict:
        """
        Update family information for a patent in the database.

        Args:
            session: Database session
            patent_id: UUID of the patent to update

        Returns:
            Updated family information
        """
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == patent_id)
        )
        patent = result.scalar_one_or_none()

        if not patent:
            return {"error": "Patent not found"}

        family_data = self.resolve_family(patent.publication_number)

        if family_data.get("family_id"):
            patent.family_id = family_data["family_id"]
            patent.family_members = [
                m["publication_number"] for m in family_data.get("members", [])
            ]
            await session.commit()

        return family_data

    async def batch_resolve_families(
        self,
        session: AsyncSession,
        limit: int = 100,
    ) -> dict:
        """
        Resolve families for patents missing family_id.

        Args:
            session: Database session
            limit: Maximum patents to process

        Returns:
            Processing statistics
        """
        result = await session.execute(
            select(PatentPublication)
            .where(PatentPublication.family_id.is_(None))
            .where(PatentPublication.office.in_(["EPO", "USPTO"]))
            .limit(limit)
        )
        patents = result.scalars().all()

        stats = {"processed": 0, "resolved": 0, "failed": 0}

        for patent in patents:
            try:
                family_data = self.resolve_family(patent.publication_number)

                if family_data.get("family_id"):
                    patent.family_id = family_data["family_id"]
                    patent.family_members = [
                        m["publication_number"] for m in family_data.get("members", [])
                    ]
                    stats["resolved"] += 1
                else:
                    stats["failed"] += 1

            except Exception as e:
                logger.warning(f"Failed to resolve family for {patent.publication_number}: {e}")
                stats["failed"] += 1

            stats["processed"] += 1

        await session.commit()
        logger.info(f"Family resolution complete: {stats}")
        return stats


async def deduplicate_by_family(
    session: AsyncSession,
    family_id: str,
) -> dict:
    """
    Get all patents in a family and identify the primary publication.

    The primary publication is typically:
    1. The granted patent (if any)
    2. The earliest publication
    3. The US or EP publication (for business relevance)

    Args:
        session: Database session
        family_id: INPADOC family ID

    Returns:
        Family analysis with primary and secondary publications
    """
    result = await session.execute(
        select(PatentPublication).where(PatentPublication.family_id == family_id)
    )
    members = result.scalars().all()

    if not members:
        return {"family_id": family_id, "members": [], "primary": None}

    grants = [m for m in members if m.legal_status == "GRANTED"]
    priority_offices = ["USPTO", "EPO"]

    primary = None
    if grants:
        priority_grants = [g for g in grants if g.office in priority_offices]
        primary = priority_grants[0] if priority_grants else grants[0]
    else:
        priority_pubs = [m for m in members if m.office in priority_offices]
        if priority_pubs:
            primary = min(priority_pubs, key=lambda x: x.publication_date or datetime.max.date())
        else:
            primary = min(members, key=lambda x: x.publication_date or datetime.max.date())

    return {
        "family_id": family_id,
        "member_count": len(members),
        "primary": {
            "id": str(primary.id),
            "doc_id": primary.doc_id,
            "office": primary.office,
            "legal_status": primary.legal_status,
        },
        "members": [
            {
                "id": str(m.id),
                "doc_id": m.doc_id,
                "office": m.office,
                "legal_status": m.legal_status,
                "is_primary": m.id == primary.id,
            }
            for m in members
        ],
    }
