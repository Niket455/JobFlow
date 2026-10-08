from datetime import UTC, datetime

from app.services.alert_schedule import in_quiet_hours, next_run_at


def test_open_window_is_never_quiet() -> None:
    assert in_quiet_hours(3, None, 7) is False
    assert in_quiet_hours(3, 22, None) is False
    assert in_quiet_hours(3, None, None) is False


def test_equal_bounds_is_never_quiet() -> None:
    assert in_quiet_hours(22, 22, 22) is False


def test_simple_window() -> None:
    assert in_quiet_hours(22, 22, 23) is True
    assert in_quiet_hours(23, 22, 23) is False
    assert in_quiet_hours(12, 22, 23) is False


def test_wrapping_window() -> None:
    assert in_quiet_hours(23, 22, 7) is True
    assert in_quiet_hours(3, 22, 7) is True
    assert in_quiet_hours(7, 22, 7) is False
    assert in_quiet_hours(12, 22, 7) is False


def test_next_run_at_cadence() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert next_run_at(now, "daily") == datetime(2026, 1, 2, tzinfo=UTC)
    assert next_run_at(now, "weekly") == datetime(2026, 1, 8, tzinfo=UTC)
