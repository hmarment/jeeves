from jeeves.model import SELECTABLE_STATUSES, Preferences, Task


def queue_candidates(
    tasks: list[Task], uncertain_duplicates: list[str], prefs: Preferences
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
        )
    ]
    candidates.sort(key=lambda task: (task.created, task.id))
    return [task.id for task in candidates]


def decision_queue(
    tasks: list[Task], uncertain_duplicates: list[str], prefs: Preferences
) -> list[str]:
    return queue_candidates(tasks, uncertain_duplicates, prefs)[: prefs.queue_cap]
