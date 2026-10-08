from datetime import datetime, timedelta

_FREQUENCY_DELTAS = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def in_quiet_hours(now_hour: int, start: int | None, end: int | None) -> bool:
    """True when `now_hour` falls in the [start, end) window (wrapping past midnight)."""
    if start is None or end is None or start == end:
        return False
    if start < end:
        return start <= now_hour < end
    return now_hour >= start or now_hour < end


def next_run_at(now: datetime, frequency: str) -> datetime:
    return now + _FREQUENCY_DELTAS.get(frequency, timedelta(days=1))
