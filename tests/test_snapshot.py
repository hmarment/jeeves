import json
from datetime import date

import pytest

from jeeves.model import Preferences
from jeeves.snapshot import (
    build_snapshot,
    event_from_google,
    extract_preferences,
    plan_from_page,
    task_from_page,
    unwrap_pages,
)
from tests.factories import TODAY, YESTERDAY, at


def notion_task(**properties):
    base = {
        "Task name": "Write report",
        "Status": "Not Started",
        "Due": None,
        "Original due": None,
        "Priority": None,
        "Size": None,
        "Deadline type": None,
        "Area": None,
        "Confidential": False,
        "Deferrals": None,
        "Last deferred": None,
        "Planned by PA": None,
        "Project Name": [],
    }
    return {
        "id": "p1",
        "url": "https://notion/p1",
        "created_time": "2026-09-01T10:00:00.000Z",
        "last_edited_time": "2026-10-01T21:30:00.000Z",
        "properties": {**base, **properties},
    }


def test_unwrap_accepts_zapier_wrapper_and_plain_payload():
    page = notion_task()
    wrapped = {"isError": False, "results": {"data": {"data": {"pages": [page]}}}}
    assert unwrap_pages(wrapped) == [page]
    assert unwrap_pages({"pages": [page]}) == [page]


def test_task_maps_notion_properties():
    task = task_from_page(
        notion_task(
            Status="Today",
            Due="2026-10-09",
            Priority="High",
            Size="M",
            **{"Deadline type": "Hard", "Area": "Work", "Deferrals": 2.0},
            **{"Planned by PA": "2026-10-06", "Project Name": ["Rocks 26Q4 | Revenue"]},
        )
    )
    assert task.id == "p1"
    assert task.title == "Write report"
    assert task.status == "Today"
    assert task.due == date(2026, 10, 9)
    assert task.size == "M"
    assert task.deadline_type == "Hard"
    assert task.deferrals == 2
    assert task.planned_by_pa == YESTERDAY
    assert task.rock_linked


def test_utc_datetime_due_becomes_berlin_date():
    task = task_from_page(notion_task(Due="2026-10-06T22:30:00.000+00:00"))
    assert task.due == TODAY


def test_timestamps_become_berlin_dates():
    task = task_from_page(notion_task())
    assert task.created == date(2026, 9, 1)
    assert task.last_edited == date(2026, 10, 1)


def test_unknown_select_values_become_empty():
    task = task_from_page(notion_task(Size="XL", Area="Life"))
    assert task.size is None
    assert task.area is None


def test_daily_plan_row_maps_relations_and_flags():
    page = {
        "id": "d1",
        "properties": {
            "Date": "2026-10-06",
            "Must-dos": ["a", "b"],
            "Quick wins": ["c"],
            "Ritual done": True,
            "Shutdown done": False,
            "Must-dos completed": None,
        },
    }
    plan = plan_from_page(page)
    assert plan.day == YESTERDAY
    assert plan.must_do_ids == ["a", "b"]
    assert plan.quick_win_ids == ["c"]
    assert plan.ritual_done
    assert plan.must_dos_completed is None


def test_google_timed_event_maps_and_detects_pa_tag():
    raw = {
        "id": "e1",
        "summary": "🎯 Focus: x",
        "description": "[jeeves] https://notion/p1",
        "start": {"dateTime": "2026-10-07T09:00:00+02:00"},
        "end": {"dateTime": "2026-10-07T10:30:00+02:00"},
    }
    event = event_from_google(raw, Preferences())
    assert event.start == at(9)
    assert event.pa_created
    assert not event.all_day


def test_google_all_day_holiday_is_out_of_office():
    raw = {
        "id": "e2",
        "summary": "Urlaub",
        "start": {"date": "2026-10-07"},
        "end": {"date": "2026-10-08"},
    }
    event = event_from_google(raw, Preferences())
    assert event.all_day
    assert event.out_of_office
    assert event.start == at(0)


def test_out_of_office_event_type_is_detected():
    raw = {
        "id": "e3",
        "summary": "Away",
        "eventType": "outOfOffice",
        "start": {"dateTime": "2026-10-07T00:00:00+02:00"},
        "end": {"dateTime": "2026-10-08T00:00:00+02:00"},
    }
    assert event_from_google(raw, Preferences()).out_of_office


def test_declined_and_free_events_are_dropped():
    declined = {
        "id": "e4",
        "summary": "Optional sync",
        "start": {"dateTime": "2026-10-07T11:00:00+02:00"},
        "end": {"dateTime": "2026-10-07T12:00:00+02:00"},
        "attendees": [{"self": True, "responseStatus": "declined"}],
    }
    free = {**declined, "id": "e5", "attendees": [], "transparency": "transparent"}
    assert event_from_google(declined, Preferences()) is None
    assert event_from_google(free, Preferences()) is None


def test_preferences_extracted_from_page_text():
    text = 'Intro\n```json\n{"mode": "auto", "work_must_dos": 2}\n```\nmore'
    prefs = extract_preferences(text)
    assert prefs.mode == "auto"
    assert prefs.work_must_dos == 2


def test_preferences_text_without_json_is_an_error():
    with pytest.raises(ValueError, match="no JSON settings block"):
        extract_preferences("nothing here")


def test_build_snapshot_picks_today_and_latest_earlier_plan():
    rows = [
        {"id": "a", "properties": {"Date": "2026-10-02", "Must-dos": ["old"]}},
        {"id": "b", "properties": {"Date": "2026-10-06", "Must-dos": ["y"]}},
        {"id": "c", "properties": {"Date": "2026-10-07", "Ritual done": True}},
    ]
    snapshot = build_snapshot(
        tasks_payload={"pages": [notion_task()]},
        plan_payload={"pages": rows},
        events_payload=[],
        prefs_payload='```json\n{"mode": "propose-only"}\n```',
        now="2026-10-07T05:30:00+00:00",
        inferences_payload={"p1": {"size": "S"}},
    )
    assert snapshot.now == at(7, 30)
    assert snapshot.yesterday_plan.day == YESTERDAY
    assert snapshot.today_plan.ritual_done
    assert snapshot.inferences["p1"].size == "S"
    assert json.loads(snapshot.model_dump_json())["tasks"][0]["id"] == "p1"


def test_last_reviewed_is_mapped():
    task = task_from_page(notion_task(**{"Last reviewed": "2026-09-28"}))
    assert task.last_reviewed == date(2026, 9, 28)


def test_unwrap_handles_saved_file_envelope_and_json_strings():
    page = notion_task()
    inner = json.dumps({"results": {"data": {"data": {"pages": [page], "count": 1}}}})
    saved_file = [{"type": "text", "text": inner}]
    assert unwrap_pages(saved_file) == [page]
    assert unwrap_pages({"results": [{"data": {"pages": [page]}}]}) == [page]


def test_payload_without_pages_is_an_error():
    with pytest.raises(ValueError, match="no 'pages'"):
        build_snapshot(
            tasks_payload={"error": "404"},
            plan_payload={"pages": []},
            events_payload=[],
            prefs_payload="```json\n{}\n```",
            now="2026-10-07T05:30:00+00:00",
        )


def test_count_without_pages_is_an_error():
    with pytest.raises(ValueError, match="count"):
        build_snapshot(
            tasks_payload={"pages": [], "count": 12},
            plan_payload={"pages": []},
            events_payload=[],
            prefs_payload="```json\n{}\n```",
            now="2026-10-07T05:30:00+00:00",
        )
