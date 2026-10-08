from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.analytics import FunnelRead, RatesRead, RejectionsRead
from app.services.analytics_service import (
    REJECTION_DIMENSIONS,
    build_analytics_service,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/funnel", response_model=FunnelRead)
def funnel(current_user: CurrentUser, db: DbSession) -> FunnelRead:
    return build_analytics_service(db).funnel(current_user)


@router.get("/rates", response_model=RatesRead)
def rates(current_user: CurrentUser, db: DbSession) -> RatesRead:
    return build_analytics_service(db).rates(current_user)


@router.get("/rejections", response_model=RejectionsRead)
def rejections(
    current_user: CurrentUser, db: DbSession, by: str = Query("source")
) -> RejectionsRead:
    if by not in REJECTION_DIMENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"by must be one of {', '.join(REJECTION_DIMENSIONS)}",
        )
    return build_analytics_service(db).rejections(current_user, by)
