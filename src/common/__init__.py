from datetime import datetime, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Normalize a datetime to UTC-aware, stripping any local tzinfo.

    If dt is None, returns None.
    If dt is naive (no tzinfo), assumes it's UTC and adds tzinfo.
    If dt is already aware, converts to UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utcnow() -> datetime:
    """Return current UTC time (timezone-aware).

    Replaces deprecated datetime.utcnow() which returns naive datetimes.
    """
    return datetime.now(timezone.utc)
