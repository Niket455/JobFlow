from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.crm import FollowUpList
from app.services.follow_up_service import build_follow_up_service

router = APIRouter(prefix="/follow-ups", tags=["crm"])


@router.get("", response_model=FollowUpList)
def list_follow_ups(current_user: CurrentUser, db: DbSession) -> FollowUpList:
    return build_follow_up_service(db).list_for_user(current_user, now=datetime.now(UTC))
