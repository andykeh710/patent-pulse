"""V4.0 Community Foundation — intelligence_items, evidence_items, moderation_events

Adds the shared publishable object model, evidence tracking, and moderation
infrastructure. All objects default to private visibility. No public features
are exposed until COMMUNITY_PUBLIC_ENABLED is set to true.

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0038"
down_revision: Union[str, None] = "0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── intelligence_items ─────────────────────────────────────────
    op.create_table(
        "intelligence_items",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("slug", sa.String(256), unique=True),
        sa.Column("summary", sa.Text()),
        sa.Column("body", sa.Text()),
        sa.Column("owner_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "visibility",
            sa.String(16),
            nullable=False,
            server_default="private",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("canonical_url", sa.String(1024)),
        sa.Column("seo_title", sa.String(256)),
        sa.Column("seo_description", sa.String(512)),
        sa.Column("og_image_url", sa.String(1024)),
        sa.Column("metadata", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_intelligence_items_slug", "intelligence_items", ["slug"], unique=True, postgresql_where=sa.text("slug IS NOT NULL"))
    op.create_index("ix_intelligence_items_visibility", "intelligence_items", ["visibility", "published_at"], postgresql_where=sa.text("visibility = 'public'"))
    op.create_index("ix_intelligence_items_owner", "intelligence_items", ["owner_user_id", "created_at"])

    # ── evidence_items ─────────────────────────────────────────────
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_type", sa.String(32), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_url", sa.String(1024)),
        sa.Column("patent_id", sa.UUID(), sa.ForeignKey("patent_publications.id")),
        sa.Column("field_used", sa.String(64)),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(16), server_default="medium"),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_items_parent", "evidence_items", ["parent_type", "parent_id"])

    # ── moderation_events ──────────────────────────────────────────
    op.create_table(
        "moderation_events",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", sa.UUID(), nullable=False),
        sa.Column("reporter_user_id", sa.String(64), sa.ForeignKey("users.id")),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("resolved_by_user_id", sa.String(64), sa.ForeignKey("users.id")),
        sa.Column("resolution", sa.String(32)),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_moderation_events_status", "moderation_events", ["status", "created_at"])
    op.create_index("ix_moderation_events_object", "moderation_events", ["object_type", "object_id"])

    # ── feature flag (env-var based, see app.config) ────────────────
    # COMMUNITY_PUBLIC_ENABLED controls public community feature exposure.
    # Default: false. Set to 'true' only after moderation infra and
    # production email are confirmed live.


def downgrade() -> None:
    op.drop_table("moderation_events")
    op.drop_table("evidence_items")
    op.drop_table("intelligence_items")
