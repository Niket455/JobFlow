"""cover letters (grounded, versioned)

Revision ID: 0011_cover_letters
Revises: 0010_tailor_runs
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_cover_letters"
down_revision: str | None = "0010_tailor_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cover_letters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=True),
        sa.Column("parent_letter_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_enc", sa.Text(), nullable=False),
        sa.Column("grounding", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_letter_id"], ["cover_letters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cover_letters_user_id", "cover_letters", ["user_id"])
    op.create_index("ix_cover_letters_job_id", "cover_letters", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_cover_letters_job_id", table_name="cover_letters")
    op.drop_index("ix_cover_letters_user_id", table_name="cover_letters")
    op.drop_table("cover_letters")
