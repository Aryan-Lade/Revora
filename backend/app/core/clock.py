from datetime import datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def to_ist(value: datetime) -> datetime:
    return aware(value).astimezone(IST)


def in_quiet_hours(value: datetime, start_hour: int, end_hour: int) -> bool:
    hour = to_ist(value).hour
    return hour >= start_hour or hour < end_hour


def next_allowed_window(value: datetime, start_hour: int, end_hour: int) -> datetime:
    local = to_ist(value)
    if not in_quiet_hours(local, start_hour, end_hour):
        return aware(value)
    target = local.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    if local.hour >= start_hour:
        target += timedelta(days=1)
    return target.astimezone(timezone.utc)


def hours_between(later: datetime, earlier: datetime) -> float:
    return (aware(later) - aware(earlier)).total_seconds() / 3600


def start_of_ist_day(value: datetime) -> datetime:
    local = to_ist(value)
    return datetime.combine(local.date(), time.min, tzinfo=IST).astimezone(timezone.utc)
