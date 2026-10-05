from datetime import timedelta

from jeeves.hygiene import inference_changes
from jeeves.model import ResetProposal, Snapshot, apply_changes, change


def propose_reset(snapshot: Snapshot) -> ResetProposal:
    today, prefs = snapshot.today, snapshot.prefs
    changes = inference_changes(snapshot.tasks, snapshot.inferences)
    tasks = apply_changes(snapshot.tasks, changes)
    stale_cutoff = today - timedelta(days=prefs.stale_days)
    recent_cutoff = today - timedelta(days=prefs.recent_soft_days)
    uninferred = []
    for task in tasks:
        if not task.is_open:
            continue
        if task.due is not None and task.original_due is None:
            changes.append(
                change(task, "original_due", task.due, "backlog reset: preserve")
            )
        if task.effective_deadline_type is None:
            uninferred.append(task.id)
            continue
        if task.effective_deadline_type == "Hard":
            continue
        if task.last_edited < stale_cutoff:
            reason = f"backlog reset: untouched since {task.last_edited}"
            changes.append(change(task, "status", "Someday", reason))
        elif task.due is not None and task.last_edited < recent_cutoff:
            reason = "backlog reset: unproven date cleared (original kept)"
            changes.append(change(task, "due", None, reason))
    return ResetProposal(changes=changes, uninferred_ids=uninferred)
