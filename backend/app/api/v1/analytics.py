from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.analytics import (
    AbTestRead,
    FunnelRead,
    RatesRead,
    RejectionReasonsRead,
    RejectionsRead,
)
from app.services.analytics_service import BREAKDOWN_DIMENSIONS, build_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _check_dimension(by: str | None) -> None:
    if by is not None and by not in BREAKDOWN_DIMENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"by must be one of {', '.join(BREAKDOWN_DIMENSIONS)}",
        )


@router.get("/funnel", response_model=FunnelRead)
def funnel(
    current_user: CurrentUser,
    db: DbSession,
    by: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> FunnelRead:
    _check_dimension(by)
    return build_analytics_service(db).funnel(current_user, by=by, since=since, until=until)


@router.get("/rates", response_model=RatesRead)
def rates(
    current_user: CurrentUser,
    db: DbSession,
    by: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> RatesRead:
    _check_dimension(by)
    return build_analytics_service(db).rates(current_user, by=by, since=since, until=until)


@router.get("/rejections", response_model=RejectionsRead)
def rejections(
    current_user: CurrentUser,
    db: DbSession,
    by: str = Query("source"),
    since: datetime | None = None,
    until: datetime | None = None,
) -> RejectionsRead:
    _check_dimension(by)
    return build_analytics_service(db).rejections(current_user, by, since=since, until=until)


@router.get("/rejection-reasons", response_model=RejectionReasonsRead)
def rejection_reasons(current_user: CurrentUser, db: DbSession) -> RejectionReasonsRead:
    return build_analytics_service(db).rejection_reasons(current_user)


@router.get("/ab-test", response_model=AbTestRead)
def ab_test(
    current_user: CurrentUser, db: DbSession, by: str = Query("resume_version")
) -> AbTestRead:
    _check_dimension(by)
    return build_analytics_service(db).ab_test(current_user, by)
