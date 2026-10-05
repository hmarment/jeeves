from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from jeeves.model import Preferences, Snapshot, apply_changes, change
from tests.factories import TODAY, at, make_event, make_task


def test_naive_now_is_rejected():
    with pytest.raises(ValidationError, match="timezone-aware"):
        Snapshot(now=datetime(2026, 10, 7, 7, 30), tasks=[])  # noqa: DTZ001


def test_naive_event_time_is_rejected():
    with pytest.raises(ValidationError, match="timezone-aware"):
        make_event(start=datetime(2026, 10, 7, 10, 0))  # noqa: DTZ001


def test_unknown_snapshot_field_is_rejected():
    with pytest.raises(ValidationError):
        Snapshot(now=at(7, 30), tasks=[], surprise=1)


def test_default_mode_is_propose_only():
    assert Preferences().mode == "propose-only"


def test_protected_prefix_is_always_hard():
    ninety = make_task(title="90 | Decision on platforms", deadline_type=None)
    jira = make_task(title="JIRA | ASQ-1 fix", deadline_type="Soft")
    assert ninety.effective_deadline_type == "Hard"
    assert jira.effective_deadline_type == "Hard"


def test_unassessed_task_needs_inference():
    assert make_task(size=None).needs_inference
    assert not make_task().needs_inference


def test_someday_and_done_are_not_open():
    assert not make_task(status="Someday").is_open
    assert not make_task(status="Done").is_open
    assert make_task(status="Backlog").is_open


def test_apply_changes_returns_updated_copies():
    task = make_task(deferrals=1)
    updated = apply_changes([task], [change(task, "deferrals", 2, "test")])
    assert updated[0].deferrals == 2
    assert task.deferrals == 1


def test_change_records_old_value():
    task = make_task(due=TODAY)
    assert change(task, "due", None, "x").old == TODAY


def test_snapshot_times_are_normalised_to_berlin():
    snapshot = Snapshot(now=datetime(2026, 10, 7, 5, 30, tzinfo=UTC), tasks=[])
    assert snapshot.now == at(7, 30)
    assert str(snapshot.now.tzinfo) == "Europe/Berlin"


def test_event_times_are_normalised_to_berlin():
    event = make_event(start=datetime(2026, 10, 6, 22, 0, tzinfo=UTC))
    assert event.start.date() == TODAY
    assert str(event.start.tzinfo) == "Europe/Berlin"
