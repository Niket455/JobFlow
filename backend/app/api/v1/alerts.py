import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, EmailSenderDep
from app.schemas.alert import (
    AlertData,
    AlertItem,
    AlertRead,
    AlertRunRead,
    AlertSummary,
    UnsubscribeResult,
)
from app.services.alert_service import AlertNotFoundError, build_alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertData, current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> AlertRead:
    return build_alert_service(db, sender).create(current_user.id, payload)


@router.get("", response_model=list[AlertSummary])
def list_alerts(
    current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> list[AlertSummary]:
    return build_alert_service(db, sender).list_for_user(current_user.id)


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(
    alert_id: uuid.UUID, current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> AlertRead:
    try:
        return build_alert_service(db, sender).get(current_user.id, alert_id)
    except AlertNotFoundError as exc:
        raise _not_found() from exc


@router.put("/{alert_id}", response_model=AlertRead)
def update_alert(
    alert_id: uuid.UUID,
    payload: AlertData,
    current_user: CurrentUser,
    db: DbSession,
    sender: EmailSenderDep,
) -> AlertRead:
    try:
        return build_alert_service(db, sender).update(current_user.id, alert_id, payload)
    except AlertNotFoundError as exc:
        raise _not_found() from exc


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: uuid.UUID, current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> None:
    try:
        build_alert_service(db, sender).delete(current_user.id, alert_id)
    except AlertNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{alert_id}/preview", response_model=list[AlertItem])
def preview_alert(
    alert_id: uuid.UUID, current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> list[AlertItem]:
    try:
        return build_alert_service(db, sender).preview(current_user.id, alert_id)
    except AlertNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{alert_id}/run", response_model=AlertRunRead)
def run_alert(
    alert_id: uuid.UUID, current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> AlertRunRead:
    try:
        return build_alert_service(db, sender).run_now(current_user.id, alert_id)
    except AlertNotFoundError as exc:
        raise _not_found() from exc


@router.get("/{alert_id}/runs", response_model=list[AlertRunRead])
def list_alert_runs(
    alert_id: uuid.UUID, current_user: CurrentUser, db: DbSession, sender: EmailSenderDep
) -> list[AlertRunRead]:
    try:
        return build_alert_service(db, sender).list_runs(current_user.id, alert_id)
    except AlertNotFoundError as exc:
        raise _not_found() from exc


@router.post("/unsubscribe/{token}", response_model=UnsubscribeResult)
def unsubscribe(token: str, db: DbSession, sender: EmailSenderDep) -> UnsubscribeResult:
    return UnsubscribeResult(unsubscribed=build_alert_service(db, sender).unsubscribe(token))
