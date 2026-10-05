from datetime import date

from jeeves.model import DailyPlanState, Preferences
from jeeves.plan import decide
from jeeves.review import backlog_review, is_first_planned_day_of_week
from tests.factories import TODAY, YESTERDAY, at, make_snapshot, make_task

MONDAY = date(2026, 10, 5)


def parked(task_id, reviewed=None, edited=date(2026, 5, 1)):
    return make_task(
        task_id, status="Backlog", last_reviewed=reviewed, last_edited=edited
    )


def test_least_recently_reviewed_parked_tasks_come_first():
    tasks = [
        parked("recent", reviewed=date(2026, 9, 28)),
        parked("never_old", edited=date(2026, 1, 1)),
        parked("never_new", edited=date(2026, 6, 1)),
        parked("long_ago", reviewed=date(2026, 7, 1)),
        make_task("active"),
    ]
    assert backlog_review(tasks, Preferences(backlog_review_count=3)) == [
        "never_old",
        "never_new",
        "long_ago",
    ]


def test_first_planned_day_of_week():
    assert is_first_planned_day_of_week(MONDAY, None)
    assert is_first_planned_day_of_week(MONDAY, DailyPlanState(day=date(2026, 10, 2)))
    assert not is_first_planned_day_of_week(TODAY, DailyPlanState(day=YESTERDAY))
    assert is_first_planned_day_of_week(TODAY, DailyPlanState(day=date(2026, 10, 2)))


def test_review_only_on_first_planned_day_of_week():
    tasks = [parked("p1")]
    monday = decide(make_snapshot(tasks, now=at(7, 30, day=MONDAY)))
    midweek = decide(make_snapshot(tasks, yesterday_plan=DailyPlanState(day=YESTERDAY)))
    assert monday.review_ids == ["p1"]
    assert midweek.review_ids == []
