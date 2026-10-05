from datetime import UTC, date, datetime

from jeeves.model import Preferences, Snapshot
from jeeves.workday import (
    focus_minutes,
    free_intervals,
    is_working_day,
    working_day_on_or_after,
    working_days_ahead,
)
from tests.factories import TODAY, at, make_event


def test_weekend_is_not_a_working_day():
    assert not is_working_day(date(2026, 10, 10), [])


def test_all_day_out_of_office_blocks_the_day():
    ooo = make_event(
        start=at(0), end=at(0, day=date(2026, 10, 8)), all_day=True, out_of_office=True
    )
    assert not is_working_day(TODAY, [ooo])
    assert is_working_day(date(2026, 10, 8), [ooo])


def test_timed_out_of_office_does_not_block_the_day():
    assert is_working_day(TODAY, [make_event(out_of_office=True)])


def test_multi_day_leave_skips_to_first_day_back():
    leave = make_event(
        start=at(0), end=at(0, day=date(2026, 10, 12)), all_day=True, out_of_office=True
    )
    assert working_day_on_or_after(TODAY, [leave]) == date(2026, 10, 12)


def test_working_days_ahead_skips_weekend():
    assert working_days_ahead(date(2026, 10, 9), 2, []) == [
        date(2026, 10, 9),
        date(2026, 10, 12),
    ]


def test_free_time_excludes_meetings_and_buffers():
    prefs = Preferences(meeting_buffer_minutes=10)
    intervals = free_intervals(at(7, 30), [make_event(start=at(10), end=at(11))], prefs)
    assert intervals == [(at(9), at(9, 50)), (at(11, 10), at(17, 30))]


def test_pa_blocks_and_all_day_events_do_not_consume_time():
    events = [
        make_event("pa", start=at(9), end=at(17), pa_created=True),
        make_event("ad", start=at(0), end=at(0, day=date(2026, 10, 8)), all_day=True),
    ]
    assert free_intervals(at(7, 30), events, Preferences()) == [(at(9), at(17, 30))]


def test_slivers_shorter_than_minimum_block_are_dropped():
    prefs = Preferences(meeting_buffer_minutes=0, min_block_minutes=30)
    events = [make_event(start=at(9, 20), end=at(17, 30))]
    assert free_intervals(at(7, 30), events, prefs) == []


def test_free_time_after_dst_change():
    monday_after = date(2026, 10, 26)
    intervals = free_intervals(at(7, 30, day=monday_after), [], Preferences())
    assert focus_minutes(intervals) == 510


def test_focus_minutes_sums_intervals():
    assert focus_minutes([(at(9), at(9, 50)), (at(11, 10), at(17, 30))]) == 430


def test_utc_all_day_leave_still_blocks_the_berlin_day():
    ooo = make_event(
        start=datetime(2026, 10, 6, 22, 0, tzinfo=UTC),
        end=datetime(2026, 10, 7, 22, 0, tzinfo=UTC),
        all_day=True,
        out_of_office=True,
    )
    assert not is_working_day(TODAY, [ooo])


def test_utc_now_still_uses_berlin_working_hours():
    now = Snapshot(now=datetime(2026, 10, 7, 5, 30, tzinfo=UTC), tasks=[]).now
    assert free_intervals(now, [], Preferences())[0][0] == at(9)


def test_run_after_work_start_counts_only_remaining_time():
    assert free_intervals(at(15), [], Preferences()) == [(at(15), at(17, 30))]
