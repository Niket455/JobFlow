import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.adapters.base import FetchError
from app.adapters.discovery import QuotaExceededError
from app.api.deps import CurrentUser, DbSession, DiscoveryRuntimeDep
from app.schemas.lead import DiscoverRunResult, DiscoverySourceCreate, DiscoverySourceRead
from app.services.discovery_service import (
    DiscoveryKindError,
    DiscoveryService,
    DiscoverySourceConflictError,
    DiscoverySourceNotFoundError,
    build_discovery_service,
)

router = APIRouter(prefix="/discovery-sources", tags=["discovery-sources"])


def _discovery(db: DbSession, runtime: DiscoveryRuntimeDep) -> DiscoveryService:
    return build_discovery_service(db, source_factory=runtime.source)


@router.post("", response_model=DiscoverySourceRead, status_code=status.HTTP_201_CREATED)
def create_discovery_source(
    payload: DiscoverySourceCreate,
    current_user: CurrentUser,
    db: DbSession,
    runtime: DiscoveryRuntimeDep,
) -> DiscoverySourceRead:
    try:
        return _discovery(db, runtime).create_source(
            current_user, kind=payload.kind, label=payload.label, target=payload.target
        )
    except DiscoveryKindError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except DiscoverySourceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Discovery source already exists"
        ) from exc


@router.get("", response_model=list[DiscoverySourceRead])
def list_discovery_sources(
    current_user: CurrentUser, db: DbSession, runtime: DiscoveryRuntimeDep
) -> list[DiscoverySourceRead]:
    return _discovery(db, runtime).list_sources(current_user)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discovery_source(
    source_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    runtime: DiscoveryRuntimeDep,
) -> None:
    try:
        _discovery(db, runtime).delete_source(current_user, source_id)
    except DiscoverySourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discovery source not found"
        ) from exc


@router.post("/{source_id}/run", response_model=DiscoverRunResult)
def run_discovery_source(
    source_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    runtime: DiscoveryRuntimeDep,
) -> DiscoverRunResult:
    try:
        return _discovery(db, runtime).run_source(current_user, source_id, now=datetime.now(UTC))
    except DiscoverySourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discovery source not found"
        ) from exc
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Google PSE daily quota exhausted",
        ) from exc
    except FetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not run discovery source"
        ) from exc
