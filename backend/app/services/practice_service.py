import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.practice_session import PracticeSession
from app.models.user import User
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.practice_session_repository import PracticeSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.interview import (
    AnswerFeedback,
    AnswerSignalsRead,
    PracticeRequest,
    PracticeSessionRead,
    PracticeSessionSummary,
)
from app.services.answer_signals import analyze_answer
from app.services.encryption import ensure_data_key
from app.services.job_context import job_text
from app.services.job_service import JobNotFoundError


class PracticeSessionNotFoundError(Exception):
    pass


class PracticeService:
    """LLM scores a timed answer against a rubric; deterministic signals are stored alongside."""

    def __init__(
        self,
        sessions: PracticeSessionRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        users: UserRepository,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.sessions = sessions
        self.jobs = jobs
        self.sources = sources
        self.analyses = analyses
        self.users = users
        self.gateway = gateway
        self.model = model

    async def evaluate(self, user: User, payload: PracticeRequest) -> PracticeSessionRead:
        context = "(none)"
        if payload.job_id is not None:
            job = self.jobs.get(payload.job_id)
            if job is None or not self.sources.exists(payload.job_id, user.id):
                raise JobNotFoundError
            context = job_text(job, self.analyses.get_for_job(job.id))

        data_key = ensure_data_key(user, self.users)
        prompt = load_prompt("answer_feedback").format(
            question=payload.question,
            answer=payload.answer,
            job_text=context,
        )
        feedback = await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)], model=self.model, schema=AnswerFeedback
        )
        session = self.sessions.create(
            user_id=user.id,
            job_id=payload.job_id,
            question=payload.question,
            category=payload.category or "general",
            duration_seconds=payload.duration_seconds,
            answer_enc=encrypt_text(data_key, payload.answer),
            rubric=feedback.model_dump(),
            score=feedback.overall,
        )
        self.sessions.commit()
        return _to_read(session, data_key)

    def get(self, user: User, session_id: uuid.UUID) -> PracticeSessionRead:
        session = self.sessions.get_for_user(user.id, session_id)
        if session is None:
            raise PracticeSessionNotFoundError
        return _to_read(session, ensure_data_key(user, self.users))

    def list_for_user(self, user: User) -> list[PracticeSessionSummary]:
        return [
            PracticeSessionSummary.model_validate(session)
            for session in self.sessions.list_for_user(user.id)
        ]


def build_practice_service(db: Session, gateway: LLMGateway) -> PracticeService:
    return PracticeService(
        PracticeSessionRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        UserRepository(db),
        gateway,
        model=settings.llm_strong_model,
    )


def _to_read(session: PracticeSession, data_key: str) -> PracticeSessionRead:
    answer = decrypt_text(data_key, session.answer_enc)
    signals = analyze_answer(answer)
    return PracticeSessionRead(
        id=session.id,
        job_id=session.job_id,
        question=session.question,
        category=session.category,
        duration_seconds=session.duration_seconds,
        answer=answer,
        rubric=AnswerFeedback.model_validate(session.rubric),
        score=session.score,
        signals=AnswerSignalsRead(
            word_count=signals.word_count,
            has_metric=signals.has_metric,
            star_coverage=signals.star_coverage,
        ),
        created_at=session.created_at,
    )
