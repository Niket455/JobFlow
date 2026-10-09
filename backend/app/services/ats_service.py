import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import ObjectStorage
from app.gateway.gateway import LLMGateway
from app.models.ats_report import AtsReportRecord
from app.models.user import User
from app.repositories.ats_report_repository import AtsReportRepository
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ats import AtsReport, AtsReportRead, AtsReportSummary
from app.schemas.job_analysis import JobAnalysisData
from app.services.ats_analyzer import analyze_ats
from app.services.job_service import JobNotFoundError
from app.services.resume_service import ResumeNotFoundError, ResumeService


class AtsReportNotFoundError(Exception):
    pass


class AtsService:
    """Computes the deterministic ATS report and persists snapshots for history."""

    def __init__(
        self,
        resumes: ResumeService,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        reports: AtsReportRepository,
    ) -> None:
        self.resumes = resumes
        self.sources = sources
        self.analyses = analyses
        self.reports = reports

    def compute(self, user: User, resume_id: uuid.UUID, job_id: uuid.UUID | None) -> AtsReport:
        version = self.resumes.get(user, resume_id)
        if version.parsed is None:
            raise ResumeNotFoundError
        return analyze_ats(version.parsed, self._analysis(user, job_id))

    def generate(self, user: User, resume_id: uuid.UUID, job_id: uuid.UUID | None) -> AtsReportRead:
        report = self.compute(user, resume_id, job_id)
        record = self.reports.create(
            user_id=user.id,
            resume_version_id=resume_id,
            job_id=job_id,
            score=report.score,
            grade=report.grade,
            report=report.model_dump(),
        )
        self.reports.commit()
        return _to_read(record)

    def list_for_user(
        self,
        user: User,
        *,
        resume_version_id: uuid.UUID | None,
        job_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> list[AtsReportSummary]:
        records = self.reports.list_for_user(
            user.id,
            resume_version_id=resume_version_id,
            job_id=job_id,
            limit=limit,
            offset=offset,
        )
        return [AtsReportSummary.model_validate(record) for record in records]

    def get(self, user: User, report_id: uuid.UUID) -> AtsReportRead:
        record = self.reports.get_for_user(user.id, report_id)
        if record is None:
            raise AtsReportNotFoundError
        return _to_read(record)

    def _analysis(self, user: User, job_id: uuid.UUID | None) -> JobAnalysisData | None:
        if job_id is None:
            return None
        if not self.sources.exists(job_id, user.id):
            raise JobNotFoundError
        record = self.analyses.get_for_job(job_id)
        return JobAnalysisData.model_validate(record.data) if record is not None else None


def _to_read(record: AtsReportRecord) -> AtsReportRead:
    return AtsReportRead(
        id=record.id,
        resume_version_id=record.resume_version_id,
        job_id=record.job_id,
        score=record.score,
        grade=record.grade,
        report=AtsReport.model_validate(record.report),
        created_at=record.created_at,
    )


def build_ats_service(db: Session, storage: ObjectStorage, gateway: LLMGateway) -> AtsService:
    return AtsService(
        ResumeService(
            ResumeVersionRepository(db),
            UserRepository(db),
            storage,
            gateway,
            model=settings.llm_cheap_model,
        ),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        AtsReportRepository(db),
    )
