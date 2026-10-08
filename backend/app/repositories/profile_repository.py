import uuid

from sqlalchemy import select

from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID) -> Profile | None:
        return self.db.scalar(select(Profile).where(Profile.user_id == user_id))

    def upsert(self, user_id: uuid.UUID, data_enc: str) -> Profile:
        profile = self.get_for_user(user_id)
        if profile is None:
            profile = Profile(user_id=user_id, data_enc=data_enc)
            self.db.add(profile)
        else:
            profile.data_enc = data_enc
        self.db.commit()
        self.db.refresh(profile)
        return profile
