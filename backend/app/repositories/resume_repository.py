import uuid

from sqlalchemy import select

from app.models.resume_version import ResumeVersion
from app.repositories.base import BaseRepository


class ResumeVersionRepository(BaseRepository):
    def list_for_user(self, user_id: uuid.UUID) -> list[ResumeVersion]:
        return list(
            self.db.scalars(
                select(ResumeVersion)
                .where(ResumeVersion.user_id == user_id)
                .order_by(ResumeVersion.created_at)
            )
        )

    def get_for_user(self, user_id: uuid.UUID, version_id: uuid.UUID) -> ResumeVersion | None:
        return self.db.scalar(
            select(ResumeVersion).where(
                ResumeVersion.user_id == user_id, ResumeVersion.id == version_id
            )
        )

    def create(
        self,
        *,
        user_id: uuid.UUID,
        label: str,
        is_master: bool,
        filename: str,
        content_type: str,
        storage_key: str,
        size_bytes: int,
        text_enc: str,
        parsed_enc: str,
        confidence: dict[str, float] | None,
        parent_version_id: uuid.UUID | None = None,
    ) -> ResumeVersion:
        record = ResumeVersion(
            user_id=user_id,
            label=label,
            is_master=is_master,
            parent_version_id=parent_version_id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            size_bytes=size_bytes,
            text_enc=text_enc,
            parsed_enc=parsed_enc,
            confidence=confidence,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
