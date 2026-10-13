from datetime import date

from jeeves.model import SELECTABLE_STATUSES, CalendarEvent, Preferences, Task
from jeeves.workday import working_days_since


def is_stale_manual_today(
    task: Task, today: date, prefs: Preferences, events: list[CalendarEvent]
) -> bool:
    return (
        task.is_manual_today
        and working_days_since(task.last_edited, today, events) > prefs.stale_today_days
    )


def queue_candidates(
    tasks: list[Task],
    uncertain_duplicates: list[str],
    prefs: Preferences,
    today: date,
    events: list[CalendarEvent] = (),
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
            or is_stale_manual_today(task, today, prefs, events)
        )
    ]
    candidates.sort(key=_urgency)
    return [task.id for task in candidates]


def _urgency(task: Task) -> tuple:
    if task.effective_deadline_type == "Hard" and task.due is not None:
        return (0, task.due, task.created, task.id)
    return (1, date.max, task.created, task.id)


def decision_queue(
    tasks: list[Task],
    uncertain_duplicates: list[str],
    prefs: Preferences,
    today: date,
    events: list[CalendarEvent] = (),
) -> list[str]:
    return queue_candidates(tasks, uncertain_duplicates, prefs, today, events)[
        : prefs.queue_cap
    ]


def frozen_ids(
    tasks: list[Task],
    uncertain_duplicates: list[str],
    prefs: Preferences,
    today: date,
    events: list[CalendarEvent] = (),
) -> set[str]:
    queued = set(decision_queue(tasks, uncertain_duplicates, prefs, today, events))
    by_id = {task.id: task for task in tasks}
    # Overflow that is Henry's own Today pick or has a Hard date stays plannable:
    # hiding it from both the plan and the queue would leave it nowhere.
    return {
        task_id
        for task_id in queue_candidates(
            tasks, uncertain_duplicates, prefs, today, events
        )
        if task_id in queued
        or not _must_stay_visible(by_id[task_id], today, prefs, events)
    }


def _must_stay_visible(
    task: Task, today: date, prefs: Preferences, events: list[CalendarEvent]
) -> bool:
    return is_stale_manual_today(task, today, prefs, events) or _urgency(task)[0] == 0
