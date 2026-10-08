import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.models.job import Job
from app.models.job_source import JobSource
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository):
    def get(self, job_id: uuid.UUID) -> Job | None:
        return self.db.get(Job, job_id)

    def get_many(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, Job]:
        if not ids:
            return {}
        rows = self.db.scalars(select(Job).where(Job.id.in_(ids)))
        return {job.id: job for job in rows}

    def find_by_content_hash(self, content_hash: str) -> Job | None:
        return self.db.scalars(
            select(Job).where(Job.content_hash == content_hash).order_by(Job.created_at).limit(1)
        ).first()

    def find_by_company_and_title(self, company_id: uuid.UUID, title: str) -> Job | None:
        return self.db.scalars(
            select(Job)
            .where(Job.company_id == company_id, func.lower(Job.title) == title.lower())
            .order_by(Job.created_at)
            .limit(1)
        ).first()

    def list_for_user(
        self, user_id: uuid.UUID, *, limit: int, offset: int, status: str | None = None
    ) -> list[Job]:
        statement = (
            select(Job)
            .join(JobSource, JobSource.job_id == Job.id)
            .where(JobSource.added_by_user_id == user_id)
        )
        if status is not None:
            statement = statement.where(Job.status == status)
        return list(
            self.db.scalars(
                statement.distinct().order_by(Job.last_seen_at.desc()).limit(limit).offset(offset)
            )
        )

    def list_due_for_recheck(self, due_before: datetime, *, limit: int) -> list[Job]:
        return list(
            self.db.scalars(
                select(Job)
                .where(
                    Job.status == "Active",
                    Job.next_check_at.is_not(None),
                    Job.next_check_at <= due_before,
                )
                .order_by(Job.next_check_at)
                .limit(limit)
            )
        )

    def create(self, **fields: Any) -> Job:
        job = Job(**fields)
        self.db.add(job)
        self.db.flush()
        return job
