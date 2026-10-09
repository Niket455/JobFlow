"""follow-up snooze / done state

Revision ID: 0018_follow_up_states
Revises: 0017_ats_reports
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_follow_up_states"
down_revision: str | None = "0017_ats_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "follow_up_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("followed_up_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "application_id", name="uq_follow_up_state_user_application"
        ),
    )
    op.create_index("ix_follow_up_states_user_id", "follow_up_states", ["user_id"])
    op.create_index("ix_follow_up_states_application_id", "follow_up_states", ["application_id"])


def downgrade() -> None:
    op.drop_index("ix_follow_up_states_application_id", table_name="follow_up_states")
    op.drop_index("ix_follow_up_states_user_id", table_name="follow_up_states")
    op.drop_table("follow_up_states")
