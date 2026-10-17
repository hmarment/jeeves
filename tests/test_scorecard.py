from datetime import date

import pytest

from jeeves.model import Preferences
from jeeves.scorecard import score_week

WEEK = date(2026, 10, 12)
SELF = {"email": "me@example.com", "self": True}
OTHER = {"email": "colleague@example.com"}


def raw_event(start: str, end: str, event_id: str = "e1", **fields) -> dict:
    return {
        "id": event_id,
        "summary": "Sync",
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "attendees": [SELF, OTHER],
        **fields,
    }


def all_day(start: str, end: str, **fields) -> dict:
    return {
        "id": "ooo",
        "summary": "Urlaub",
        "start": {"date": start},
        "end": {"date": end},
        **fields,
    }


def hours(events: list[dict], week: date = WEEK) -> float | None:
    return score_week(events, week, Preferences()).meeting_hours


def test_meeting_with_other_attendee_counts():
    event = raw_event("2026-10-13T10:00:00+02:00", "2026-10-13T11:00:00+02:00")
    assert hours([event]) == 1.0


def test_no_other_attendee_is_not_meeting():
    event = raw_event(
        "2026-10-13T10:00:00+02:00", "2026-10-13T11:00:00+02:00", attendees=[SELF]
    )
    assert hours([event]) == 0.0


def test_resource_only_attendees_is_not_meeting():
    room = {"email": "room@resource.calendar.google.com", "resource": True}
    event = raw_event(
        "2026-10-13T10:00:00+02:00",
        "2026-10-13T11:00:00+02:00",
        attendees=[SELF, room],
    )
    assert hours([event]) == 0.0


def test_declined_and_transparent_excluded():
    declined = raw_event(
        "2026-10-13T10:00:00+02:00",
        "2026-10-13T11:00:00+02:00",
        event_id="d",
        attendees=[{**SELF, "responseStatus": "declined"}, OTHER],
    )
    free = raw_event(
        "2026-10-14T10:00:00+02:00",
        "2026-10-14T11:00:00+02:00",
        event_id="f",
        transparency="transparent",
    )
    assert hours([declined, free]) == 0.0


def test_focus_time_excluded_including_lunch():
    lunch = raw_event(
        "2026-10-13T12:00:00+02:00",
        "2026-10-13T13:00:00+02:00",
        summary="Lunch",
        eventType="focusTime",
    )
    assert hours([lunch]) == 0.0


def test_jeeves_block_excluded():
    block = raw_event(
        "2026-10-13T10:00:00+02:00",
        "2026-10-13T11:00:00+02:00",
        description="[jeeves]",
    )
    assert hours([block]) == 0.0


def test_overlapping_meetings_count_once():
    first = raw_event("2026-10-13T10:00:00+02:00", "2026-10-13T11:00:00+02:00")
    second = raw_event(
        "2026-10-13T10:30:00+02:00", "2026-10-13T11:30:00+02:00", event_id="e2"
    )
    assert hours([first, second]) == 1.5


def test_outside_working_hours_counts():
    early = raw_event("2026-10-13T08:00:00+02:00", "2026-10-13T08:30:00+02:00")
    late = raw_event(
        "2026-10-13T19:00:00+02:00", "2026-10-13T20:00:00+02:00", event_id="e2"
    )
    assert hours([early, late]) == 1.5


def test_event_crossing_week_start_is_clipped():
    event = raw_event("2026-10-11T23:00:00+02:00", "2026-10-12T01:00:00+02:00")
    assert hours([event]) == 1.0


def test_dst_week_counts_elapsed_time():
    event = raw_event("2026-10-25T01:00:00+02:00", "2026-10-25T04:00:00+01:00")
    assert hours([event], date(2026, 10, 19)) == 4.0


def test_full_ooo_week_is_none():
    score = score_week(
        [all_day("2026-10-12", "2026-10-17", eventType="outOfOffice")],
        WEEK,
        Preferences(),
    )
    assert score.meeting_hours is None
    assert score.working_days == 0


def test_part_ooo_week_scores_raw_hours():
    meeting = raw_event("2026-10-14T09:00:00+02:00", "2026-10-14T12:00:00+02:00")
    score = score_week(
        [all_day("2026-10-12", "2026-10-14"), meeting], WEEK, Preferences()
    )
    assert score.meeting_hours == 3.0
    assert score.working_days == 3


def test_non_monday_week_start_raises():
    with pytest.raises(ValueError):
        score_week([], date(2026, 10, 13), Preferences())


def test_rounds_to_one_decimal():
    event = raw_event("2026-10-13T10:00:00+02:00", "2026-10-13T10:20:00+02:00")
    assert hours([event]) == 0.3
