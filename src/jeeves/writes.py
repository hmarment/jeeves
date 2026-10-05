from datetime import date
from typing import Any

from jeeves.model import FieldChange, PlanResult, Snapshot
from jeeves.snapshot import unwrap_pages

NOTION_NAMES = {
    "status": "Status",
    "due": "Due",
    "original_due": "Original due",
    "priority": "Priority",
    "size": "Size",
    "deadline_type": "Deadline type",
    "area": "Area",
    "confidential": "Confidential",
    "deferrals": "Deferrals",
    "last_deferred": "Last deferred",
    "planned_by_pa": "Planned by PA",
}
BATCH_SIZE = 40


def _value(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


def task_writes(changes: list[FieldChange]) -> list[dict]:
    by_task: dict[str, dict] = {}
    for item in changes:
        properties = by_task.setdefault(item.task_id, {})
        properties[NOTION_NAMES[item.field]] = _value(item.new)
    return [
        {"op": "update", "page_id": task_id, "properties": properties}
        for task_id, properties in by_task.items()
    ]


def _show(value: Any) -> str:
    return "–" if value is None else str(_value(value))


def _log_lines(snapshot: Snapshot, result: PlanResult, mode: str) -> list[str]:
    titles = {task.id: task.title for task in snapshot.tasks}
    heading = (
        "## Change log"
        if mode == "auto"
        else "## Would change (trial – nothing applied)"
    )
    lines = [heading]
    for item in result.changes:
        title = titles.get(item.task_id, item.task_id)
        label = NOTION_NAMES[item.field]
        lines.append(
            f"- {title}: {label} {_show(item.old)} → {_show(item.new)} ({item.reason})"
        )
    if not result.changes:
        lines.append("- No task changes")
    lines.append("## Calendar")
    for block in result.blocks_create:
        lines.append(
            f"- Focus block {block.start:%H:%M}–{block.end:%H:%M}: {block.title}"
        )
    for block in result.blocks_delete:
        lines.append(f"- Remove block {block.event_id} ({block.reason})")
    return lines


def _rows_by_date(plan_payload: Any) -> dict[str, str]:
    return {
        page["properties"]["Date"]: page["id"] for page in unwrap_pages(plan_payload)
    }


def build_writes(
    snapshot: Snapshot,
    result: PlanResult,
    plan_payload: Any,
    database_id: str,
    mode: str,
) -> dict[str, list]:
    rows = _rows_by_date(plan_payload)
    today = snapshot.today.isoformat()
    if result.status == "skipped":
        return {"task_writes": [], "plan_writes": []}
    counts = {
        "Hard-overdue count": result.hard_overdue_count,
        "Deferral-limit count": result.deferral_limit_count,
    }
    if result.status == "locked":
        plan_writes = (
            [{"op": "update", "page_id": rows[today], "properties": counts}]
            if today in rows
            else []
        )
        return {"task_writes": [], "plan_writes": plan_writes}

    updates = task_writes(result.changes) if mode == "auto" else []
    chunks = [updates[i : i + BATCH_SIZE] for i in range(0, len(updates), BATCH_SIZE)]
    properties = {
        "Date": today,
        "Focus minutes": result.focus_minutes,
        "Must-dos": result.must_do_ids,
        "Quick wins": result.quick_win_ids,
        "Decision queue": result.queue_ids,
        **counts,
        "Run status": "OK" if mode == "auto" else "Proposed",
    }
    body = _log_lines(snapshot, result, mode)
    if today in rows:
        plan_writes = [
            {"op": "update", "page_id": rows[today], "properties": properties},
            {"op": "replace_body", "page_id": rows[today], "body_lines": body},
        ]
    else:
        plan_writes = [
            {
                "op": "create",
                "database_id": database_id,
                "properties": properties,
                "body_lines": body,
            }
        ]
    yesterday = snapshot.yesterday_plan
    if (
        result.yesterday_completed is not None
        and yesterday is not None
        and yesterday.day.isoformat() in rows
    ):
        plan_writes.append(
            {
                "op": "update",
                "page_id": rows[yesterday.day.isoformat()],
                "properties": {"Must-dos completed": result.yesterday_completed},
            }
        )
    return {"task_writes": chunks, "plan_writes": plan_writes}
