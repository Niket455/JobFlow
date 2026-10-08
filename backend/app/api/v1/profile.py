from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import ProfileData, ProfileRead
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


def _service(db: DbSession) -> ProfileService:
    return ProfileService(ProfileRepository(db), UserRepository(db))


@router.get("", response_model=ProfileRead)
def get_profile(current_user: CurrentUser, db: DbSession) -> ProfileRead:
    return _service(db).get(current_user)


@router.put("", response_model=ProfileRead)
def update_profile(payload: ProfileData, current_user: CurrentUser, db: DbSession) -> ProfileRead:
    return _service(db).update(current_user, payload)
