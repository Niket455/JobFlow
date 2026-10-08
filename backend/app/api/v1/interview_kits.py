import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, GatewayDep
from app.schemas.interview import InterviewKitRead, InterviewKitRequest, InterviewKitSummary
from app.services.interview_kit_service import (
    InterviewKitNotFoundError,
    build_interview_kit_service,
)
from app.services.job_service import JobNotFoundError
from app.services.resume_service import ResumeNotFoundError

router = APIRouter(prefix="/interview-kits", tags=["interview-kits"])


@router.post("", response_model=InterviewKitRead, status_code=status.HTTP_201_CREATED)
async def generate_interview_kit(
    payload: InterviewKitRequest, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> InterviewKitRead:
    try:
        return await build_interview_kit_service(db, gateway).generate(current_user, payload)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("", response_model=list[InterviewKitSummary])
def list_interview_kits(
    current_user: CurrentUser,
    db: DbSession,
    gateway: GatewayDep,
    job_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[InterviewKitSummary]:
    return build_interview_kit_service(db, gateway).list_for_user(current_user, job_id)


@router.get("/{kit_id}", response_model=InterviewKitRead)
def get_interview_kit(
    kit_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> InterviewKitRead:
    try:
        return build_interview_kit_service(db, gateway).get(current_user, kit_id)
    except InterviewKitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview kit not found"
        ) from exc
