from datetime import date, timedelta

from jeeves.model import PARKED_STATUS, DailyPlanState, Preferences, Task


def is_first_planned_day_of_week(today: date, previous: DailyPlanState | None) -> bool:
    monday = today - timedelta(days=today.weekday())
    return previous is None or previous.day < monday


def backlog_review(tasks: list[Task], prefs: Preferences) -> list[str]:
    candidates = sorted(
        (task for task in tasks if task.status == PARKED_STATUS),
        key=lambda task: (task.last_reviewed or date.min, task.last_edited, task.id),
    )
    return [task.id for task in candidates[: prefs.backlog_review_count]]
