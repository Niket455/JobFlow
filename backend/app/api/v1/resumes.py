import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status

from app.api.deps import CurrentUser, DbSession, GatewayDep, StorageDep
from app.core.config import settings
from app.core.media_types import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ats import AtsReport
from app.schemas.job_analysis import JobAnalysisData
from app.schemas.resume import ResumeVersionRead, ResumeVersionSummary
from app.schemas.tailor import TailorRequest, TailorRunRead
from app.services.ats_analyzer import analyze_ats
from app.services.job_service import JobNotFoundError
from app.services.resume_parser import UnsupportedFileTypeError
from app.services.resume_service import ResumeFormat, ResumeNotFoundError, ResumeService
from app.services.tailor_service import build_tailor_service

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_CONTENT_TYPES = {PDF_CONTENT_TYPE, DOCX_CONTENT_TYPE}


def _service(db: DbSession, storage: StorageDep, gateway: GatewayDep) -> ResumeService:
    return ResumeService(
        ResumeVersionRepository(db),
        UserRepository(db),
        storage,
        gateway,
        model=settings.llm_cheap_model,
    )


@router.post("", response_model=ResumeVersionRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
    file: Annotated[UploadFile, File()],
) -> ResumeVersionRead:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are supported",
        )
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large"
        )
    try:
        return await _service(db, storage, gateway).upload(
            current_user,
            filename=file.filename or "resume",
            content_type=file.content_type,
            data=data,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type"
        ) from exc


@router.get("", response_model=list[ResumeVersionSummary])
def list_resumes(
    current_user: CurrentUser, db: DbSession, storage: StorageDep, gateway: GatewayDep
) -> list[ResumeVersionSummary]:
    return _service(db, storage, gateway).list(current_user)


@router.get("/{resume_id}", response_model=ResumeVersionRead)
def get_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
) -> ResumeVersionRead:
    try:
        return _service(db, storage, gateway).get(current_user, resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc


@router.get("/{resume_id}/export")
def export_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
    resume_format: Annotated[ResumeFormat, Query(alias="format")] = "pdf",
) -> Response:
    try:
        data, filename, content_type = _service(db, storage, gateway).export(
            current_user, resume_id, resume_format
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{resume_id}/tailor", response_model=TailorRunRead, status_code=status.HTTP_201_CREATED
)
async def tailor_resume(
    resume_id: uuid.UUID,
    payload: TailorRequest,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
) -> TailorRunRead:
    try:
        return await build_tailor_service(db, storage, gateway).tailor(
            current_user, resume_id, payload
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("/{resume_id}/ats-report", response_model=AtsReport)
def resume_ats_report(
    resume_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
    job_id: Annotated[uuid.UUID | None, Query()] = None,
) -> AtsReport:
    try:
        version = _service(db, storage, gateway).get(current_user, resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    if version.parsed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        )
    analysis = None
    if job_id is not None:
        if not JobSourceRepository(db).exists(job_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        record = JobAnalysisRepository(db).get_for_job(job_id)
        analysis = JobAnalysisData.model_validate(record.data) if record is not None else None
    return analyze_ats(version.parsed, analysis)
