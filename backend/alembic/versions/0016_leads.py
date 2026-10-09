"""leads and discovery sources

Revision ID: 0016_leads
Revises: 0015_notifications
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_leads"
down_revision: str | None = "0015_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("target", sa.String(length=2048), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "kind", "target", name="uq_discovery_source_user_kind_target"
        ),
    )
    op.create_index("ix_discovery_sources_user_id", "discovery_sources", ["user_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("discovery_source_id", sa.Uuid(), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="New", nullable=False),
        sa.Column("rough_score", sa.Float(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["discovery_source_id"], ["discovery_sources.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_lead_user_dedupe"),
    )
    op.create_index("ix_leads_user_id", "leads", ["user_id"])
    op.create_index("ix_leads_discovery_source_id", "leads", ["discovery_source_id"])
    op.create_index("ix_leads_job_id", "leads", ["job_id"])
    op.create_index("ix_leads_status", "leads", ["status"])


def downgrade() -> None:
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_job_id", table_name="leads")
    op.drop_index("ix_leads_discovery_source_id", table_name="leads")
    op.drop_index("ix_leads_user_id", table_name="leads")
    op.drop_table("leads")
    op.drop_index("ix_discovery_sources_user_id", table_name="discovery_sources")
    op.drop_table("discovery_sources")
