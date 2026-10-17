from datetime import UTC, date, datetime, time, timedelta

from jeeves.model import BERLIN, Frozen, Preferences
from jeeves.snapshot import _event_type, event_from_google
from jeeves.workday import is_working_day


class WeekScore(Frozen):
    week_start: date
    meeting_hours: float | None
    working_days: int


def is_meeting(raw: dict, prefs: Preferences) -> bool:
    event = event_from_google(raw, prefs)
    if event is None or event.all_day or event.out_of_office or event.pa_created:
        return False
    if _event_type(raw) == "focustime":
        return False
    return any(
        not attendee.get("self") and not attendee.get("resource")
        for attendee in raw.get("attendees") or []
    )


def score_week(
    raw_events: list[dict], week_start: date, prefs: Preferences
) -> WeekScore:
    if week_start.weekday() != 0:
        raise ValueError(f"week start {week_start} is not a Monday")
    window_start = datetime.combine(week_start, time.min, BERLIN).astimezone(UTC)
    window_end = datetime.combine(
        week_start + timedelta(days=7), time.min, BERLIN
    ).astimezone(UTC)
    events = [e for raw in raw_events if (e := event_from_google(raw, prefs))]
    working_days = sum(
        is_working_day(week_start + timedelta(days=offset), events)
        for offset in range(5)
    )
    if working_days == 0:
        return WeekScore(week_start=week_start, meeting_hours=None, working_days=0)
    intervals = sorted(
        (
            max(event.start.astimezone(UTC), window_start),
            min(event.end.astimezone(UTC), window_end),
        )
        for raw in raw_events
        if is_meeting(raw, prefs)
        and (event := event_from_google(raw, prefs))
        and event.end > window_start
        and event.start < window_end
    )
    total, cursor = timedelta(), window_start
    for start, end in intervals:
        start = max(start, cursor)
        if end > start:
            total += end - start
            cursor = end
    return WeekScore(
        week_start=week_start,
        meeting_hours=round(total.total_seconds() / 3600, 1),
        working_days=working_days,
    )
