import uuid
from typing import Any

from sqlalchemy import select

from app.models.job_source import JobSource
from app.repositories.base import BaseRepository


class JobSourceRepository(BaseRepository):
    def get_for_url_and_user(self, canonical_url: str, user_id: uuid.UUID) -> JobSource | None:
        return self.db.scalar(
            select(JobSource).where(
                JobSource.canonical_url == canonical_url,
                JobSource.added_by_user_id == user_id,
            )
        )

    def list_for_job(self, job_id: uuid.UUID) -> list[JobSource]:
        return list(
            self.db.scalars(
                select(JobSource)
                .where(JobSource.job_id == job_id)
                .order_by(JobSource.first_seen_at)
            )
        )

    def latest_for_job(self, job_id: uuid.UUID) -> JobSource | None:
        return self.db.scalars(
            select(JobSource)
            .where(JobSource.job_id == job_id)
            .order_by(JobSource.last_seen_at.desc())
            .limit(1)
        ).first()

    def exists(self, job_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        found = self.db.scalar(
            select(JobSource.id)
            .where(JobSource.job_id == job_id, JobSource.added_by_user_id == user_id)
            .limit(1)
        )
        return found is not None

    def create(self, **fields: Any) -> JobSource:
        source = JobSource(**fields)
        self.db.add(source)
        self.db.flush()
        return source
