import json
import re
from datetime import date, datetime
from typing import Any, get_args

from jeeves.model import (
    BERLIN,
    Area,
    CalendarEvent,
    DailyPlanState,
    DeadlineType,
    Inference,
    Preferences,
    Size,
    Snapshot,
    Task,
)

JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _envelope(payload: Any) -> dict | None:
    if isinstance(payload, str) and payload.lstrip()[:1] in ("{", "["):
        try:
            return _envelope(json.loads(payload))
        except json.JSONDecodeError:
            return None
    if isinstance(payload, dict):
        if isinstance(payload.get("pages"), list):
            return payload
        children = payload.values()
    elif isinstance(payload, list):
        children = payload
    else:
        return None
    for child in children:
        found = _envelope(child)
        if found is not None:
            return found
    return None


def unwrap_pages(payload: Any) -> list[dict]:
    envelope = _envelope(payload)
    return envelope["pages"] if envelope else []


def _required_pages(payload: Any, label: str) -> list[dict]:
    envelope = _envelope(payload)
    if envelope is None:
        raise ValueError(f"no 'pages' found in the {label} payload")
    if envelope.get("count") and not envelope["pages"]:
        raise ValueError(f"{label} payload has count {envelope['count']} but no pages")
    return envelope["pages"]


def berlin_date(value: str | None) -> date | None:
    if not value:
        return None
    if len(value) == 10:
        return date.fromisoformat(value)
    return datetime.fromisoformat(value).astimezone(BERLIN).date()


def _choice(value: Any, allowed: Any) -> Any:
    return value if value in get_args(allowed) else None


def task_from_page(page: dict) -> Task:
    props = page["properties"]
    projects = props.get("Project Name") or []
    return Task(
        id=page["id"],
        title=props.get("Task name") or "",
        status=props.get("Status") or "",
        created=berlin_date(page["created_time"]),
        last_edited=berlin_date(page["last_edited_time"]),
        due=berlin_date(props.get("Due")),
        original_due=berlin_date(props.get("Original due")),
        priority=props.get("Priority"),
        size=_choice(props.get("Size"), Size),
        deadline_type=_choice(props.get("Deadline type"), DeadlineType),
        area=_choice(props.get("Area"), Area),
        confidential=bool(props.get("Confidential")),
        deferrals=int(props.get("Deferrals") or 0),
        last_deferred=berlin_date(props.get("Last deferred")),
        planned_by_pa=berlin_date(props.get("Planned by PA")),
        last_reviewed=berlin_date(props.get("Last reviewed")),
        rock_linked=any("Rock" in str(name) for name in projects),
    )


def plan_from_page(page: dict) -> DailyPlanState:
    props = page["properties"]
    completed = props.get("Must-dos completed")
    return DailyPlanState(
        day=berlin_date(props["Date"]),
        must_do_ids=props.get("Must-dos") or [],
        quick_win_ids=props.get("Quick wins") or [],
        ritual_done=bool(props.get("Ritual done")),
        shutdown_done=bool(props.get("Shutdown done")),
        must_dos_completed=None if completed is None else int(completed),
    )


def _google_time(value: dict) -> tuple[datetime, bool]:
    if "date" in value:
        return datetime.combine(
            date.fromisoformat(value["date"]), datetime.min.time(), BERLIN
        ), True
    return datetime.fromisoformat(value["dateTime"]), False


def _declined(raw: dict) -> bool:
    return any(
        attendee.get("self") and attendee.get("responseStatus") == "declined"
        for attendee in raw.get("attendees") or []
    )


def event_from_google(raw: dict, prefs: Preferences) -> CalendarEvent | None:
    start, all_day = _google_time(raw["start"])
    end, _ = _google_time(raw["end"])
    title = raw.get("summary") or ""
    keyword_hit = any(k.lower() in title.lower() for k in prefs.ooo_keywords)
    out_of_office = raw.get("eventType") == "outOfOffice" or (all_day and keyword_hit)
    if not out_of_office and (
        _declined(raw) or raw.get("transparency") == "transparent"
    ):
        return None
    return CalendarEvent(
        id=raw["id"],
        title=title,
        start=start,
        end=end,
        all_day=all_day or raw.get("eventType") == "outOfOffice",
        pa_created="[jeeves]" in (raw.get("description") or ""),
        out_of_office=out_of_office,
    )


def extract_preferences(payload: Any) -> Preferences:
    if isinstance(payload, dict):
        return Preferences.model_validate(payload)
    match = JSON_BLOCK.search(payload)
    if match is None:
        raise ValueError("no JSON settings block found in PA Preferences")
    return Preferences.model_validate(json.loads(match.group(1)))


def build_snapshot(
    tasks_payload: Any,
    plan_payload: Any,
    events_payload: list[dict],
    prefs_payload: Any,
    now: str,
    inferences_payload: dict | None = None,
) -> Snapshot:
    prefs = extract_preferences(prefs_payload)
    current = datetime.fromisoformat(now).astimezone(BERLIN)
    plans = sorted(
        (plan_from_page(page) for page in _required_pages(plan_payload, "daily plan")),
        key=lambda plan: plan.day,
    )
    today = current.date()
    earlier = [plan for plan in plans if plan.day < today]
    events = [event_from_google(raw, prefs) for raw in events_payload]
    return Snapshot(
        now=current,
        prefs=prefs,
        tasks=[
            task_from_page(page) for page in _required_pages(tasks_payload, "tasks")
        ],
        events=[event for event in events if event is not None],
        yesterday_plan=earlier[-1] if earlier else None,
        today_plan=next((plan for plan in plans if plan.day == today), None),
        inferences={
            task_id: Inference.model_validate(value)
            for task_id, value in (inferences_payload or {}).items()
        },
    )
