from datetime import date

from jeeves.model import (
    AlsoRelevant,
    BlockCreate,
    DailyPlanState,
    FieldChange,
    PlanResult,
)
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
            "properties": {
                "Due": {"date": {"start": "2026-10-07"}},
                "Original due": {"date": {"start": "2026-10-02"}},
            },
        },
        {
            "op": "update",
            "page_id": "t2",
            "properties": {
                "Status": {"status": {"name": "Not Started"}},
                "Planned by PA": {"date": None},
            },
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
        [{"op": "update", "page_id": "t1", "properties": {"Deferrals": {"number": 1}}}]
    ]
    today, body, yesterday = out["plan_writes"]
    assert today["op"] == "update" and today["page_id"] == "row-t"
    assert today["properties"]["Run status"] == {"select": {"name": "OK"}}
    assert today["properties"]["Must-dos"] == {"relation": [{"id": "t1"}]}
    assert body["op"] == "replace_body" and body["page_id"] == "row-t"
    assert "- A: Deferrals 0 → 1 (planned 2026-10-06, not done)" in body["body_lines"]
    assert yesterday == {
        "op": "update",
        "page_id": "row-y",
        "properties": {"Must-dos completed": {"number": 1}},
    }


def test_propose_only_writes_no_tasks_and_labels_the_log():
    snapshot = make_snapshot([make_task("t1", title="A"), make_task("t2", title="B")])
    out = build_writes(snapshot, result(), {"pages": []}, "db", "propose-only")
    assert out["task_writes"] == []
    create = out["plan_writes"][0]
    assert create["op"] == "create" and create["database_id"] == "db"
    assert create["properties"]["Date"] == {
        "title": [{"text": {"content": "2026-10-07"}}]
    }
    assert create["properties"]["Run status"] == {"select": {"name": "Proposed"}}
    assert create["body_lines"][0] == "## Would change (trial – nothing applied)"
    assert any("Focus block 09:00–10:30" in line for line in create["body_lines"])


def test_task_writes_are_chunked_by_ten():
    tasks = [make_task(f"t{i}") for i in range(45)]
    changes = [change(f"t{i}", "size", None, "S") for i in range(45)]
    snapshot = make_snapshot(tasks)
    out = build_writes(snapshot, result(changes=changes), {"pages": []}, "db", "auto")
    assert [len(chunk) for chunk in out["task_writes"]] == [10, 10, 10, 10, 5]


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
                "properties": {
                    "Hard-overdue count": {"number": 3},
                    "Deferral-limit count": {"number": 1},
                },
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
    assert out["plan_writes"][0]["properties"]["Backlog review"] == {
        "relation": [{"id": "p9"}]
    }


def test_every_value_type_is_encoded():
    from jeeves.writes import encode

    assert encode("Size", "S") == {"select": {"name": "S"}}
    assert encode("Size", None) == {"select": None}
    assert encode("Confidential", True) == {"checkbox": True}
    assert encode("Run note", "boom") == {"rich_text": [{"text": {"content": "boom"}}]}
    assert encode("Run note", None) == {"rich_text": []}


def _body(snapshot, changes):
    out = build_writes(
        snapshot,
        PlanResult(status="planned", changes=changes),
        {"pages": []},
        "db",
        "auto",
    )
    return out["plan_writes"][0]["body_lines"]


def test_log_has_one_line_per_task_with_old_and_new():
    snapshot = make_snapshot([make_task("a", title="Alpha")])
    lines = _body(
        snapshot,
        [
            change("a", "size", None, "M", "inferred"),
            change("a", "area", None, "Work", "inferred"),
            change("a", "due", date(2026, 10, 1), TODAY, "soft date passed"),
        ],
    )
    assert lines[1] == (
        "- Alpha: Size → M; Area → Work; Due 2026-10-01 → 2026-10-07 "
        "(inferred; soft date passed)"
    )
    assert lines[2] == "## Calendar"


def test_log_omits_reason_when_every_change_is_an_inferred_fill():
    snapshot = make_snapshot([make_task("a", title="Alpha")])
    lines = _body(snapshot, [change("a", "size", None, "M", "inferred")])
    assert lines[1] == "- Alpha: Size → M"


def test_log_shortens_long_titles():
    title = "JIRA | ASQ-1 - " + "very long title " * 5
    snapshot = make_snapshot([make_task("a", title=title)])
    lines = _body(snapshot, [change("a", "size", None, "M", "inferred")])
    name = lines[1].removeprefix("- ").split(": Size")[0]
    assert len(name) <= 50
    assert name.endswith("…")


def test_log_hides_confidential_titles():
    snapshot = make_snapshot([make_task("c", title="Comp band", confidential=True)])
    lines = _body(snapshot, [change("c", "size", None, "S", "inferred")])
    assert lines[1] == "- 🔒 confidential task: Size → S"


def test_log_hides_title_of_task_inferred_confidential():
    snapshot = make_snapshot([make_task("c", title="Salary review", size=None)])
    lines = _body(snapshot, [change("c", "confidential", False, True, "inferred")])
    assert "Salary review" not in "\n".join(lines)


def test_body_lists_birthdays_and_also_relevant_before_the_calendar():
    snapshot = make_snapshot(
        [
            make_task("b", title="Message Ann — happy birthday", due=date(2026, 10, 5)),
            make_task("t", title="Prep board deck"),
            make_task("c", title="Comp band", confidential=True),
        ]
    )
    result = PlanResult(
        status="planned",
        birthday_ids=["b"],
        also_relevant=[
            AlsoRelevant(task_id="t", reason="High priority"),
            AlsoRelevant(task_id="c", reason="Hard, due Fri 09 Oct"),
        ],
        also_relevant_more=2,
    )
    out = build_writes(snapshot, result, {"pages": []}, "db", "auto")
    lines = out["plan_writes"][0]["body_lines"]
    assert lines[lines.index("## Birthdays") + 1] == (
        "- Message Ann — happy birthday: 2 days late (due 05 Oct)"
    )
    start = lines.index("## Also relevant, not planned")
    assert lines[start + 1 : start + 4] == [
        "- Prep board deck: High priority",
        "- 🔒 confidential task: Hard, due Fri 09 Oct",
        "- … and 2 more",
    ]
    assert lines.index("## Calendar") > start


def test_body_has_no_extra_sections_when_nothing_to_show():
    lines = _body(make_snapshot([make_task("a")]), [])
    assert "## Birthdays" not in lines
    assert "## Also relevant, not planned" not in lines


def test_body_lists_lunch_errands():
    snapshot = make_snapshot([make_task("e", title="Return parcel")])
    result = PlanResult(status="planned", errand_ids=["e"])
    out = build_writes(snapshot, result, {"pages": []}, "db", "auto")
    lines = out["plan_writes"][0]["body_lines"]
    assert lines[lines.index("## Lunch errands") + 1] == "- Return parcel"


def test_many_pure_fills_collapse_into_one_summary_line():
    tasks = [make_task(f"t{i}", title=f"Task {i}") for i in range(30)]
    changes = [change(f"t{i}", "size", None, "M", "inferred") for i in range(30)]
    changes += [change(f"t{i}", "area", None, "Work", "inferred") for i in range(30)]
    changes.append(change("t0", "due", date(2026, 10, 1), TODAY, "soft date passed"))
    lines = _body(make_snapshot(tasks), changes)
    assert lines[1] == (
        "- Task 0: Size → M; Area → Work; Due 2026-10-01 → 2026-10-07 "
        "(inferred; soft date passed)"
    )
    assert lines[2] == (
        "- 29 tasks filled in (empty before, not itemised): Area → Work ×29; Size → M ×29"
    )
    assert lines[3] == "## Calendar"


def test_few_pure_fills_stay_itemised():
    tasks = [make_task(f"t{i}", title=f"Task {i}") for i in range(3)]
    changes = [change(f"t{i}", "size", None, "M", "inferred") for i in range(3)]
    lines = _body(make_snapshot(tasks), changes)
    assert lines[1:4] == [f"- Task {i}: Size → M" for i in range(3)]


def test_inferred_confidential_flags_are_never_collapsed():
    tasks = [make_task(f"t{i}", title=f"Task {i}", size=None) for i in range(30)]
    changes = [change(f"t{i}", "size", None, "M", "inferred") for i in range(30)]
    changes.append(
        change("t5", "confidential", False, True, "inferred: likely sensitive")
    )
    lines = _body(make_snapshot(tasks), changes)
    assert any(line.startswith("- 🔒 confidential task:") for line in lines)
    assert "- 29 tasks filled in" in "\n".join(lines)
