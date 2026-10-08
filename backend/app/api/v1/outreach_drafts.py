import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, GatewayDep
from app.schemas.crm import OutreachDraftRead, OutreachDraftSummary, OutreachRequest
from app.services.contact_service import ContactNotFoundError
from app.services.job_service import JobNotFoundError
from app.services.outreach_service import (
    OutreachDraftNotFoundError,
    build_outreach_service,
)

router = APIRouter(prefix="/outreach-drafts", tags=["outreach"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outreach draft not found")


@router.post("", response_model=OutreachDraftRead, status_code=status.HTTP_201_CREATED)
async def generate_outreach(
    payload: OutreachRequest, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> OutreachDraftRead:
    try:
        return await build_outreach_service(db, gateway).generate(current_user, payload)
    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        ) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc


@router.get("", response_model=list[OutreachDraftSummary])
def list_outreach_drafts(
    current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> list[OutreachDraftSummary]:
    return build_outreach_service(db, gateway).list_for_user(current_user)


@router.get("/{draft_id}", response_model=OutreachDraftRead)
def get_outreach_draft(
    draft_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> OutreachDraftRead:
    try:
        return build_outreach_service(db, gateway).get(current_user, draft_id)
    except OutreachDraftNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{draft_id}/send", response_model=OutreachDraftRead)
def send_outreach_draft(
    draft_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> OutreachDraftRead:
    try:
        return build_outreach_service(db, gateway).mark_sent(current_user, draft_id)
    except OutreachDraftNotFoundError as exc:
        raise _not_found() from exc
