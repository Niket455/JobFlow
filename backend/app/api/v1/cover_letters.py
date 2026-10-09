import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, GatewayDep
from app.schemas.cover_letter import (
    CoverLetterRead,
    CoverLetterRequest,
    CoverLetterReviseRequest,
    CoverLetterSummary,
)
from app.services.cover_letter_service import (
    CoverLetterNotFoundError,
    CoverLetterService,
    build_cover_letter_service,
)
from app.services.job_service import JobNotFoundError
from app.services.resume_service import ResumeNotFoundError

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


def _service(db: DbSession, gateway: GatewayDep) -> CoverLetterService:
    return build_cover_letter_service(db, gateway)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found")


@router.post("", response_model=CoverLetterRead, status_code=status.HTTP_201_CREATED)
async def generate_cover_letter(
    payload: CoverLetterRequest, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> CoverLetterRead:
    try:
        return await _service(db, gateway).generate(current_user, payload)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("", response_model=list[CoverLetterSummary])
def list_cover_letters(
    current_user: CurrentUser,
    db: DbSession,
    gateway: GatewayDep,
    job_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CoverLetterSummary]:
    return _service(db, gateway).list_for_user(
        current_user, job_id=job_id, limit=limit, offset=offset
    )


@router.get("/{letter_id}", response_model=CoverLetterRead)
def get_cover_letter(
    letter_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> CoverLetterRead:
    try:
        return _service(db, gateway).get(current_user, letter_id)
    except CoverLetterNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/{letter_id}/revise", response_model=CoverLetterRead, status_code=status.HTTP_201_CREATED
)
async def revise_cover_letter(
    letter_id: uuid.UUID,
    payload: CoverLetterReviseRequest,
    current_user: CurrentUser,
    db: DbSession,
    gateway: GatewayDep,
) -> CoverLetterRead:
    try:
        return await _service(db, gateway).revise(current_user, letter_id, payload.instructions)
    except CoverLetterNotFoundError as exc:
        raise _not_found() from exc


@router.delete("/{letter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover_letter(
    letter_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> None:
    try:
        _service(db, gateway).delete(current_user, letter_id)
    except CoverLetterNotFoundError as exc:
        raise _not_found() from exc
