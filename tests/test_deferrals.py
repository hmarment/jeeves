from jeeves.deferrals import close_out_changes, planned_ids, yesterday_completed
from jeeves.model import DailyPlanState
from tests.factories import TODAY, YESTERDAY, make_task

PLAN = DailyPlanState(day=YESTERDAY, must_do_ids=["t1"], quick_win_ids=["q1"])


def fields(changes):
    return {(c.task_id, c.field): c.new for c in changes}


def test_planned_ids_covers_must_dos_and_quick_wins():
    assert planned_ids(PLAN) == {"t1", "q1"}
    assert planned_ids(None) == set()


def test_planned_unfinished_task_gets_one_deferral():
    result = fields(close_out_changes([make_task()], PLAN, TODAY, 3))
    assert result[("t1", "deferrals")] == 1
    assert result[("t1", "last_deferred")] == YESTERDAY


def test_shutdown_deferral_is_not_double_counted():
    task = make_task(deferrals=1, last_deferred=YESTERDAY)
    assert ("t1", "deferrals") not in fields(close_out_changes([task], PLAN, TODAY, 3))


def test_done_tasks_are_not_deferred():
    assert close_out_changes([make_task(status="Done")], PLAN, TODAY, 3) == []


def test_soft_due_is_carried_to_today():
    result = fields(close_out_changes([make_task(due=YESTERDAY)], PLAN, TODAY, 3))
    assert result[("t1", "due")] == TODAY
    assert result[("t1", "original_due")] == YESTERDAY


def test_hard_due_is_never_carried():
    task = make_task(due=YESTERDAY, deadline_type="Hard")
    assert ("t1", "due") not in fields(close_out_changes([task], PLAN, TODAY, 3))


def test_reaching_the_limit_stops_rolling():
    task = make_task(due=YESTERDAY, deferrals=2)
    result = fields(close_out_changes([task], PLAN, TODAY, 3))
    assert result[("t1", "deferrals")] == 3
    assert ("t1", "due") not in result


def test_task_already_at_limit_is_frozen():
    task = make_task(due=YESTERDAY, deferrals=3)
    assert close_out_changes([task], PLAN, TODAY, 3) == []


def test_unplanned_tasks_are_ignored():
    assert close_out_changes([make_task("other")], PLAN, TODAY, 3) == []


def test_yesterday_completed_counts_done_must_dos():
    plan = DailyPlanState(day=YESTERDAY, must_do_ids=["t1", "t2"])
    assert yesterday_completed([make_task("t1", status="Done")], plan) == 1


def test_yesterday_completed_respects_shutdown_value():
    plan = DailyPlanState(day=YESTERDAY, must_dos_completed=2)
    assert yesterday_completed([], plan) is None
