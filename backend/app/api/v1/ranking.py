from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.ranking import RankingRead, RankingStateRead
from app.services.ranking_service import build_ranking_service

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("", response_model=RankingRead)
def ranking(
    current_user: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=100)
) -> RankingRead:
    return build_ranking_service(db).ranking(current_user, limit=limit)


@router.post("/reset", response_model=RankingStateRead)
def reset_ranking(current_user: CurrentUser, db: DbSession) -> RankingStateRead:
    return build_ranking_service(db).reset(current_user, now=datetime.now(UTC))
