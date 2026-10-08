import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, GatewayDep
from app.schemas.interview import (
    StarStoryCreate,
    StarStoryDraft,
    StarStoryDraftRequest,
    StarStoryRead,
    StarStorySummary,
    StarStoryUpdate,
)
from app.services.resume_service import ResumeNotFoundError
from app.services.star_story_service import (
    StarStoryLinkError,
    StarStoryNotFoundError,
    build_star_story_service,
)

router = APIRouter(prefix="/star-stories", tags=["star-stories"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Star story not found")


@router.post("", response_model=StarStoryRead, status_code=status.HTTP_201_CREATED)
def create_star_story(
    payload: StarStoryCreate, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> StarStoryRead:
    try:
        return build_star_story_service(db, gateway).create(current_user, payload)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except StarStoryLinkError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[StarStorySummary])
def list_star_stories(
    current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> list[StarStorySummary]:
    return build_star_story_service(db, gateway).list_for_user(current_user)


@router.post("/draft", response_model=StarStoryDraft)
async def draft_star_story(
    payload: StarStoryDraftRequest, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> StarStoryDraft:
    try:
        return await build_star_story_service(db, gateway).draft(current_user, payload)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except StarStoryLinkError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{story_id}", response_model=StarStoryRead)
def get_star_story(
    story_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> StarStoryRead:
    try:
        return build_star_story_service(db, gateway).get(current_user, story_id)
    except StarStoryNotFoundError as exc:
        raise _not_found() from exc


@router.put("/{story_id}", response_model=StarStoryRead)
def update_star_story(
    story_id: uuid.UUID,
    payload: StarStoryUpdate,
    current_user: CurrentUser,
    db: DbSession,
    gateway: GatewayDep,
) -> StarStoryRead:
    try:
        return build_star_story_service(db, gateway).update(current_user, story_id, payload)
    except StarStoryNotFoundError as exc:
        raise _not_found() from exc
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found"
        ) from exc
    except StarStoryLinkError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_star_story(
    story_id: uuid.UUID, current_user: CurrentUser, db: DbSession, gateway: GatewayDep
) -> None:
    try:
        build_star_story_service(db, gateway).delete(current_user, story_id)
    except StarStoryNotFoundError as exc:
        raise _not_found() from exc
