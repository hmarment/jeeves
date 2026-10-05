from datetime import date

from jeeves.model import PARKED_STATUS, FieldChange, Inference, Task, change

INFERABLE_FIELDS = ("area", "size", "deadline_type")


def roll_due(task: Task, new_due: date, reason: str) -> list[FieldChange]:
    changes = []
    if task.original_due is None:
        changes.append(change(task, "original_due", task.due, "preserve before moving"))
    changes.append(change(task, "due", new_due, reason))
    return changes


def inference_changes(
    tasks: list[Task], inferences: dict[str, Inference]
) -> list[FieldChange]:
    changes = []
    for task in tasks:
        inference = inferences.get(task.id)
        if inference is None or not task.is_open:
            continue
        # Confidential is a checkbox, so "never assessed" can only be told apart from
        # "the user unticked it" while the task still lacks its other inferred fields.
        if inference.confidential and task.needs_inference and not task.confidential:
            changes.append(
                change(task, "confidential", True, "inferred: likely sensitive")
            )
        for field in INFERABLE_FIELDS:
            value = getattr(inference, field)
            if field == "deadline_type" and task.is_protected:
                value = "Hard"
            if value is not None and getattr(task, field) is None:
                changes.append(change(task, field, value, "inferred"))
    return changes


def duplicate_changes(
    tasks: list[Task], inferences: dict[str, Inference]
) -> tuple[list[FieldChange], list[str]]:
    open_ids = {task.id for task in tasks if task.is_open}
    archived: set[str] = set()
    changes, uncertain = [], []
    # Newest first, so of two tasks naming each other the older one survives.
    for task in sorted(tasks, key=lambda t: (t.created, t.id), reverse=True):
        inference = inferences.get(task.id)
        if inference is None or task.id not in open_ids or task.is_protected:
            continue
        target = inference.duplicate_of
        if target is None or target == task.id or target not in open_ids:
            continue
        if target in archived:
            continue
        if inference.duplicate_certain and not task.is_manual_today:
            archived.add(task.id)
            changes.append(change(task, "status", "Archived", f"duplicate of {target}"))
        else:
            uncertain.append(task.id)
    return changes, sorted(uncertain)


def soft_roll_changes(
    tasks: list[Task], today: date, skip: set[str], deferral_limit: int
) -> list[FieldChange]:
    changes = []
    for task in tasks:
        if (
            task.is_open
            and task.status != PARKED_STATUS
            and task.effective_deadline_type == "Soft"
            and task.due is not None
            and task.due < today
            and task.id not in skip
            and task.deferrals < deferral_limit
        ):
            changes.extend(
                roll_due(task, today, "soft date passed; rolled, no deferral")
            )
    return changes
