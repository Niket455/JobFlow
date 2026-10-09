import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.base import FetchError, RobotsDisallowedError
from app.api.deps import CurrentUser, DbSession, FetcherDep
from app.schemas.job import JobRead
from app.schemas.lead import LeadRead, LeadSummary
from app.services.lead_service import LeadNotFoundError, LeadService, build_lead_service

router = APIRouter(prefix="/leads", tags=["leads"])


def _leads(db: DbSession, fetcher: FetcherDep) -> LeadService:
    return build_lead_service(db, fetcher)


@router.get("", response_model=list[LeadSummary])
def list_leads(
    current_user: CurrentUser,
    db: DbSession,
    fetcher: FetcherDep,
    lead_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[LeadSummary]:
    return _leads(db, fetcher).list_for_user(
        current_user, status=lead_status, limit=limit, offset=offset
    )


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: uuid.UUID, current_user: CurrentUser, db: DbSession, fetcher: FetcherDep
) -> LeadRead:
    try:
        return _leads(db, fetcher).get(current_user, lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc


@router.post("/{lead_id}/capture", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def capture_lead(
    lead_id: uuid.UUID, current_user: CurrentUser, db: DbSession, fetcher: FetcherDep
) -> JobRead:
    try:
        return _leads(db, fetcher).capture(current_user, lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc
    except RobotsDisallowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="robots.txt disallows fetching this URL"
        ) from exc
    except FetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not fetch the lead URL"
        ) from exc


@router.post("/{lead_id}/dismiss", response_model=LeadRead)
def dismiss_lead(
    lead_id: uuid.UUID, current_user: CurrentUser, db: DbSession, fetcher: FetcherDep
) -> LeadRead:
    try:
        return _leads(db, fetcher).dismiss(current_user, lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc
