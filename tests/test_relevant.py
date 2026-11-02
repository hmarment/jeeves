from datetime import date

from jeeves.relevant import LIMIT, also_relevant, birthday_ids
from tests.factories import TODAY, make_task

HORIZON = date(2026, 10, 13)


def relevant(tasks, planned=(), frozen=(), declined=()):
    return also_relevant(
        tasks, set(planned), TODAY, HORIZON, set(frozen), set(declined)
    )


def test_birthdays_are_overdue_or_due_within_two_days_oldest_first():
    tasks = [
        make_task("late", title="Message Ann — happy birthday", due=date(2026, 10, 1)),
        make_task("soon", title="Buy gift for Bob", due=date(2026, 10, 9)),
        make_task("far", title="Message Cy — happy birthday", due=date(2026, 10, 10)),
        make_task("undated", title="Message Di — happy birthday"),
        make_task("done", title="Message Ed — happy birthday", status="Done"),
        make_task("other", title="Write report", due=date(2026, 10, 1)),
    ]
    assert birthday_ids(tasks, TODAY) == ["late", "soon"]


def test_birthdays_include_the_backlog():
    task = make_task("b", title="Message Ann — happy birthday", status="Backlog")
    assert birthday_ids([task.model_copy(update={"due": TODAY})], TODAY) == ["b"]


def test_hard_overdue_and_upcoming_hard_are_listed_with_reasons():
    tasks = [
        make_task("over", due=date(2026, 10, 1), deadline_type="Hard"),
        make_task("soon", due=date(2026, 10, 9), deadline_type="Hard"),
        make_task("prio", priority="High"),
        make_task("plain"),
    ]
    shown, more = relevant(tasks)
    assert [(i.task_id, i.reason) for i in shown] == [
        ("over", "Hard, overdue since 01 Oct"),
        ("soon", "Hard, due Fri 09 Oct"),
        ("prio", "High priority"),
    ]
    assert more == 0


def test_planned_frozen_and_birthday_tasks_are_left_out():
    tasks = [
        make_task("planned", priority="High"),
        make_task("frozen", priority="High"),
        make_task("bday", title="Buy gift for Bob", priority="High"),
        make_task("shown", priority="High"),
    ]
    shown, _ = relevant(tasks, planned={"planned"}, frozen={"frozen"})
    assert [i.task_id for i in shown] == ["shown"]


def test_declined_yesterday_and_large_tasks_are_flagged():
    tasks = [
        make_task("dec"),
        make_task("big", priority="High", size="L"),
    ]
    shown, _ = relevant(tasks, declined={"dec"})
    reasons = {i.task_id: i.reason for i in shown}
    assert reasons == {
        "big": "High priority; L, needs splitting",
        "dec": "deferred yesterday",
    }


def test_list_is_capped_and_counts_the_rest():
    tasks = [make_task(f"t{i}", priority="High") for i in range(LIMIT + 3)]
    shown, more = relevant(tasks)
    assert len(shown) == LIMIT
    assert more == 3
