import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, GatewayDep
from app.schemas.interview import (
    PracticeRequest,
    PracticeSessionRead,
    PracticeSessionSummary,
)
from app.services.job_service import JobNotFoundError
from app.services.practice_service import (
    PracticeSessionNotFoundError,
    build_practice_service,
)

router = APIRouter(prefix="/practice-sessions", tags=["practice"])


@router.post("", response_model=PracticeSessionRead, status_code=status.HTTP_201_CREATED)
async def evaluate_answer(
    payload: PracticeRequest, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> PracticeSessionRead:
    try:
        return await build_practice_service(db, gateway).evaluate(current_user, payload)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("", response_model=list[PracticeSessionSummary])
def list_practice_sessions(
    current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> list[PracticeSessionSummary]:
    return build_practice_service(db, gateway).list_for_user(current_user)


@router.get("/{session_id}", response_model=PracticeSessionRead)
def get_practice_session(
    session_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> PracticeSessionRead:
    try:
        return build_practice_service(db, gateway).get(current_user, session_id)
    except PracticeSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found"
        ) from exc
