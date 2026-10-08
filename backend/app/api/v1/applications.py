import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationEventRead,
    ApplicationRead,
    ApplicationSummary,
)
from app.services.application_service import (
    ApplicationNotFoundError,
    ApplicationService,
    DuplicateApplicationError,
)
from app.services.job_service import JobNotFoundError

router = APIRouter(prefix="/applications", tags=["applications"])


def _service(db: DbSession) -> ApplicationService:
    return ApplicationService(
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate, current_user: CurrentUser, db: DbSession
) -> ApplicationRead:
    try:
        return _service(db).create(current_user, payload)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except DuplicateApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "An application already exists for this job",
                "application_id": str(exc.application_id),
            },
        ) from exc


@router.get("", response_model=list[ApplicationSummary])
def list_applications(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[ApplicationSummary]:
    return _service(db).list_for_user(current_user, limit=limit, offset=offset)


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> ApplicationRead:
    try:
        return _service(db).get(current_user, application_id)
    except ApplicationNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/{application_id}/events",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_application_event(
    application_id: uuid.UUID,
    payload: ApplicationEventCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ApplicationRead:
    try:
        return _service(db).add_event(current_user, application_id, payload)
    except ApplicationNotFoundError as exc:
        raise _not_found() from exc


@router.get("/{application_id}/events", response_model=list[ApplicationEventRead])
def list_application_events(
    application_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> list[ApplicationEventRead]:
    try:
        return _service(db).list_events(current_user, application_id)
    except ApplicationNotFoundError as exc:
        raise _not_found() from exc
