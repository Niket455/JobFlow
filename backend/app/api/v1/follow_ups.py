import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.crm import FollowUpList, FollowUpSnoozeRequest, FollowUpStateRead
from app.services.follow_up_service import FollowUpNotFoundError, build_follow_up_service

router = APIRouter(prefix="/follow-ups", tags=["crm"])


@router.get("", response_model=FollowUpList)
def list_follow_ups(current_user: CurrentUser, db: DbSession) -> FollowUpList:
    return build_follow_up_service(db).list_for_user(current_user, now=datetime.now(UTC))


@router.post("/{application_id}/snooze", response_model=FollowUpStateRead)
def snooze_follow_up(
    application_id: uuid.UUID,
    payload: FollowUpSnoozeRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> FollowUpStateRead:
    try:
        return build_follow_up_service(db).snooze(
            current_user, application_id, days=payload.days, now=datetime.now(UTC)
        )
    except FollowUpNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        ) from exc


@router.post("/{application_id}/done", response_model=FollowUpStateRead)
def done_follow_up(
    application_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> FollowUpStateRead:
    try:
        return build_follow_up_service(db).mark_done(
            current_user, application_id, now=datetime.now(UTC)
        )
    except FollowUpNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        ) from exc
