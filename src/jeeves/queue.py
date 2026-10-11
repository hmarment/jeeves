from datetime import date

from jeeves.model import SELECTABLE_STATUSES, Preferences, Task


def _is_stale_manual_today(task: Task, today: date, prefs: Preferences) -> bool:
    return (
        task.is_manual_today
        and (today - task.last_edited).days > prefs.stale_today_days
    )


def queue_candidates(
    tasks: list[Task], uncertain_duplicates: list[str], prefs: Preferences, today: date
) -> list[str]:
    uncertain = set(uncertain_duplicates)
    candidates = [
        task
        for task in tasks
        if task.is_open
        and (
            task.deferrals >= prefs.deferral_limit
            or task.id in uncertain
            or (task.size == "L" and task.status in SELECTABLE_STATUSES)
            or _is_stale_manual_today(task, today, prefs)
        )
    ]
    candidates.sort(key=lambda task: (task.created, task.id))
    return [task.id for task in candidates]


def decision_queue(
    tasks: list[Task], uncertain_duplicates: list[str], prefs: Preferences, today: date
) -> list[str]:
    return queue_candidates(tasks, uncertain_duplicates, prefs, today)[
        : prefs.queue_cap
    ]
