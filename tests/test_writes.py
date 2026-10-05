from datetime import date

from jeeves.model import BlockCreate, DailyPlanState, FieldChange, PlanResult
from jeeves.writes import build_writes, task_writes
from tests.factories import TODAY, YESTERDAY, at, make_snapshot, make_task


def change(task_id, field, old, new, reason="r"):
    return FieldChange(task_id=task_id, field=field, old=old, new=new, reason=reason)


def test_task_changes_are_grouped_per_task_with_notion_names():
    writes = task_writes(
        [
            change("t1", "due", date(2026, 10, 2), TODAY),
            change("t1", "original_due", None, date(2026, 10, 2)),
            change("t2", "status", "Today", "Not Started"),
            change("t2", "planned_by_pa", YESTERDAY, None),
        ]
    )
    assert writes == [
        {
            "op": "update",
            "page_id": "t1",
            "properties": {"Due": "2026-10-07", "Original due": "2026-10-02"},
        },
        {
            "op": "update",
            "page_id": "t2",
            "properties": {"Status": "Not Started", "Planned by PA": None},
        },
    ]


def plan_rows():
    return {
        "pages": [
            {"id": "row-y", "properties": {"Date": "2026-10-06"}},
            {"id": "row-t", "properties": {"Date": "2026-10-07"}},
        ]
    }


def result(**overrides):
    fields = {
        "status": "planned",
        "focus_minutes": 300,
        "must_do_ids": ["t1"],
        "quick_win_ids": ["t2"],
        "queue_ids": [],
        "changes": [change("t1", "deferrals", 0, 1, "planned 2026-10-06, not done")],
        "blocks_create": [
            BlockCreate(
                task_id="t1",
                start=at(9),
                end=at(10, 30),
                title="🎯 Focus: A",
                private=False,
            )
        ],
        "hard_overdue_count": 2,
        "deferral_limit_count": 0,
        "yesterday_completed": 1,
        "dm_text": "hi",
    }
    return PlanResult(**{**fields, **overrides})


def test_auto_mode_applies_tasks_and_updates_existing_rows():
    snapshot = make_snapshot(
        [make_task("t1", title="A"), make_task("t2", title="B")],
        yesterday_plan=DailyPlanState(day=YESTERDAY, must_do_ids=["t1"]),
    )
    out = build_writes(snapshot, result(), plan_rows(), "db", "auto")
    assert out["task_writes"] == [
        [{"op": "update", "page_id": "t1", "properties": {"Deferrals": 1}}]
    ]
    today, body, yesterday = out["plan_writes"]
    assert today["op"] == "update" and today["page_id"] == "row-t"
    assert today["properties"]["Run status"] == "OK"
    assert today["properties"]["Must-dos"] == ["t1"]
    assert body["op"] == "replace_body" and body["page_id"] == "row-t"
    assert "- A: Deferrals 0 → 1 (planned 2026-10-06, not done)" in body["body_lines"]
    assert yesterday == {
        "op": "update",
        "page_id": "row-y",
        "properties": {"Must-dos completed": 1},
    }


def test_propose_only_writes_no_tasks_and_labels_the_log():
    snapshot = make_snapshot([make_task("t1", title="A"), make_task("t2", title="B")])
    out = build_writes(snapshot, result(), {"pages": []}, "db", "propose-only")
    assert out["task_writes"] == []
    create = out["plan_writes"][0]
    assert create["op"] == "create" and create["database_id"] == "db"
    assert create["properties"]["Date"] == "2026-10-07"
    assert create["properties"]["Run status"] == "Proposed"
    assert create["body_lines"][0] == "## Would change (trial – nothing applied)"
    assert any("Focus block 09:00–10:30" in line for line in create["body_lines"])


def test_task_writes_are_chunked_by_forty():
    tasks = [make_task(f"t{i}") for i in range(45)]
    changes = [change(f"t{i}", "size", None, "S") for i in range(45)]
    snapshot = make_snapshot(tasks)
    out = build_writes(snapshot, result(changes=changes), {"pages": []}, "db", "auto")
    assert [len(chunk) for chunk in out["task_writes"]] == [40, 5]


def test_locked_result_only_updates_counts():
    snapshot = make_snapshot([make_task()])
    locked = PlanResult(status="locked", hard_overdue_count=3, deferral_limit_count=1)
    out = build_writes(snapshot, locked, plan_rows(), "db", "auto")
    assert out == {
        "task_writes": [],
        "plan_writes": [
            {
                "op": "update",
                "page_id": "row-t",
                "properties": {"Hard-overdue count": 3, "Deferral-limit count": 1},
            }
        ],
    }


def test_skipped_result_writes_nothing():
    out = build_writes(
        make_snapshot([]), PlanResult(status="skipped"), plan_rows(), "db", "auto"
    )
    assert out == {"task_writes": [], "plan_writes": []}


def test_backlog_review_is_written_to_the_plan_row():
    snapshot = make_snapshot([make_task("t1", title="A")])
    out = build_writes(
        snapshot, result(review_ids=["p9"]), {"pages": []}, "db", "propose-only"
    )
    assert out["plan_writes"][0]["properties"]["Backlog review"] == ["p9"]
