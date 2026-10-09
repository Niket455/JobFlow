"""ats report snapshots

Revision ID: 0017_ats_reports
Revises: 0016_leads
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_ats_reports"
down_revision: str | None = "0016_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ats_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(length=2), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ats_reports_user_id", "ats_reports", ["user_id"])
    op.create_index("ix_ats_reports_resume_version_id", "ats_reports", ["resume_version_id"])
    op.create_index("ix_ats_reports_job_id", "ats_reports", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_ats_reports_job_id", table_name="ats_reports")
    op.drop_index("ix_ats_reports_resume_version_id", table_name="ats_reports")
    op.drop_index("ix_ats_reports_user_id", table_name="ats_reports")
    op.drop_table("ats_reports")
