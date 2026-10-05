from datetime import date

from jeeves.hygiene import duplicate_changes, inference_changes, soft_roll_changes
from jeeves.model import Inference
from tests.factories import TODAY, YESTERDAY, make_task


def fields(changes):
    return {(c.task_id, c.field): c.new for c in changes}


def test_inference_fills_only_empty_fields():
    task = make_task(size=None, area="Personal")
    changes = inference_changes([task], {"t1": Inference(size="S", area="Work")})
    assert fields(changes) == {("t1", "size"): "S"}


def test_confidential_is_only_inferred_for_unassessed_tasks():
    assessed = make_task("a")
    fresh = make_task("b", size=None)
    inferences = {
        "a": Inference(confidential=True),
        "b": Inference(confidential=True, size="M"),
    }
    result = fields(inference_changes([assessed, fresh], inferences))
    assert ("a", "confidential") not in result
    assert result[("b", "confidential")] is True


def test_closed_tasks_are_not_inferred():
    task = make_task(status="Done", size=None)
    assert inference_changes([task], {"t1": Inference(size="S")}) == []


def test_certain_duplicate_is_archived_not_done():
    inferences = {"t1": Inference(duplicate_of="t9", duplicate_certain=True)}
    changes, uncertain = duplicate_changes([make_task(), make_task("t9")], inferences)
    assert fields(changes) == {("t1", "status"): "Archived"}
    assert uncertain == []


def test_uncertain_duplicate_is_returned_for_the_queue():
    changes, uncertain = duplicate_changes(
        [make_task(), make_task("t9")], {"t1": Inference(duplicate_of="t9")}
    )
    assert changes == []
    assert uncertain == ["t1"]


def test_protected_task_is_never_archived_as_duplicate():
    inferences = {"t1": Inference(duplicate_of="t9", duplicate_certain=True)}
    changes, uncertain = duplicate_changes(
        [make_task(title="90 | Same todo")], inferences
    )
    assert changes == []
    assert uncertain == []


def test_unplanned_soft_overdue_rolls_without_deferral_and_preserves_original():
    task = make_task(due=date(2026, 10, 2))
    changes = soft_roll_changes([task], TODAY, skip=set(), deferral_limit=3)
    assert fields(changes) == {
        ("t1", "original_due"): date(2026, 10, 2),
        ("t1", "due"): TODAY,
    }


def test_existing_original_due_is_not_overwritten():
    task = make_task(due=YESTERDAY, original_due=date(2026, 9, 1))
    assert ("t1", "original_due") not in fields(
        soft_roll_changes([task], TODAY, set(), 3)
    )


def test_hard_and_empty_deadline_types_never_roll():
    hard = make_task("h", due=YESTERDAY, deadline_type="Hard")
    empty = make_task("e", due=YESTERDAY, deadline_type=None)
    jira = make_task("j", title="JIRA | ASQ-1", due=YESTERDAY, deadline_type="Soft")
    assert soft_roll_changes([hard, empty, jira], TODAY, set(), 3) == []


def test_planned_and_queued_tasks_are_not_rolled_here():
    planned = make_task("p", due=YESTERDAY)
    queued = make_task("q", due=YESTERDAY, deferrals=3)
    assert soft_roll_changes([planned, queued], TODAY, {"p"}, 3) == []


def test_self_duplicate_is_ignored():
    inferences = {"t1": Inference(duplicate_of="t1", duplicate_certain=True)}
    assert duplicate_changes([make_task()], inferences) == ([], [])


def test_mutual_duplicates_keep_the_older_task():
    older = make_task("old", created=date(2026, 8, 1))
    newer = make_task("new", created=date(2026, 9, 1))
    inferences = {
        "old": Inference(duplicate_of="new", duplicate_certain=True),
        "new": Inference(duplicate_of="old", duplicate_certain=True),
    }
    changes, _ = duplicate_changes([older, newer], inferences)
    assert fields(changes) == {("new", "status"): "Archived"}


def test_duplicate_of_missing_or_closed_task_is_ignored():
    closed = make_task("closed", status="Done")
    inferences = {
        "t1": Inference(duplicate_of="missing", duplicate_certain=True),
        "t2": Inference(duplicate_of="closed", duplicate_certain=True),
    }
    assert duplicate_changes(
        [make_task("t1"), make_task("t2"), closed], inferences
    ) == (
        [],
        [],
    )


def test_manual_today_duplicate_goes_to_queue_not_archive():
    mine = make_task("mine", status="Today")
    inferences = {"mine": Inference(duplicate_of="t9", duplicate_certain=True)}
    changes, uncertain = duplicate_changes([mine, make_task("t9")], inferences)
    assert changes == []
    assert uncertain == ["mine"]


def test_protected_task_never_gets_soft_written():
    task = make_task(title="JIRA | ASQ-1", deadline_type=None)
    changes = inference_changes([task], {"t1": Inference(deadline_type="Soft")})
    assert fields(changes) == {("t1", "deadline_type"): "Hard"}


def test_backlog_tasks_are_parked_and_never_rolled():
    task = make_task(status="Backlog", due=YESTERDAY)
    assert soft_roll_changes([task], TODAY, set(), 3) == []
