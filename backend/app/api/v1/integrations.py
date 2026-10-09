import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, GatewayDep, InboxProviderFactoryDep
from app.integrations.base import InboxNotConfiguredError
from app.schemas.integrations import IntegrationCreate, IntegrationRead, SyncResult
from app.services.integration_service import (
    IntegrationNotConfiguredError,
    IntegrationNotFoundError,
    build_integration_service,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")


@router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
def connect_integration(
    payload: IntegrationCreate,
    current_user: CurrentUser,
    db: DbSession,
    provider_factory: InboxProviderFactoryDep,
) -> IntegrationRead:
    try:
        return build_integration_service(db, provider_factory).connect(current_user, payload)
    except IntegrationNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[IntegrationRead])
def list_integrations(
    current_user: CurrentUser, db: DbSession, provider_factory: InboxProviderFactoryDep
) -> list[IntegrationRead]:
    return build_integration_service(db, provider_factory).list_for_user(current_user)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_integration(
    integration_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    provider_factory: InboxProviderFactoryDep,
) -> None:
    try:
        build_integration_service(db, provider_factory).disconnect(current_user, integration_id)
    except IntegrationNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{integration_id}/sync", response_model=SyncResult)
async def sync_integration(
    integration_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    provider_factory: InboxProviderFactoryDep,
    gateway: GatewayDep,
) -> SyncResult:
    try:
        return await build_integration_service(db, provider_factory).sync(
            current_user, integration_id, gateway
        )
    except IntegrationNotFoundError as exc:
        raise _not_found() from exc
    except InboxNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
