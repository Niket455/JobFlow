from datetime import UTC, datetime, timedelta

from app.services.application_status import StatusEvent, derive


def _at(minutes: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minutes)


def _event(event_type: str, minutes: int) -> StatusEvent:
    return StatusEvent(type=event_type, occurred_at=_at(minutes), created_at=_at(minutes))


def test_empty_log_is_saved() -> None:
    assert derive([]) == ("Saved", "Saved")


def test_latest_staged_event_wins() -> None:
    events = [_event("applied", 0), _event("interview", 10)]
    assert derive(events) == ("Interview", "Interview")


def test_notes_and_unknown_types_are_ignored() -> None:
    events = [_event("offer", 0), _event("note", 20), _event("weird", 30)]
    assert derive(events) == ("Offer", "Offer")


def test_terminal_statuses_map_to_closed_column() -> None:
    assert derive([_event("interview", 0), _event("rejected", 5)]) == ("Rejected", "Closed")
    assert derive([_event("withdrawn", 0)]) == ("Withdrawn", "Closed")


def test_event_type_is_case_insensitive() -> None:
    assert derive([_event("Interview", 0)]) == ("Interview", "Interview")
