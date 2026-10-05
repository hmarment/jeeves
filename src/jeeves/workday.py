from datetime import date, datetime, timedelta

from jeeves.model import CalendarEvent, Preferences

Interval = tuple[datetime, datetime]


def is_working_day(day: date, events: list[CalendarEvent]) -> bool:
    if day.weekday() >= 5:
        return False
    return not any(
        event.all_day
        and event.out_of_office
        and event.start.date() <= day < event.end.date()
        for event in events
    )


def working_day_on_or_after(day: date, events: list[CalendarEvent]) -> date:
    while not is_working_day(day, events):
        day += timedelta(days=1)
    return day


def working_days_ahead(
    start: date, count: int, events: list[CalendarEvent]
) -> list[date]:
    days, candidate = [], start
    while len(days) < count:
        if is_working_day(candidate, events):
            days.append(candidate)
        candidate += timedelta(days=1)
    return days


def free_intervals(
    now: datetime, events: list[CalendarEvent], prefs: Preferences
) -> list[Interval]:
    day, tz = now.date(), now.tzinfo
    window_start = max(datetime.combine(day, prefs.work_start, tz), now)
    window_end = datetime.combine(day, prefs.work_end, tz)
    buffer = timedelta(minutes=prefs.meeting_buffer_minutes)
    busy = sorted(
        (event.start - buffer, event.end + buffer)
        for event in events
        if not event.all_day
        and not event.pa_created
        and event.end > window_start
        and event.start < window_end
    )
    free, cursor = [], window_start
    for start, end in busy:
        if start > cursor:
            free.append((cursor, min(start, window_end)))
        cursor = max(cursor, end)
    if cursor < window_end:
        free.append((cursor, window_end))
    minimum = timedelta(minutes=prefs.min_block_minutes)
    return [(start, end) for start, end in free if end - start >= minimum]


def focus_minutes(intervals: list[Interval]) -> int:
    return sum(int((end - start).total_seconds() // 60) for start, end in intervals)
