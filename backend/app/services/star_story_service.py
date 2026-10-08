import json
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.star_story import StarStory
from app.models.user import User
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.star_story_repository import StarStoryRepository
from app.repositories.user_repository import UserRepository
from app.schemas.interview import (
    StarStoryCreate,
    StarStoryDraft,
    StarStoryDraftRequest,
    StarStoryRead,
    StarStorySummary,
    StarStoryUpdate,
)
from app.schemas.profile import ProfileData
from app.services.encryption import ensure_data_key
from app.services.resume_service import ResumeNotFoundError
from app.services.tailor_grounding import get_value, path_exists

_CONTENT_KEYS = ("situation", "task", "action", "result")
_LINK_KEYS = ("resume_version_id", "resume_item_path")


class StarStoryNotFoundError(Exception):
    pass


class StarStoryLinkError(Exception):
    pass


class StarStoryService:
    """CRUD for reusable STAR stories, each optionally linked to a resume item."""

    def __init__(
        self,
        resumes: ResumeVersionRepository,
        stories: StarStoryRepository,
        users: UserRepository,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.resumes = resumes
        self.stories = stories
        self.users = users
        self.gateway = gateway
        self.model = model

    def create(self, user: User, payload: StarStoryCreate) -> StarStoryRead:
        data_key = ensure_data_key(user, self.users)
        self._validate_link(user, payload.resume_version_id, payload.resume_item_path, data_key)
        story = self.stories.create(
            user_id=user.id,
            title=payload.title,
            skills=payload.skills,
            resume_version_id=payload.resume_version_id,
            resume_item_path=payload.resume_item_path,
            content_enc=encrypt_text(
                data_key,
                json.dumps({key: getattr(payload, key) for key in _CONTENT_KEYS}),
            ),
        )
        return _to_read(story, data_key)

    def update(self, user: User, story_id: uuid.UUID, payload: StarStoryUpdate) -> StarStoryRead:
        story = self._get(user, story_id)
        data_key = ensure_data_key(user, self.users)
        updates = payload.model_dump(exclude_unset=True)
        if any(key in updates for key in _LINK_KEYS):
            self._validate_link(
                user,
                updates.get("resume_version_id"),
                updates.get("resume_item_path"),
                data_key,
            )
        for key in ("title", "skills", *_LINK_KEYS):
            if key in updates:
                setattr(story, key, updates[key])
        if any(key in updates for key in _CONTENT_KEYS):
            content = _content(story, data_key)
            for key in _CONTENT_KEYS:
                if key in updates:
                    content[key] = updates[key] or ""
            story.content_enc = encrypt_text(data_key, json.dumps(content))
        self.stories.save(story)
        return _to_read(story, data_key)

    def get(self, user: User, story_id: uuid.UUID) -> StarStoryRead:
        return _to_read(self._get(user, story_id), ensure_data_key(user, self.users))

    def list_for_user(self, user: User) -> list[StarStorySummary]:
        return [
            StarStorySummary.model_validate(story) for story in self.stories.list_for_user(user.id)
        ]

    def delete(self, user: User, story_id: uuid.UUID) -> None:
        self.stories.delete(self._get(user, story_id))

    async def draft(self, user: User, payload: StarStoryDraftRequest) -> StarStoryDraft:
        record = self.resumes.get_for_user(user.id, payload.resume_version_id)
        if record is None or record.parsed_enc is None:
            raise ResumeNotFoundError
        data_key = ensure_data_key(user, self.users)
        profile = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        item = get_value(profile.model_dump(), payload.path)
        if item is None:
            raise StarStoryLinkError(f"Unknown resume path: {payload.path}")
        prompt = load_prompt("star_story").format(resume_item=json.dumps(item))
        return await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)], model=self.model, schema=StarStoryDraft
        )

    def _get(self, user: User, story_id: uuid.UUID) -> StarStory:
        story = self.stories.get_for_user(user.id, story_id)
        if story is None:
            raise StarStoryNotFoundError
        return story

    def _validate_link(
        self,
        user: User,
        resume_version_id: uuid.UUID | None,
        path: str | None,
        data_key: str,
    ) -> None:
        if resume_version_id is None:
            if path is not None:
                raise StarStoryLinkError("resume_item_path requires resume_version_id")
            return
        record = self.resumes.get_for_user(user.id, resume_version_id)
        if record is None or record.parsed_enc is None:
            raise ResumeNotFoundError
        if path is None:
            return
        profile = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        if not path_exists(profile.model_dump(), path):
            raise StarStoryLinkError(f"Unknown resume path: {path}")


def build_star_story_service(db: Session, gateway: LLMGateway) -> StarStoryService:
    return StarStoryService(
        ResumeVersionRepository(db),
        StarStoryRepository(db),
        UserRepository(db),
        gateway,
        model=settings.llm_strong_model,
    )


def _content(story: StarStory, data_key: str) -> dict[str, str]:
    parsed: dict[str, str] = json.loads(decrypt_text(data_key, story.content_enc))
    return parsed


def _to_read(story: StarStory, data_key: str) -> StarStoryRead:
    content = _content(story, data_key)
    return StarStoryRead(
        id=story.id,
        title=story.title,
        situation=content.get("situation", ""),
        task=content.get("task", ""),
        action=content.get("action", ""),
        result=content.get("result", ""),
        skills=story.skills,
        resume_version_id=story.resume_version_id,
        resume_item_path=story.resume_item_path,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )
