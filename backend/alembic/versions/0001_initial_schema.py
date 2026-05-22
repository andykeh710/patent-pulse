"""Initial schema with PatentPublication table

Revision ID: 0001
Revises:
Create Date: 2026-03-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "patent_publications",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("doc_id", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(64), nullable=True),
        sa.Column("office", sa.String(8), nullable=False),
        sa.Column("publication_number", sa.String(32), nullable=False),
        sa.Column("application_number", sa.String(32), nullable=True),
        sa.Column("kind_code", sa.String(4), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("priority_date", sa.Date(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("grant_date", sa.Date(), nullable=True),
        sa.Column("assignees", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("inventors", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("cpc", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("ipc", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("claims_text", sa.Text(), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("citations_backward", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("family_members", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("legal_status", sa.String(32), nullable=True),
        sa.Column("maintenance_status", sa.String(32), nullable=True),
        sa.Column("estimated_expiry_date", sa.Date(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("novel_applications", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("interesting_score", sa.Float(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "search_vector",
            sa.dialects.postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("summarized_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_patent_publications_doc_id", "patent_publications", ["doc_id"], unique=True)
    op.create_index("ix_patent_publications_family_id", "patent_publications", ["family_id"])
    op.create_index(
        "ix_patent_publications_publication_number", "patent_publications", ["publication_number"]
    )
    op.create_index(
        "ix_patent_publications_publication_date", "patent_publications", ["publication_date"]
    )
    op.create_index(
        "ix_patent_publications_estimated_expiry_date",
        "patent_publications",
        ["estimated_expiry_date"],
    )
    op.create_index(
        "ix_patent_publications_search_vector",
        "patent_publications",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_patent_publications_cpc",
        "patent_publications",
        ["cpc"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_patent_publications_assignees",
        "patent_publications",
        ["assignees"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("patent_publications")
    op.execute("DROP EXTENSION IF EXISTS vector")
