import uuid
from typing import Any

from sqlalchemy import select

from app.models.star_story import StarStory
from app.repositories.base import BaseRepository


class StarStoryRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, story_id: uuid.UUID) -> StarStory | None:
        return self.db.scalar(
            select(StarStory).where(StarStory.user_id == user_id, StarStory.id == story_id)
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[StarStory]:
        return list(
            self.db.scalars(
                select(StarStory)
                .where(StarStory.user_id == user_id)
                .order_by(StarStory.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> StarStory:
        story = StarStory(**fields)
        self.db.add(story)
        self.db.commit()
        self.db.refresh(story)
        return story

    def save(self, story: StarStory) -> None:
        self.db.commit()
        self.db.refresh(story)

    def delete(self, story: StarStory) -> None:
        self.db.delete(story)
        self.db.commit()
