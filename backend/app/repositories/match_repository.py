import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.models.job import Job
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

    def list_eligible(
        self, user_id: uuid.UUID, *, min_overall: float, since: datetime | None
    ) -> list[Match]:
        statement = (
            select(Match)
            .join(Job, Job.id == Match.job_id)
            .where(
                Match.user_id == user_id,
                Match.overall >= min_overall,
                Job.status == "Active",
            )
        )
        if since is not None:
            statement = statement.where(Match.updated_at > since)
        return list(self.db.scalars(statement.order_by(Match.overall.desc())))

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
