from datetime import date

from jeeves.model import Preferences
from jeeves.selection import select
from tests.factories import TODAY, make_task

HORIZON = date(2026, 10, 13)


def pick(tasks, focus=480, prefs=None, excluded=()):
    return select(tasks, TODAY, HORIZON, focus, prefs or Preferences(), set(excluded))


def test_hard_due_today_beats_high_priority():
    tasks = [
        make_task("prio", priority="Very High"),
        make_task("hard", due=TODAY, deadline_type="Hard"),
    ]
    assert pick(tasks).must_do_ids[0] == "hard"


def test_big_hard_deadline_later_this_week_is_pulled_forward():
    tasks = [
        make_task("prio", priority="High"),
        make_task("later", due=date(2026, 10, 9), deadline_type="Hard"),
    ]
    assert pick(tasks).must_do_ids[:2] == ["later", "prio"]


def test_rolled_soft_date_does_not_jump_the_queue():
    tasks = [make_task("soft", due=TODAY), make_task("prio", priority="High")]
    assert pick(tasks).must_do_ids[:2] == ["prio", "soft"]


def test_three_work_plus_one_personal():
    tasks = [make_task(f"w{i}") for i in range(5)] + [
        make_task("p1", area="Personal"),
        make_task("p2", area="Personal"),
    ]
    assert pick(tasks).must_do_ids == ["p1", "w0", "w1", "w2"]


def test_capacity_caps_must_dos():
    tasks = [make_task(f"w{i}") for i in range(3)]
    assert pick(tasks, focus=200).must_do_ids == ["w0"]


def test_hard_due_today_is_kept_even_over_capacity():
    result = pick([make_task("hard", due=TODAY, deadline_type="Hard")], focus=60)
    assert result.must_do_ids == ["hard"]
    assert result.over_capacity_minutes == 60


def test_personal_must_do_does_not_consume_focus_time():
    assert pick([make_task("p", area="Personal")], focus=0).must_do_ids == ["p"]


def test_manual_today_tasks_are_ranked_first():
    tasks = [
        make_task("hard", due=TODAY, deadline_type="Hard"),
        make_task("mine", status="Today"),
    ]
    assert pick(tasks).must_do_ids[:2] == ["mine", "hard"]


def test_small_tasks_go_to_quick_wins_most_overdue_first():
    tasks = [
        make_task("s_new", size="S", due=TODAY),
        make_task("s_old", size="S", due=date(2026, 9, 1)),
        make_task("s3", size="S"),
    ]
    result = pick(tasks)
    assert result.must_do_ids == []
    assert result.quick_win_ids == ["s_old", "s_new"]


def test_l_queued_and_pending_tasks_are_not_selected():
    tasks = [
        make_task("big", size="L"),
        make_task("queued"),
        make_task("waiting", status="Pending"),
    ]
    assert pick(tasks, excluded={"queued"}).must_do_ids == []


def test_backlog_only_selected_for_near_hard_deadline():
    tasks = [
        make_task("b1", status="Backlog"),
        make_task("b2", status="Backlog", due=date(2026, 10, 9), deadline_type="Hard"),
    ]
    assert pick(tasks).must_do_ids == ["b2"]


def test_parked_task_with_overdue_hard_date_is_left_parked():
    tasks = [
        make_task(
            "stale", status="Backlog", due=date(2026, 5, 6), deadline_type="Hard"
        ),
        make_task(
            "soon", status="Backlog", due=date(2026, 10, 9), deadline_type="Hard"
        ),
    ]
    assert pick(tasks).must_do_ids == ["soon"]
