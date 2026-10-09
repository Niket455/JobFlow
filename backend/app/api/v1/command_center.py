from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.command_center import CommandCenter
from app.services.command_center_service import build_command_center_service

router = APIRouter(prefix="/command-center", tags=["command-center"])


@router.get("", response_model=CommandCenter)
def command_center(current_user: CurrentUser, db: DbSession) -> CommandCenter:
    return build_command_center_service(db).build(current_user, now=datetime.now(UTC))
