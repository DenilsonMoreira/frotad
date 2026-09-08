from datetime import datetime, timedelta, timezone

from frotad.services.periods import is_period_active, period_duration_seconds


def test_period_is_active_when_started_and_not_finished() -> None:
    start = datetime.now(timezone.utc)
    assert is_period_active(start, None) is True


def test_closed_period_is_not_active() -> None:
    start = datetime.now(timezone.utc)
    assert is_period_active(start, start + timedelta(minutes=1)) is False


def test_duration_uses_end_when_closed() -> None:
    start = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=42)
    assert period_duration_seconds(start, end) == 42 * 60
