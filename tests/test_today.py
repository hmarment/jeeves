from jeeves.today import today_changes
from tests.factories import TODAY, YESTERDAY, make_task


def fields(changes):
    return {(c.task_id, c.field): c.new for c in changes}


def test_selected_tasks_move_to_today_with_pa_stamp():
    assert fields(today_changes([make_task()], ["t1"], TODAY)) == {
        ("t1", "status"): "Today",
        ("t1", "planned_by_pa"): TODAY,
    }


def test_stale_pa_task_is_cleared():
    task = make_task(status="Today", planned_by_pa=YESTERDAY)
    assert fields(today_changes([task], [], TODAY)) == {
        ("t1", "status"): "Not Started",
        ("t1", "planned_by_pa"): None,
    }


def test_manual_today_task_is_never_cleared():
    assert today_changes([make_task(status="Today")], [], TODAY) == []


def test_selected_manual_today_task_is_left_alone():
    assert today_changes([make_task(status="Today")], ["t1"], TODAY) == []


def test_reselected_pa_task_is_restamped_not_moved():
    task = make_task(status="Today", planned_by_pa=YESTERDAY)
    assert fields(today_changes([task], ["t1"], TODAY)) == {
        ("t1", "planned_by_pa"): TODAY
    }


def test_same_day_rerun_clears_dropped_pa_picks():
    task = make_task(status="Today", planned_by_pa=TODAY)
    assert fields(today_changes([task], [], TODAY))[("t1", "status")] == "Not Started"


def test_stamp_is_cleared_once_task_is_out_of_today():
    task = make_task(status="In Progress", planned_by_pa=YESTERDAY)
    assert fields(today_changes([task], [], TODAY)) == {("t1", "planned_by_pa"): None}


def test_closed_tasks_keep_their_stamp():
    task = make_task(status="Done", planned_by_pa=YESTERDAY)
    assert today_changes([task], [], TODAY) == []
