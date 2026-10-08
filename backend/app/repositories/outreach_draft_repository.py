import uuid
from typing import Any

from sqlalchemy import select

from app.models.outreach_draft import OutreachDraft
from app.repositories.base import BaseRepository


class OutreachDraftRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, draft_id: uuid.UUID) -> OutreachDraft | None:
        return self.db.scalar(
            select(OutreachDraft).where(
                OutreachDraft.user_id == user_id, OutreachDraft.id == draft_id
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[OutreachDraft]:
        return list(
            self.db.scalars(
                select(OutreachDraft)
                .where(OutreachDraft.user_id == user_id)
                .order_by(OutreachDraft.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> OutreachDraft:
        draft = OutreachDraft(**fields)
        self.db.add(draft)
        self.db.flush()
        return draft

    def save(self, draft: OutreachDraft) -> None:
        self.db.commit()
        self.db.refresh(draft)
