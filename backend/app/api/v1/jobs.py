import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.base import FetchError, RobotsDisallowedError
from app.api.deps import CurrentUser, DbSession, FetcherDep, GatewayDep
from app.core.config import settings
from app.repositories.company_repository import CompanyRepository
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.job import IngestRequest, JobRead, JobSourceRead, JobSummary
from app.schemas.job_analysis import JobAnalysisRead
from app.schemas.match import MatchRead
from app.services.job_analysis_service import JobAnalysisNotFoundError, JobAnalysisService
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_refresh_service import JobRefreshService
from app.services.job_service import JobNotFoundError, JobService
from app.services.match_service import build_match_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _ingestion(db: DbSession, fetcher: FetcherDep) -> JobIngestionService:
    return JobIngestionService(
        CompanyRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
        FetchLogRepository(db),
        fetcher,
    )


def _refresh(db: DbSession, fetcher: FetcherDep) -> JobRefreshService:
    return JobRefreshService(
        JobRepository(db), JobSourceRepository(db), FetchLogRepository(db), fetcher
    )


def _analysis(db: DbSession, gateway: GatewayDep) -> JobAnalysisService:
    return JobAnalysisService(
        JobRepository(db),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        gateway,
        model=settings.llm_cheap_model,
    )


def _jobs(db: DbSession) -> JobService:
    return JobService(JobRepository(db), JobSourceRepository(db), CompanyRepository(db))


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def ingest_job(
    payload: IngestRequest, current_user: CurrentUser, db: DbSession, fetcher: FetcherDep
) -> JobRead:
    if not settings.enable_user_url_ingestion:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User-URL ingestion is disabled"
        )
    try:
        return _ingestion(db, fetcher).ingest(current_user, str(payload.url))
    except RobotsDisallowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="robots.txt disallows fetching this URL"
        ) from exc
    except FetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not fetch the URL"
        ) from exc


@router.get("", response_model=list[JobSummary])
def list_jobs(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[JobSummary]:
    return _jobs(db).list_for_user(current_user, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> JobRead:
    try:
        return _jobs(db).get(current_user, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("/{job_id}/sources", response_model=list[JobSourceRead])
def list_job_sources(
    job_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> list[JobSourceRead]:
    try:
        return _jobs(db).list_sources(current_user, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.post("/{job_id}/refresh", response_model=JobRead)
def refresh_job(
    job_id: uuid.UUID, current_user: CurrentUser, db: DbSession, fetcher: FetcherDep
) -> JobRead:
    if _refresh(db, fetcher).refresh(current_user, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _jobs(db).get(current_user, job_id)


@router.post("/{job_id}/analyze", response_model=JobAnalysisRead)
async def analyze_job(
    job_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> JobAnalysisRead:
    try:
        return await _analysis(db, gateway).analyze(current_user, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("/{job_id}/analysis", response_model=JobAnalysisRead)
def get_job_analysis(
    job_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> JobAnalysisRead:
    try:
        return _analysis(db, gateway).get(current_user, job_id)
    except (JobNotFoundError, JobAnalysisNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found"
        ) from exc


@router.post("/{job_id}/match", response_model=MatchRead)
def match_job(job_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> MatchRead:
    try:
        return build_match_service(db).match(current_user, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
