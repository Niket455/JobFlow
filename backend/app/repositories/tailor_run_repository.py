import uuid
from typing import Any

from sqlalchemy import select

from app.models.tailor_run import TailorRun
from app.repositories.base import BaseRepository


class TailorRunRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, run_id: uuid.UUID) -> TailorRun | None:
        return self.db.scalar(
            select(TailorRun).where(TailorRun.user_id == user_id, TailorRun.id == run_id)
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[TailorRun]:
        return list(
            self.db.scalars(
                select(TailorRun)
                .where(TailorRun.user_id == user_id)
                .order_by(TailorRun.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> TailorRun:
        run = TailorRun(**fields)
        self.db.add(run)
        self.db.flush()
        return run

    def save(self, run: TailorRun) -> None:
        self.db.commit()
        self.db.refresh(run)
