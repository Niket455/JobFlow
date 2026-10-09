import uuid

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def list_active(self, *, limit: int) -> list[User]:
        return list(
            self.db.scalars(
                select(User).where(User.is_active.is_(True)).order_by(User.created_at).limit(limit)
            )
        )

    def create(self, email: str, password_hash: str, wrapped_data_key: str) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            wrapped_data_key=wrapped_data_key,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
