import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.interview_kit import InterviewKit
from app.models.user import User
from app.repositories.interview_kit_repository import InterviewKitRepository
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.interview import (
    InterviewKitDraft,
    InterviewKitRead,
    InterviewKitRequest,
    InterviewKitSummary,
)
from app.schemas.profile import ProfileData
from app.services.encryption import ensure_data_key
from app.services.job_context import job_text
from app.services.job_service import JobNotFoundError
from app.services.resume_service import ResumeNotFoundError


class InterviewKitNotFoundError(Exception):
    pass


class InterviewKitService:
    """LLM builds a personalized interview question set from the resume and the job."""

    def __init__(
        self,
        resumes: ResumeVersionRepository,
        kits: InterviewKitRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        users: UserRepository,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.resumes = resumes
        self.kits = kits
        self.jobs = jobs
        self.sources = sources
        self.analyses = analyses
        self.users = users
        self.gateway = gateway
        self.model = model

    async def generate(self, user: User, payload: InterviewKitRequest) -> InterviewKitRead:
        if payload.resume_version_id is not None:
            record = self.resumes.get_for_user(user.id, payload.resume_version_id)
        else:
            records = self.resumes.list_for_user(user.id)
            record = records[-1] if records else None
        if record is None or record.parsed_enc is None:
            raise ResumeNotFoundError

        job = self.jobs.get(payload.job_id)
        if job is None or not self.sources.exists(payload.job_id, user.id):
            raise JobNotFoundError

        data_key = ensure_data_key(user, self.users)
        profile = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        resume_text = decrypt_text(data_key, record.text_enc) if record.text_enc else ""
        analysis = self.analyses.get_for_job(job.id)
        prompt = load_prompt("interview_kit").format(
            resume_json=profile.model_dump_json(),
            resume_text=resume_text or profile.model_dump_json(),
            job_text=job_text(job, analysis),
        )
        draft = await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)], model=self.model, schema=InterviewKitDraft
        )
        kit = self.kits.create(
            user_id=user.id,
            job_id=job.id,
            resume_version_id=record.id,
            model=self.model,
            questions=[question.model_dump() for question in draft.questions],
        )
        self.kits.commit()
        return InterviewKitRead.model_validate(kit)

    def get(self, user: User, kit_id: uuid.UUID) -> InterviewKitRead:
        return InterviewKitRead.model_validate(self._get(user, kit_id))

    def list_for_user(
        self, user: User, job_id: uuid.UUID | None = None
    ) -> list[InterviewKitSummary]:
        return [
            InterviewKitSummary(
                id=kit.id,
                job_id=kit.job_id,
                question_count=len(kit.questions),
                created_at=kit.created_at,
            )
            for kit in self.kits.list_for_user(user.id, job_id=job_id)
        ]

    def _get(self, user: User, kit_id: uuid.UUID) -> InterviewKit:
        kit = self.kits.get_for_user(user.id, kit_id)
        if kit is None:
            raise InterviewKitNotFoundError
        return kit


def build_interview_kit_service(db: Session, gateway: LLMGateway) -> InterviewKitService:
    return InterviewKitService(
        ResumeVersionRepository(db),
        InterviewKitRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        UserRepository(db),
        gateway,
        model=settings.llm_strong_model,
    )
