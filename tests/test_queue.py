from datetime import date

from jeeves.model import Preferences
from jeeves.queue import decision_queue
from tests.factories import make_task


def test_queue_takes_limit_hits_splits_and_uncertain_duplicates_oldest_first():
    tasks = [
        make_task("new_limit", deferrals=3, created=date(2026, 9, 20)),
        make_task("old_split", size="L", created=date(2026, 8, 1)),
        make_task("dup", created=date(2026, 9, 1)),
        make_task("normal"),
    ]
    assert decision_queue(tasks, ["dup"], Preferences()) == [
        "old_split",
        "dup",
        "new_limit",
    ]


def test_queue_is_capped():
    tasks = [
        make_task(f"t{i}", deferrals=3, created=date(2026, 9, i + 1)) for i in range(7)
    ]
    assert decision_queue(tasks, [], Preferences(queue_cap=5)) == [
        f"t{i}" for i in range(5)
    ]


def test_backlog_l_tasks_do_not_flood_the_queue():
    assert (
        decision_queue([make_task(size="L", status="Backlog")], [], Preferences()) == []
    )


def test_closed_tasks_are_not_queued():
    assert (
        decision_queue([make_task(status="Done", deferrals=3)], [], Preferences()) == []
    )
