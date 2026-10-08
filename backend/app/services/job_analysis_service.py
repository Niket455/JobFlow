import uuid

from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.job_analysis import JobAnalysis
from app.models.user import User
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.job_analysis import JobAnalysisData, JobAnalysisRead
from app.services.job_service import JobNotFoundError


class JobAnalysisNotFoundError(Exception):
    pass


class JobAnalysisService:
    """LLM extraction of a job posting into a validated, confidence-scored analysis."""

    def __init__(
        self,
        jobs: JobRepository,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.jobs = jobs
        self.sources = sources
        self.analyses = analyses
        self.gateway = gateway
        self.model = model

    def get(self, user: User, job_id: uuid.UUID) -> JobAnalysisRead:
        self._ensure_visible(user, job_id)
        record = self.analyses.get_for_job(job_id)
        if record is None:
            raise JobAnalysisNotFoundError
        return self._to_read(job_id, record)

    async def analyze(self, user: User, job_id: uuid.UUID) -> JobAnalysisRead:
        self._ensure_visible(user, job_id)
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError
        prompt = load_prompt("job_analysis").format(job_description=job.description or "")
        data = await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)],
            model=self.model,
            schema=JobAnalysisData,
        )
        record = self.analyses.upsert(job_id, data.model_dump())
        return self._to_read(job_id, record)

    def _ensure_visible(self, user: User, job_id: uuid.UUID) -> None:
        if not self.sources.exists(job_id, user.id):
            raise JobNotFoundError

    @staticmethod
    def _to_read(job_id: uuid.UUID, record: JobAnalysis) -> JobAnalysisRead:
        return JobAnalysisRead.model_validate(
            {**record.data, "job_id": job_id, "updated_at": record.updated_at}
        )
