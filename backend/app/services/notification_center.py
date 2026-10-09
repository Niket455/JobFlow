import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationDraft:
    kind: str
    title: str
    body: str
    dedupe_key: str
    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None


def derive_notifications(
    *,
    stale_applications: list[tuple[uuid.UUID, uuid.UUID, str, int]],
    interviews: list[tuple[uuid.UUID, uuid.UUID, str]],
    strong_matches: list[tuple[uuid.UUID, str, float]],
    pending_emails: list[tuple[uuid.UUID, str]],
    top_gap: tuple[str, float] | None,
) -> list[NotificationDraft]:
    """Deterministically derive the user's notifications from current state.

    Each draft carries a stable `dedupe_key` so a refresh never duplicates a notification.
    """
    drafts: list[NotificationDraft] = []

    for application_id, job_id, title, days in stale_applications:
        drafts.append(
            NotificationDraft(
                kind="follow_up",
                title=f"Follow up on {title}",
                body=f"No update in {days} days.",
                dedupe_key=f"follow_up:{application_id}",
                job_id=job_id,
                application_id=application_id,
            )
        )
    for application_id, job_id, title in interviews:
        drafts.append(
            NotificationDraft(
                kind="interview",
                title=f"Prepare for your interview: {title}",
                body="You have an interview in progress.",
                dedupe_key=f"interview:{application_id}",
                job_id=job_id,
                application_id=application_id,
            )
        )
    for job_id, title, overall in strong_matches:
        drafts.append(
            NotificationDraft(
                kind="match",
                title=f"Strong match: {title}",
                body=f"Scores {overall:.1f}/10.",
                dedupe_key=f"match:{job_id}",
                job_id=job_id,
            )
        )
    for message_id, subject in pending_emails:
        drafts.append(
            NotificationDraft(
                kind="email",
                title="Email to review",
                body=subject,
                dedupe_key=f"email:{message_id}",
            )
        )
    if top_gap is not None:
        skill, demand = top_gap
        drafts.append(
            NotificationDraft(
                kind="skill_gap",
                title=f"Skill gap: {skill}",
                body=f"{demand}% of your tracked jobs ask for {skill}.",
                dedupe_key=f"gap:{skill}",
            )
        )
    return drafts
