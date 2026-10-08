import uuid
from dataclasses import dataclass

from app.schemas.insights import PlanItem

_INTERVIEW = 1
_FOLLOW_UP = 2
_REVIEW = 3
_LEARNING = 4


@dataclass(frozen=True)
class MatchCandidate:
    job_id: uuid.UUID
    title: str
    overall: float


@dataclass(frozen=True)
class ApplicationCandidate:
    application_id: uuid.UUID
    job_id: uuid.UUID
    title: str
    status: str
    days_since_update: int


def build_daily_plan(
    *,
    matches: list[MatchCandidate],
    applications: list[ApplicationCandidate],
    skills: list[str],
    follow_up_days: int,
    max_items: int,
) -> list[PlanItem]:
    """Prioritized, deterministic 'today' list.

    Order: interview prep, then follow-ups, then strong matches, then learning gaps.
    """
    ranked: list[tuple[int, float, PlanItem]] = []

    for application in applications:
        if application.status == "Interview":
            ranked.append(
                (
                    _INTERVIEW,
                    -float(application.days_since_update),
                    PlanItem(
                        kind="interview_prep",
                        title=f"Prep for interview: {application.title}",
                        detail="You have an interview in progress — practice your answers.",
                        priority=_INTERVIEW,
                        job_id=application.job_id,
                        application_id=application.application_id,
                    ),
                )
            )

    for application in applications:
        if application.status == "Applied" and application.days_since_update >= follow_up_days:
            ranked.append(
                (
                    _FOLLOW_UP,
                    -float(application.days_since_update),
                    PlanItem(
                        kind="follow_up",
                        title=f"Follow up on {application.title}",
                        detail=f"No update in {application.days_since_update} days.",
                        priority=_FOLLOW_UP,
                        job_id=application.job_id,
                        application_id=application.application_id,
                    ),
                )
            )

    for match in matches:
        ranked.append(
            (
                _REVIEW,
                -match.overall,
                PlanItem(
                    kind="review_job",
                    title=f"Review match: {match.title} ({match.overall:.1f}/10)",
                    detail="A strong match you haven't applied to yet.",
                    priority=_REVIEW,
                    job_id=match.job_id,
                ),
            )
        )

    for rank, skill in enumerate(skills):
        ranked.append(
            (
                _LEARNING,
                -float(rank),
                PlanItem(
                    kind="learning",
                    title=f"Learn {skill}",
                    detail="In demand across the jobs you're tracking.",
                    priority=_LEARNING,
                ),
            )
        )

    ranked.sort(key=lambda entry: (entry[0], entry[1]))
    return [item for _, _, item in ranked[:max_items]]
