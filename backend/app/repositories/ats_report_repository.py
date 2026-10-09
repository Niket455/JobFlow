import uuid
from typing import Any

from sqlalchemy import select

from app.models.ats_report import AtsReportRecord
from app.repositories.base import BaseRepository


class AtsReportRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, report_id: uuid.UUID) -> AtsReportRecord | None:
        return self.db.scalar(
            select(AtsReportRecord).where(
                AtsReportRecord.user_id == user_id, AtsReportRecord.id == report_id
            )
        )

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        resume_version_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AtsReportRecord]:
        query = select(AtsReportRecord).where(AtsReportRecord.user_id == user_id)
        if resume_version_id is not None:
            query = query.where(AtsReportRecord.resume_version_id == resume_version_id)
        if job_id is not None:
            query = query.where(AtsReportRecord.job_id == job_id)
        return list(
            self.db.scalars(
                query.order_by(AtsReportRecord.created_at.desc()).limit(limit).offset(offset)
            )
        )

    def create(self, **fields: Any) -> AtsReportRecord:
        record = AtsReportRecord(**fields)
        self.db.add(record)
        self.db.flush()
        return record
