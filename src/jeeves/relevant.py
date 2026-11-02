from datetime import date, timedelta

from jeeves.model import (
    PARKED_STATUS,
    SELECTABLE_STATUSES,
    AlsoRelevant,
    Task,
)
from jeeves.selection import _is_hard, _rank_key

LIMIT = 5
BIRTHDAY_LOOKAHEAD_DAYS = 2


def birthday_ids(tasks: list[Task], today: date) -> list[str]:
    horizon = today + timedelta(days=BIRTHDAY_LOOKAHEAD_DAYS)
    due = [
        task
        for task in tasks
        if task.is_open
        and task.is_birthday
        and task.due is not None
        and task.due <= horizon
    ]
    due.sort(key=lambda task: (task.due, task.created, task.id))
    return [task.id for task in due]


def _reason(
    task: Task, today: date, horizon_end: date, declined: set[str]
) -> str | None:
    if _is_hard(task) and task.due < today:
        return f"Hard, overdue since {task.due:%d %b}"
    if _is_hard(task) and task.due <= horizon_end:
        return f"Hard, due {task.due:%a %d %b}"
    if task.id in declined:
        return "deferred yesterday"
    if task.priority in ("High", "Very High"):
        return f"{task.priority} priority"
    if task.rock_linked:
        return "Rock-linked"
    return None


def also_relevant(
    tasks: list[Task],
    planned: set[str],
    today: date,
    horizon_end: date,
    frozen: set[str],
    declined: set[str],
) -> tuple[list[AlsoRelevant], int]:
    found = []
    for task in tasks:
        if task.id in planned or task.id in frozen or task.is_birthday:
            continue
        plannable = task.status in SELECTABLE_STATUSES or (
            task.status == PARKED_STATUS
            and _is_hard(task)
            and today <= task.due <= horizon_end
        )
        reason = _reason(task, today, horizon_end, declined) if plannable else None
        if reason is None:
            continue
        if task.size == "L":
            reason += "; L, needs splitting"
        found.append((task, reason))
    found.sort(key=lambda item: _rank_key(item[0], today, horizon_end))
    shown = [AlsoRelevant(task_id=t.id, reason=r) for t, r in found[:LIMIT]]
    return shown, max(len(found) - LIMIT, 0)
