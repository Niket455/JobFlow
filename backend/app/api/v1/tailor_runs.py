import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, GatewayDep, StorageDep
from app.schemas.resume import ResumeVersionRead
from app.schemas.tailor import TailorDecisions, TailorRunRead
from app.services.resume_service import ResumeNotFoundError
from app.services.tailor_service import (
    TailorDecisionError,
    TailorRunAlreadyAppliedError,
    TailorRunNotFoundError,
    build_tailor_service,
)

router = APIRouter(prefix="/tailor-runs", tags=["tailor-runs"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailor run not found")


@router.get("/{run_id}", response_model=TailorRunRead)
def get_tailor_run(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
) -> TailorRunRead:
    try:
        return build_tailor_service(db, storage, gateway).get_run(current_user, run_id)
    except TailorRunNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{run_id}/decisions", response_model=TailorRunRead)
def set_tailor_decisions(
    run_id: uuid.UUID,
    payload: TailorDecisions,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
) -> TailorRunRead:
    try:
        return build_tailor_service(db, storage, gateway).set_decisions(
            current_user, run_id, payload
        )
    except TailorRunNotFoundError as exc:
        raise _not_found() from exc
    except TailorDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{run_id}/apply", response_model=ResumeVersionRead)
def apply_tailor_run(
    run_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    gateway: GatewayDep,
) -> ResumeVersionRead:
    try:
        return build_tailor_service(db, storage, gateway).apply(current_user, run_id)
    except (TailorRunNotFoundError, ResumeNotFoundError) as exc:
        raise _not_found() from exc
    except TailorRunAlreadyAppliedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tailor run already applied"
        ) from exc
