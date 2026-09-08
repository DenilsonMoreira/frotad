from datetime import datetime, timezone


def is_period_active(start_at: datetime | None, end_at: datetime | None) -> bool:
    return start_at is not None and end_at is None


def period_duration_seconds(
    start_at: datetime,
    end_at: datetime | None,
    *,
    now: datetime | None = None,
) -> int:
    effective_end = end_at or now or datetime.now(timezone.utc)
    seconds = int((effective_end - start_at).total_seconds())
    return max(seconds, 0)
