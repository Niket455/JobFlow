import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, GatewayDep
from app.schemas.cover_letter import CoverLetterRead, CoverLetterRequest, CoverLetterSummary
from app.services.cover_letter_service import (
    CoverLetterNotFoundError,
    build_cover_letter_service,
)
from app.services.job_service import JobNotFoundError
from app.services.resume_service import ResumeNotFoundError

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


@router.post("", response_model=CoverLetterRead, status_code=status.HTTP_201_CREATED)
async def generate_cover_letter(
    payload: CoverLetterRequest, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> CoverLetterRead:
    try:
        return await build_cover_letter_service(db, gateway).generate(current_user, payload)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("", response_model=list[CoverLetterSummary])
def list_cover_letters(
    current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> list[CoverLetterSummary]:
    return build_cover_letter_service(db, gateway).list_for_user(current_user)


@router.get("/{letter_id}", response_model=CoverLetterRead)
def get_cover_letter(
    letter_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> CoverLetterRead:
    try:
        return build_cover_letter_service(db, gateway).get(current_user, letter_id)
    except CoverLetterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found"
        ) from exc
