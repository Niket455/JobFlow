"""interview prep: kits, practice sessions, star stories

Revision ID: 0012_interview_prep
Revises: 0011_cover_letters
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_interview_prep"
down_revision: str | None = "0011_cover_letters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interview_kits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_kits_user_id", "interview_kits", ["user_id"])
    op.create_index("ix_interview_kits_job_id", "interview_kits", ["job_id"])

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("question", sa.String(length=1000), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("answer_enc", sa.Text(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_practice_sessions_user_id", "practice_sessions", ["user_id"])
    op.create_index("ix_practice_sessions_job_id", "practice_sessions", ["job_id"])

    op.create_table(
        "star_stories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=True),
        sa.Column("resume_item_path", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("content_enc", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_star_stories_user_id", "star_stories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_star_stories_user_id", table_name="star_stories")
    op.drop_table("star_stories")
    op.drop_index("ix_practice_sessions_job_id", table_name="practice_sessions")
    op.drop_index("ix_practice_sessions_user_id", table_name="practice_sessions")
    op.drop_table("practice_sessions")
    op.drop_index("ix_interview_kits_job_id", table_name="interview_kits")
    op.drop_index("ix_interview_kits_user_id", table_name="interview_kits")
    op.drop_table("interview_kits")
