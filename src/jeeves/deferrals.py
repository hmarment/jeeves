from datetime import date

from jeeves.hygiene import roll_due
from jeeves.model import DailyPlanState, FieldChange, Task, change


def planned_ids(plan: DailyPlanState | None) -> set[str]:
    if plan is None:
        return set()
    return set(plan.must_do_ids) | set(plan.quick_win_ids)


def close_out_changes(
    tasks: list[Task], plan: DailyPlanState | None, today: date, deferral_limit: int
) -> list[FieldChange]:
    planned = planned_ids(plan)
    changes = []
    for task in tasks:
        if (
            task.id not in planned
            or not task.is_open
            or task.deferrals >= deferral_limit
        ):
            continue
        deferrals = task.deferrals
        if task.last_deferred is None or task.last_deferred < plan.day:
            deferrals += 1
            changes.append(
                change(task, "deferrals", deferrals, f"planned {plan.day}, not done")
            )
            changes.append(change(task, "last_deferred", plan.day, "deferral recorded"))
        if (
            deferrals < deferral_limit
            and task.effective_deadline_type == "Soft"
            and task.due is not None
            and task.due < today
        ):
            changes.extend(roll_due(task, today, "carried over from yesterday's plan"))
    return changes


def yesterday_completed(tasks: list[Task], plan: DailyPlanState | None) -> int | None:
    if plan is None or plan.must_dos_completed is not None:
        return None
    done = {task.id for task in tasks if task.status == "Done"}
    return sum(1 for task_id in plan.must_do_ids if task_id in done)
