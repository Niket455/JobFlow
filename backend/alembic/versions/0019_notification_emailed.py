"""notification email delivery

Revision ID: 0019_notification_emailed
Revises: 0018_follow_up_states
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_notification_emailed"
down_revision: str | None = "0018_follow_up_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications", sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("notifications", "emailed_at")
