from datetime import date

from jeeves.model import Inference
from jeeves.reset import propose_reset
from tests.factories import make_snapshot, make_task


def fields(changes):
    return {(c.task_id, c.field): c.new for c in changes}


def test_stale_unproven_task_goes_to_someday_with_original_due_kept():
    task = make_task(due=date(2026, 6, 1), last_edited=date(2026, 7, 1))
    result = fields(propose_reset(make_snapshot([task])).changes)
    assert result[("t1", "status")] == "Someday"
    assert result[("t1", "original_due")] == date(2026, 6, 1)


def test_recent_soft_date_is_kept():
    task = make_task(due=date(2026, 10, 1), last_edited=date(2026, 9, 20))
    result = fields(propose_reset(make_snapshot([task])).changes)
    assert set(result) == {("t1", "original_due")}


def test_uninferred_deadline_type_is_left_alone_and_reported():
    task = make_task(
        due=date(2026, 6, 1), last_edited=date(2026, 7, 1), deadline_type=None
    )
    proposal = propose_reset(make_snapshot([task]))
    assert set(fields(proposal.changes)) == {("t1", "original_due")}
    assert proposal.uninferred_ids == ["t1"]


def test_older_unproven_date_is_cleared_but_preserved():
    task = make_task(due=date(2026, 9, 1), last_edited=date(2026, 8, 25))
    result = fields(propose_reset(make_snapshot([task])).changes)
    assert result[("t1", "due")] is None
    assert result[("t1", "original_due")] == date(2026, 9, 1)


def test_protected_and_hard_tasks_are_untouched_apart_from_preservation():
    old = date(2026, 5, 1)
    tasks = [
        make_task("n", title="90 | Ninety todo", due=old, last_edited=old),
        make_task("h", due=old, last_edited=old, deadline_type="Hard"),
    ]
    result = fields(propose_reset(make_snapshot(tasks)).changes)
    assert set(result) == {("n", "original_due"), ("h", "original_due")}


def test_closed_tasks_are_ignored():
    task = make_task(status="Done", due=date(2026, 5, 1), last_edited=date(2026, 5, 1))
    assert propose_reset(make_snapshot([task])).changes == []


def test_inferences_are_part_of_the_proposal():
    snapshot = make_snapshot(
        [make_task(size=None)], inferences={"t1": Inference(size="S")}
    )
    assert fields(propose_reset(snapshot).changes)[("t1", "size")] == "S"
