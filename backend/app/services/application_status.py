from dataclasses import dataclass
from datetime import datetime

STAGE_BY_EVENT: dict[str, str] = {
    "saved": "Saved",
    "applied": "Applied",
    "screening": "Interview",
    "interview": "Interview",
    "assessment": "Interview",
    "offer": "Offer",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}

STATUSES = ("Saved", "Applied", "Interview", "Offer", "Rejected", "Withdrawn")
KANBAN_COLUMNS = ("Saved", "Applied", "Interview", "Offer", "Closed")
_CLOSED = {"Rejected", "Withdrawn"}


@dataclass(frozen=True)
class StatusEvent:
    type: str
    occurred_at: datetime
    created_at: datetime


def stage_for(event_type: str) -> str | None:
    return STAGE_BY_EVENT.get(event_type.strip().lower())


def derive(events: list[StatusEvent]) -> tuple[str, str]:
    """Derive (status, kanban) from the event log. Latest staged event wins; notes are ignored."""
    ordered = sorted(events, key=lambda event: (event.occurred_at, event.created_at), reverse=True)
    status = "Saved"
    for event in ordered:
        stage = stage_for(event.type)
        if stage is not None:
            status = stage
            break
    return status, "Closed" if status in _CLOSED else status
