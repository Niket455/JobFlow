"""tailor runs (resume tailoring with fact-grounding)

Revision ID: 0010_tailor_runs
Revises: 0009_alerts
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_tailor_runs"
down_revision: str | None = "0009_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tailor_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("base_resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="proposed", nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("applied_resume_version_id", sa.Uuid(), nullable=True),
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
            ["base_resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["applied_resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tailor_runs_user_id", "tailor_runs", ["user_id"])
    op.create_index(
        "ix_tailor_runs_base_resume_version_id", "tailor_runs", ["base_resume_version_id"]
    )
    op.create_index("ix_tailor_runs_job_id", "tailor_runs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_tailor_runs_job_id", table_name="tailor_runs")
    op.drop_index("ix_tailor_runs_base_resume_version_id", table_name="tailor_runs")
    op.drop_index("ix_tailor_runs_user_id", table_name="tailor_runs")
    op.drop_table("tailor_runs")
