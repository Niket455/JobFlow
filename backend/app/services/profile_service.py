from app.core.crypto import decrypt_text, encrypt_text
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import ProfileData, ProfileRead
from app.services.encryption import ensure_data_key


class ProfileService:
    def __init__(self, profiles: ProfileRepository, users: UserRepository) -> None:
        self.profiles = profiles
        self.users = users

    def get(self, user: User) -> ProfileRead:
        record = self.profiles.get_for_user(user.id)
        if record is None:
            return ProfileRead()
        data_key = ensure_data_key(user, self.users)
        data = ProfileData.model_validate_json(decrypt_text(data_key, record.data_enc))
        return ProfileRead(**data.model_dump(), updated_at=record.updated_at)

    def update(self, user: User, payload: ProfileData) -> ProfileRead:
        data_key = ensure_data_key(user, self.users)
        record = self.profiles.upsert(user.id, encrypt_text(data_key, payload.model_dump_json()))
        return ProfileRead(**payload.model_dump(), updated_at=record.updated_at)
