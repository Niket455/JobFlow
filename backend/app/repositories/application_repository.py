import uuid
from typing import Any

from sqlalchemy import select

from app.models.application import Application
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, application_id: uuid.UUID) -> Application | None:
        return self.db.scalar(
            select(Application).where(
                Application.user_id == user_id, Application.id == application_id
            )
        )

    def get_for_user_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> Application | None:
        return self.db.scalar(
            select(Application).where(Application.user_id == user_id, Application.job_id == job_id)
        )

    def list_for_user(self, user_id: uuid.UUID, *, limit: int, offset: int) -> list[Application]:
        return list(
            self.db.scalars(
                select(Application)
                .where(Application.user_id == user_id)
                .order_by(Application.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )

    def create(self, **fields: Any) -> Application:
        application = Application(**fields)
        self.db.add(application)
        self.db.flush()
        return application
