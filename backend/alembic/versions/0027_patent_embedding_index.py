"""HNSW pgvector index on patent_publications.embedding

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-08

Adds an HNSW index on patent_publications.embedding for sub-millisecond
approximate nearest-neighbour lookups via cosine similarity (<=> operator).
Without this index, every semantic search query runs a full sequential scan
of the table (~64K rows).

Parameters (per Phase 1 audit):
  - m = 16               (default, good for 1536-dim vectors)
  - ef_construction = 64  (higher build-time recall at modest cost)

The index is created CONCURRENTLY so it does not lock the table and is
safe to ship while the embedding backfill is running.
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
              idx_patents_embedding_hnsw
            ON patent_publications
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_patents_embedding_hnsw")
