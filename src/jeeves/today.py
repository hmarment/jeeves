from datetime import date

from jeeves.model import FieldChange, Task, change


def today_changes(
    tasks: list[Task], selected_ids: list[str], today: date
) -> list[FieldChange]:
    selected = set(selected_ids)
    changes = []
    for task in tasks:
        if task.id in selected:
            if task.status != "Today":
                changes.append(change(task, "status", "Today", "planned for today"))
                changes.append(
                    change(task, "planned_by_pa", today, "planned for today")
                )
            elif task.planned_by_pa is not None and task.planned_by_pa != today:
                changes.append(change(task, "planned_by_pa", today, "re-planned"))
        elif (
            task.status == "Today"
            and task.planned_by_pa is not None
            and task.planned_by_pa <= today
        ):
            changes.append(change(task, "status", "Not Started", "not in today's plan"))
            changes.append(change(task, "planned_by_pa", None, "not in today's plan"))
        elif task.is_open and task.status != "Today" and task.planned_by_pa is not None:
            changes.append(change(task, "planned_by_pa", None, "no longer in Today"))
    return changes
