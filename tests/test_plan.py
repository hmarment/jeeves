from datetime import date

from jeeves.model import DailyPlanState, Inference
from jeeves.plan import decide
from tests.factories import TODAY, YESTERDAY, at, make_event, make_snapshot, make_task


def test_weekend_is_skipped():
    result = decide(make_snapshot([make_task()], now=at(7, 30, day=date(2026, 10, 10))))
    assert result.status == "skipped"
    assert result.changes == []
    assert result.dm_text == ""


def test_locked_plan_changes_nothing():
    snapshot = make_snapshot(
        [make_task(due=YESTERDAY)],
        [make_event("old", start=at(9), end=at(10), pa_created=True)],
        today_plan=DailyPlanState(day=TODAY, ritual_done=True),
    )
    result = decide(snapshot)
    assert result.status == "locked"
    assert result.changes == []
    assert result.blocks_create == []
    assert result.blocks_delete == []


def test_full_run_plans_books_and_replaces_old_pa_blocks():
    old_block = make_event("old", start=at(9), end=at(10), pa_created=True)
    tasks = [make_task("a", due=TODAY, deadline_type="Hard"), make_task("s", size="S")]
    result = decide(make_snapshot(tasks, [old_block]))
    assert result.status == "planned"
    assert result.must_do_ids == ["a"]
    assert result.quick_win_ids == ["s"]
    assert [d.event_id for d in result.blocks_delete] == ["old"]
    assert {b.task_id for b in result.blocks_create} == {"a", None}
    assert "Run /start-day" in result.dm_text


def test_inference_runs_before_rolling():
    task = make_task(due=YESTERDAY, deadline_type=None)
    result = decide(
        make_snapshot([task], inferences={"t1": Inference(deadline_type="Hard")})
    )
    assert ("t1", "due") not in {(c.task_id, c.field) for c in result.changes}


def test_yesterday_close_out_and_completion_are_reported():
    plan = DailyPlanState(day=YESTERDAY, must_do_ids=["done", "open"])
    tasks = [make_task("done", status="Done"), make_task("open")]
    result = decide(make_snapshot(tasks, yesterday_plan=plan))
    assert result.yesterday_completed == 1
    assert ("open", "deferrals") in {(c.task_id, c.field) for c in result.changes}


def test_metrics_and_queue():
    tasks = [
        make_task("h", due=YESTERDAY, deadline_type="Hard"),
        make_task("d", deferrals=3),
    ]
    result = decide(make_snapshot(tasks))
    assert result.hard_overdue_count == 1
    assert result.deferral_limit_count == 1
    assert result.queue_ids == ["d"]
    assert "d" not in result.must_do_ids


def test_late_run_keeps_past_pa_blocks():
    past = make_event("past", start=at(9), end=at(10), pa_created=True)
    future = make_event("future", start=at(16), end=at(17), pa_created=True)
    result = decide(make_snapshot([make_task()], [past, future], now=at(15)))
    assert [d.event_id for d in result.blocks_delete] == ["future"]
    assert all(b.start >= at(15) for b in result.blocks_create)


def test_queue_overflow_is_not_selected_or_rolled():
    tasks = [
        make_task(f"q{i}", deferrals=3, created=date(2026, 9, i + 1)) for i in range(6)
    ]
    tasks.append(make_task("dup", due=YESTERDAY))
    snapshot = make_snapshot(
        [*tasks, make_task("orig")], inferences={"dup": Inference(duplicate_of="orig")}
    )
    result = decide(snapshot)
    assert "q5" not in result.must_do_ids
    assert ("dup", "due") not in {(c.task_id, c.field) for c in result.changes}
    assert "dup" not in result.must_do_ids


def test_stale_pa_stamp_is_cleared_when_task_leaves_today():
    task = make_task(status="Pending", planned_by_pa=date(2026, 9, 30))
    result = decide(make_snapshot([task]))
    assert ("t1", "planned_by_pa") in {(c.task_id, c.field) for c in result.changes}


def test_hard_overdue_in_backlog_does_not_count():
    tasks = [
        make_task("parked", status="Backlog", due=YESTERDAY, deadline_type="Hard"),
        make_task("live", due=YESTERDAY, deadline_type="Hard"),
    ]
    assert decide(make_snapshot(tasks)).hard_overdue_count == 1
