import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, GatewayDep, StorageDep
from app.schemas.ats import AtsReportRead, AtsReportSummary
from app.services.ats_service import AtsReportNotFoundError, AtsService, build_ats_service

router = APIRouter(prefix="/ats-reports", tags=["ats-reports"])


def _service(db: DbSession, storage: StorageDep, gateway: GatewayDep) -> AtsService:
    return build_ats_service(db, storage, gateway)


@router.get("", response_model=list[AtsReportSummary])
def list_ats_reports(
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
    resume_version_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[AtsReportSummary]:
    return _service(db, storage, gateway).list_for_user(
        current_user,
        resume_version_id=resume_version_id,
        job_id=job_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=AtsReportRead)
def get_ats_report(
    report_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
) -> AtsReportRead:
    try:
        return _service(db, storage, gateway).get(current_user, report_id)
    except AtsReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ATS report not found"
        ) from exc
