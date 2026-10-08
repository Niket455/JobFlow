import uuid
from typing import Any

from sqlalchemy import select

from app.models.job_analysis import JobAnalysis
from app.repositories.base import BaseRepository


class JobAnalysisRepository(BaseRepository):
    def get_for_job(self, job_id: uuid.UUID) -> JobAnalysis | None:
        return self.db.scalar(select(JobAnalysis).where(JobAnalysis.job_id == job_id))

    def upsert(self, job_id: uuid.UUID, data: dict[str, Any]) -> JobAnalysis:
        record = self.get_for_job(job_id)
        if record is None:
            record = JobAnalysis(job_id=job_id, data=data)
            self.db.add(record)
        else:
            record.data = data
        self.db.commit()
        self.db.refresh(record)
        return record
