import uuid

from app.services.notification_center import derive_notifications

APP = uuid.uuid4()
JOB = uuid.uuid4()
MSG = uuid.uuid4()


def test_derive_all_triggers() -> None:
    drafts = derive_notifications(
        stale_applications=[(APP, JOB, "Data Engineer", 10)],
        interviews=[(APP, JOB, "Data Engineer")],
        strong_matches=[(JOB, "Data Engineer", 9.0)],
        pending_emails=[(MSG, "Interview invitation")],
        top_gap=("Kubernetes", 66.7),
    )

    assert {draft.kind for draft in drafts} == {
        "follow_up",
        "interview",
        "match",
        "email",
        "skill_gap",
    }
    assert {draft.dedupe_key for draft in drafts} == {
        f"follow_up:{APP}",
        f"interview:{APP}",
        f"match:{JOB}",
        f"email:{MSG}",
        "gap:Kubernetes",
    }


def test_derive_empty() -> None:
    drafts = derive_notifications(
        stale_applications=[],
        interviews=[],
        strong_matches=[],
        pending_emails=[],
        top_gap=None,
    )
    assert drafts == []
