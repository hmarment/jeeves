from dataclasses import dataclass
from datetime import date

from jeeves.model import SELECTABLE_STATUSES, Preferences, Task

PRIORITY_RANK = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3, "Very Low": 4}


@dataclass(frozen=True)
class Selection:
    must_do_ids: list[str]
    quick_win_ids: list[str]
    over_capacity_minutes: int


def minutes_for(task: Task, prefs: Preferences) -> int:
    return prefs.size_minutes.get(task.size or "M", prefs.size_minutes["M"])


def _is_hard(task: Task) -> bool:
    return task.effective_deadline_type == "Hard" and task.due is not None


def _tier(task: Task, today: date, horizon_end: date) -> int:
    if _is_hard(task) and task.due <= today:
        return 0
    if _is_hard(task) and task.due <= horizon_end and task.size == "M":
        return 1
    if task.rock_linked or task.priority in ("High", "Very High"):
        return 2
    return 3


def _rank_key(task: Task, today: date, horizon_end: date) -> tuple:
    return (
        _tier(task, today, horizon_end),
        task.due or date.max,
        PRIORITY_RANK.get(task.priority, 5),
        task.created,
        task.id,
    )


def _is_candidate(task: Task, excluded: set[str], horizon_end: date) -> bool:
    if task.id in excluded or task.size == "L":
        return False
    if task.status in SELECTABLE_STATUSES:
        return True
    return task.status == "Backlog" and _is_hard(task) and task.due <= horizon_end


def select(
    tasks: list[Task],
    today: date,
    horizon_end: date,
    focus: int,
    prefs: Preferences,
    excluded: set[str],
) -> Selection:
    candidates = sorted(
        (task for task in tasks if _is_candidate(task, excluded, horizon_end)),
        key=lambda task: _rank_key(task, today, horizon_end),
    )
    ordered = [t for t in candidates if t.is_manual_today] + [
        t for t in candidates if not t.is_manual_today
    ]
    budget = max(focus - prefs.quick_wins_minutes, 0)
    slots = {"Work": prefs.work_must_dos, "Personal": prefs.personal_must_dos}
    must_dos, used = [], 0
    for task in ordered:
        area = task.area or "Work"
        forced = task.is_manual_today or _tier(task, today, horizon_end) == 0
        if slots[area] == 0 or (task.size == "S" and not forced):
            continue
        cost = minutes_for(task, prefs) if area == "Work" else 0
        if cost and not forced and used + cost > budget:
            continue
        must_dos.append(task)
        used += cost
        slots[area] -= 1

    chosen = {task.id for task in must_dos}
    quick_pool = sorted(
        (t for t in candidates if t.id not in chosen and t.size == "S"),
        key=lambda task: (task.due or date.max, task.created, task.id),
    )
    quick_wins, quick_used = [], 0
    for task in quick_pool:
        cost = minutes_for(task, prefs)
        if quick_used + cost <= prefs.quick_wins_minutes:
            quick_wins.append(task.id)
            quick_used += cost
    return Selection(
        must_do_ids=[task.id for task in must_dos],
        quick_win_ids=quick_wins,
        over_capacity_minutes=max(used - budget, 0),
    )
