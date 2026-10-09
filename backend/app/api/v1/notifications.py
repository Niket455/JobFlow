import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, EmailSenderDep
from app.schemas.notification import TestEmailResult
from app.schemas.notifications import NotificationRead, RefreshResult, UnreadCount
from app.services.notification_center_service import (
    NotificationNotFoundError,
    build_notification_center_service,
)
from app.services.notification_service import EmailDisabledError, NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    unread: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
) -> list[NotificationRead]:
    return build_notification_center_service(db).list_for_user(
        current_user, unread_only=unread, limit=limit
    )


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(current_user: CurrentUser, db: DbSession) -> UnreadCount:
    return UnreadCount(unread=build_notification_center_service(db).unread_count(current_user))


@router.post("/refresh", response_model=RefreshResult)
def refresh_notifications(current_user: CurrentUser, db: DbSession) -> RefreshResult:
    return build_notification_center_service(db).refresh(current_user, now=datetime.now(UTC))


@router.post("/read-all", response_model=UnreadCount)
def read_all(current_user: CurrentUser, db: DbSession) -> UnreadCount:
    service = build_notification_center_service(db)
    service.mark_all_read(current_user, now=datetime.now(UTC))
    return UnreadCount(unread=service.unread_count(current_user))


@router.post("/test", response_model=TestEmailResult)
def send_test_email(current_user: CurrentUser, sender: EmailSenderDep) -> TestEmailResult:
    try:
        message = NotificationService(sender).send_test_email(current_user)
    except EmailDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email is disabled"
        ) from exc
    return TestEmailResult(sent=True, to=message.to, provider=sender.provider)


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> NotificationRead:
    try:
        return build_notification_center_service(db).mark_read(
            current_user, notification_id, now=datetime.now(UTC)
        )
    except NotificationNotFoundError as exc:
        raise _not_found() from exc


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    try:
        build_notification_center_service(db).delete(current_user, notification_id)
    except NotificationNotFoundError as exc:
        raise _not_found() from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
