"""job lifecycle re-check columns

Revision ID: 0005_job_lifecycle
Revises: 0004_jobs
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_job_lifecycle"
down_revision: str | None = "0004_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_jobs_next_check_at", "jobs", ["next_check_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_next_check_at", table_name="jobs")
    op.drop_column("jobs", "next_check_at")
    op.drop_column("jobs", "last_checked_at")
