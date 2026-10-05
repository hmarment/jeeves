from datetime import date

from jeeves.booking import plan_blocks
from jeeves.deferrals import close_out_changes, planned_ids, yesterday_completed
from jeeves.dm import render_dm
from jeeves.hygiene import duplicate_changes, inference_changes, soft_roll_changes
from jeeves.model import (
    PARKED_STATUS,
    BlockDelete,
    FieldChange,
    PlanResult,
    Preferences,
    Snapshot,
    Task,
    apply_changes,
)
from jeeves.queue import decision_queue, queue_candidates
from jeeves.review import backlog_review, is_first_planned_day_of_week
from jeeves.selection import select
from jeeves.today import today_changes
from jeeves.workday import (
    focus_minutes,
    free_intervals,
    is_working_day,
    working_days_ahead,
)


def _metrics(tasks: list[Task], today: date, prefs: Preferences) -> dict[str, int]:
    return {
        "hard_overdue_count": sum(
            1
            for t in tasks
            if t.is_open
            and t.status != PARKED_STATUS
            and t.effective_deadline_type == "Hard"
            and t.due is not None
            and t.due < today
        ),
        "deferral_limit_count": sum(
            1 for t in tasks if t.is_open and t.deferrals >= prefs.deferral_limit
        ),
    }


def decide(snapshot: Snapshot) -> PlanResult:
    today, prefs, events = snapshot.today, snapshot.prefs, snapshot.events
    if not is_working_day(today, events):
        return PlanResult(status="skipped", reason="not a working day")
    if snapshot.today_plan is not None and snapshot.today_plan.ritual_done:
        return PlanResult(
            status="locked",
            reason="ritual done",
            **_metrics(snapshot.tasks, today, prefs),
        )

    tasks = snapshot.tasks
    changes: list[FieldChange] = []

    def run(step: list[FieldChange]) -> None:
        nonlocal tasks
        changes.extend(step)
        tasks = apply_changes(tasks, step)

    run(inference_changes(tasks, snapshot.inferences))
    duplicates, uncertain = duplicate_changes(tasks, snapshot.inferences)
    run(duplicates)
    completed = yesterday_completed(tasks, snapshot.yesterday_plan)
    run(close_out_changes(tasks, snapshot.yesterday_plan, today, prefs.deferral_limit))
    frozen = set(queue_candidates(tasks, uncertain, prefs))
    skip = planned_ids(snapshot.yesterday_plan) | frozen
    run(soft_roll_changes(tasks, today, skip, prefs.deferral_limit))

    queue = decision_queue(tasks, uncertain, prefs)
    horizon_end = working_days_ahead(today, prefs.week_ahead_working_days, events)[-1]
    intervals = free_intervals(snapshot.now, events, prefs)
    focus = focus_minutes(intervals)
    selection = select(tasks, today, horizon_end, focus, prefs, frozen)
    run(today_changes(tasks, selection.must_do_ids + selection.quick_win_ids, today))

    by_id = {task.id: task for task in tasks}
    must_dos = [by_id[task_id] for task_id in selection.must_do_ids]
    return PlanResult(
        status="planned",
        focus_minutes=focus,
        must_do_ids=selection.must_do_ids,
        quick_win_ids=selection.quick_win_ids,
        queue_ids=queue,
        review_ids=(
            backlog_review(tasks, prefs)
            if is_first_planned_day_of_week(today, snapshot.yesterday_plan)
            else []
        ),
        changes=changes,
        blocks_create=plan_blocks(
            must_dos, bool(selection.quick_win_ids), intervals, snapshot.now, prefs
        ),
        blocks_delete=[
            BlockDelete(event_id=event.id, reason="replanned")
            for event in events
            if event.pa_created
            and event.start.date() == today
            and event.start >= snapshot.now
        ],
        over_capacity_minutes=selection.over_capacity_minutes,
        yesterday_completed=completed,
        dm_text=render_dm(
            today,
            focus,
            must_dos[0] if must_dos else None,
            len(queue),
            selection.over_capacity_minutes,
        ),
        **_metrics(tasks, today, prefs),
    )
