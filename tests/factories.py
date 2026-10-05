from datetime import date, datetime
from zoneinfo import ZoneInfo

from jeeves.model import CalendarEvent, Snapshot, Task

BERLIN = ZoneInfo("Europe/Berlin")
TODAY = date(2026, 10, 7)
YESTERDAY = date(2026, 10, 6)


def at(hour: int, minute: int = 0, day: date = TODAY) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=BERLIN)


def make_task(task_id: str = "t1", **overrides) -> Task:
    fields = {
        "id": task_id,
        "title": f"Task {task_id}",
        "status": "Not Started",
        "created": date(2026, 9, 1),
        "last_edited": date(2026, 10, 1),
        "area": "Work",
        "size": "M",
        "deadline_type": "Soft",
    }
    return Task(**{**fields, **overrides})


def make_event(
    event_id: str = "e1", start=None, end=None, **overrides
) -> CalendarEvent:
    fields = {
        "id": event_id,
        "title": f"Meeting {event_id}",
        "start": start or at(10),
        "end": end or at(11),
    }
    return CalendarEvent(**{**fields, **overrides})


def make_snapshot(tasks=(), events=(), now=None, **overrides) -> Snapshot:
    return Snapshot(
        now=now or at(7, 30), tasks=list(tasks), events=list(events), **overrides
    )
