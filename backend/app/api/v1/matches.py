import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.match import MatchRead, MatchSummary
from app.services.match_service import MatchNotFoundError, build_match_service

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/recompute")
def recompute_matches(current_user: CurrentUser, db: DbSession) -> dict[str, int]:
    return {"recomputed": build_match_service(db).recompute(current_user)}


@router.get("", response_model=list[MatchSummary])
def list_matches(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[MatchSummary]:
    return build_match_service(db).list_for_user(current_user, limit=limit, offset=offset)


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> MatchRead:
    try:
        return build_match_service(db).get(current_user, match_id)
    except MatchNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        ) from exc
