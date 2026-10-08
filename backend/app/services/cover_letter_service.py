import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.cover_letter import CoverLetter
from app.models.user import User
from app.repositories.cover_letter_repository import CoverLetterRepository
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.cover_letter import (
    CoverLetterClaimRead,
    CoverLetterDraft,
    CoverLetterRead,
    CoverLetterRequest,
    CoverLetterSummary,
)
from app.schemas.profile import ProfileData
from app.services.encryption import ensure_data_key
from app.services.job_context import job_text
from app.services.job_service import JobNotFoundError
from app.services.resume_service import ResumeNotFoundError
from app.services.tailor_grounding import is_grounded


class CoverLetterNotFoundError(Exception):
    pass


class CoverLetterService:
    """LLM drafts a cover letter; a deterministic verifier grounds each claim in resume/JD."""

    def __init__(
        self,
        resumes: ResumeVersionRepository,
        letters: CoverLetterRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        users: UserRepository,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.resumes = resumes
        self.letters = letters
        self.jobs = jobs
        self.sources = sources
        self.analyses = analyses
        self.users = users
        self.gateway = gateway
        self.model = model

    async def generate(self, user: User, payload: CoverLetterRequest) -> CoverLetterRead:
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
        context = job_text(job, analysis)

        prompt = load_prompt("cover_letter").format(
            resume_json=profile.model_dump_json(),
            resume_text=resume_text or profile.model_dump_json(),
            job_text=context,
            instructions=payload.instructions or "(none)",
        )
        draft = await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)], model=self.model, schema=CoverLetterDraft
        )

        corpus = f"{resume_text or profile.model_dump_json()}\n{context}"
        claims = [
            CoverLetterClaimRead(
                text=claim.text,
                source_span=claim.source_span,
                grounded=is_grounded(claim.source_span, corpus),
            )
            for claim in draft.claims
        ]
        letter = self.letters.create(
            user_id=user.id,
            job_id=job.id,
            resume_version_id=record.id,
            label=f"Cover letter — {job.title}",
            model=self.model,
            subject=draft.subject,
            body_enc=encrypt_text(data_key, draft.body),
            grounding=[claim.model_dump() for claim in claims],
        )
        self.letters.commit()
        return _to_read(letter, data_key)

    def list_for_user(self, user: User) -> list[CoverLetterSummary]:
        return [
            CoverLetterSummary.model_validate(letter)
            for letter in self.letters.list_for_user(user.id)
        ]

    def get(self, user: User, letter_id: uuid.UUID) -> CoverLetterRead:
        letter = self.letters.get_for_user(user.id, letter_id)
        if letter is None:
            raise CoverLetterNotFoundError
        data_key = ensure_data_key(user, self.users)
        return _to_read(letter, data_key)


def build_cover_letter_service(db: Session, gateway: LLMGateway) -> CoverLetterService:
    return CoverLetterService(
        ResumeVersionRepository(db),
        CoverLetterRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        UserRepository(db),
        gateway,
        model=settings.llm_strong_model,
    )


def _to_read(letter: CoverLetter, data_key: str) -> CoverLetterRead:
    claims = [CoverLetterClaimRead(**item) for item in letter.grounding]
    return CoverLetterRead(
        id=letter.id,
        job_id=letter.job_id,
        resume_version_id=letter.resume_version_id,
        label=letter.label,
        model=letter.model,
        subject=letter.subject,
        body=decrypt_text(data_key, letter.body_enc),
        claims=claims,
        blocked_count=sum(1 for claim in claims if not claim.grounded),
        created_at=letter.created_at,
    )
