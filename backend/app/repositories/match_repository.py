import uuid
from typing import Any

from sqlalchemy import select

from app.models.match import Match
from app.repositories.base import BaseRepository


class MatchRepository(BaseRepository):
    def get_for_user_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> Match | None:
        return self.db.scalar(select(Match).where(Match.user_id == user_id, Match.job_id == job_id))

    def get_for_user(self, user_id: uuid.UUID, match_id: uuid.UUID) -> Match | None:
        return self.db.scalar(select(Match).where(Match.user_id == user_id, Match.id == match_id))

    def list_for_user(self, user_id: uuid.UUID, *, limit: int, offset: int) -> list[Match]:
        return list(
            self.db.scalars(
                select(Match)
                .where(Match.user_id == user_id)
                .order_by(Match.overall.desc(), Match.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    def upsert(self, user_id: uuid.UUID, job_id: uuid.UUID, data: dict[str, Any]) -> Match:
        record = self.get_for_user_job(user_id, job_id)
        if record is None:
            record = Match(user_id=user_id, job_id=job_id, **data)
            self.db.add(record)
        else:
            for key, value in data.items():
                setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record
