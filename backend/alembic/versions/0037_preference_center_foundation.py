"""V3.1 — Preference center foundation: feed interactions, hidden items, user fields.

Adds:
- users.use_case, digest_frequency, digest_topics_only, digest_min_opp_score
- feed_interactions (tracks user actions on feed items)
- hidden_feed_items (persists user-hid items)

Uses object_type + object_id instead of feed_item_id so interactions
reference underlying objects (patents, trends, companies) directly.
"""

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ── User preference columns ──────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "use_case",
            sa.String(64),
            nullable=True,
            comment="startup_ideas, rd_monitoring, competitive_intel, "
            "investment_research, expiry_freedom, licensing, academic, general",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "digest_frequency",
            sa.String(16),
            server_default="weekly",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "digest_topics_only",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "digest_min_opp_score",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )

    # ── Feed interactions ─────────────────────────────────────────────
    op.create_table(
        "feed_interactions",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", sa.String(256), nullable=False),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_feed_interactions_user_time",
        "feed_interactions",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_feed_interactions_object",
        "feed_interactions",
        ["user_id", "object_type", "object_id"],
    )

    # ── Hidden feed items ─────────────────────────────────────────────
    op.create_table(
        "hidden_feed_items",
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", sa.String(256), nullable=False),
        sa.Column(
            "hidden_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "object_type", "object_id"),
    )


def downgrade():
    op.drop_table("hidden_feed_items")
    op.drop_table("feed_interactions")
    op.drop_column("users", "digest_min_opp_score")
    op.drop_column("users", "digest_topics_only")
    op.drop_column("users", "digest_frequency")
    op.drop_column("users", "use_case")
