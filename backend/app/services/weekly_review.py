from dataclasses import dataclass
from datetime import date

from app.services.application_status import STAGE_BY_EVENT

_ACTIVITY_STAGES = ("applied", "interview", "offer", "rejected", "withdrawn")


@dataclass(frozen=True)
class ActivityEvent:
    event_type: str
    occurred_on: date


def summarize_activity(events: list[ActivityEvent]) -> dict[str, int]:
    """Count staged application events by stage within a window (saved is not activity)."""
    counts = dict.fromkeys(_ACTIVITY_STAGES, 0)
    for event in events:
        stage = STAGE_BY_EVENT.get(event.event_type.strip().lower())
        key = stage.lower() if stage else None
        if key in counts:
            counts[key] += 1
    return counts
