import uuid
from pathlib import Path
from typing import Literal

from app.core.crypto import decrypt_text, encrypt_text
from app.core.media_types import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from app.core.storage import ObjectStorage
from app.gateway.gateway import LLMGateway
from app.models.resume_version import ResumeVersion
from app.models.user import User
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import ProfileData
from app.schemas.resume import ResumeVersionRead, ResumeVersionSummary
from app.services.encryption import ensure_data_key
from app.services.resume_parser import extract_text, parse_resume
from app.services.resume_renderer import render_docx, render_pdf

ResumeFormat = Literal["pdf", "docx"]


class ResumeNotFoundError(Exception):
    pass


class ResumeService:
    def __init__(
        self,
        resumes: ResumeVersionRepository,
        users: UserRepository,
        storage: ObjectStorage,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.resumes = resumes
        self.users = users
        self.storage = storage
        self.gateway = gateway
        self.model = model

    async def upload(
        self, user: User, *, filename: str, content_type: str, data: bytes
    ) -> ResumeVersionRead:
        text = extract_text(content_type, data)
        data_key = ensure_data_key(user, self.users)
        profile, confidence = await parse_resume(self.gateway, model=self.model, text=text)

        existing = self.resumes.list_for_user(user.id)
        is_master = len(existing) == 0
        label = "Master" if is_master else f"Version {len(existing) + 1}"
        storage_key = f"users/{user.id}/resumes/{uuid.uuid4().hex}/{filename}"
        self.storage.put(storage_key, data, content_type)

        record = self.resumes.create(
            user_id=user.id,
            label=label,
            is_master=is_master,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            size_bytes=len(data),
            text_enc=encrypt_text(data_key, text),
            parsed_enc=encrypt_text(data_key, profile.model_dump_json()),
            confidence=confidence,
        )
        return self._to_read(record, data_key)

    def list(self, user: User) -> list[ResumeVersionSummary]:
        return [
            ResumeVersionSummary.model_validate(record)
            for record in self.resumes.list_for_user(user.id)
        ]

    def get(self, user: User, version_id: uuid.UUID) -> ResumeVersionRead:
        record = self.resumes.get_for_user(user.id, version_id)
        if record is None:
            raise ResumeNotFoundError
        return self._to_read(record, ensure_data_key(user, self.users))

    def export(
        self, user: User, version_id: uuid.UUID, fmt: ResumeFormat
    ) -> tuple[bytes, str, str]:
        record = self.resumes.get_for_user(user.id, version_id)
        if record is None or record.parsed_enc is None:
            raise ResumeNotFoundError
        data_key = ensure_data_key(user, self.users)
        profile = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        if fmt == "pdf":
            data, content_type = render_pdf(profile), PDF_CONTENT_TYPE
        else:
            data, content_type = render_docx(profile), DOCX_CONTENT_TYPE
        filename = f"{Path(record.filename).stem or 'resume'}.{fmt}"
        return data, filename, content_type

    @staticmethod
    def _to_read(record: ResumeVersion, data_key: str) -> ResumeVersionRead:
        parsed = None
        if record.parsed_enc:
            parsed = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        return ResumeVersionRead(
            id=record.id,
            label=record.label,
            is_master=record.is_master,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            created_at=record.created_at,
            confidence=record.confidence,
            parsed=parsed,
        )
