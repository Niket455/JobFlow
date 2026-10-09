from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.insights import DailyPlan, LearningRoadmap, SkillGapReport, WeeklyReview
from app.services.daily_plan_service import build_daily_plan_service
from app.services.learning_roadmap_service import build_learning_roadmap_service
from app.services.skill_gap_service import build_skill_gap_service
from app.services.weekly_review_service import build_weekly_review_service

router = APIRouter(tags=["insights"])


@router.get("/skill-gap", response_model=SkillGapReport)
def skill_gap(current_user: CurrentUser, db: DbSession) -> SkillGapReport:
    return build_skill_gap_service(db).report(current_user)


@router.get("/learning-roadmap", response_model=LearningRoadmap)
def learning_roadmap(current_user: CurrentUser, db: DbSession) -> LearningRoadmap:
    return build_learning_roadmap_service(db).roadmap(current_user)


@router.get("/daily-plan", response_model=DailyPlan)
def daily_plan(current_user: CurrentUser, db: DbSession) -> DailyPlan:
    return build_daily_plan_service(db).plan(current_user, now=datetime.now(UTC))


@router.get("/weekly-review", response_model=WeeklyReview)
def weekly_review(current_user: CurrentUser, db: DbSession) -> WeeklyReview:
    return build_weekly_review_service(db).review(current_user, now=datetime.now(UTC))
