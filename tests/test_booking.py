from jeeves.booking import QUICK_WINS_TITLE, plan_blocks
from jeeves.model import Preferences
from tests.factories import at, make_task

NOW = at(7, 30)


def spans(blocks):
    return [(b.task_id, b.start, b.end) for b in blocks]


def test_quick_wins_take_preferred_slot_then_must_dos_fill_in_order():
    tasks = [make_task("a"), make_task("b", size="S")]
    blocks = plan_blocks(tasks, True, [(at(9), at(17, 30))], NOW, Preferences())
    assert spans(blocks) == [
        (None, at(13, 30), at(14)),
        ("a", at(9), at(10, 30)),
        ("b", at(10, 30), at(10, 45)),
    ]
    assert blocks[0].title == QUICK_WINS_TITLE


def test_confidential_block_is_generic_and_private():
    task = make_task(title="Interview candidates", confidential=True)
    block = plan_blocks([task], False, [(at(9), at(12))], NOW, Preferences())[0]
    assert block.title == "🎯 Focus block"
    assert block.private


def test_normal_block_names_the_task():
    block = plan_blocks(
        [make_task(title="Write brief")], False, [(at(9), at(12))], NOW, Preferences()
    )[0]
    assert block.title == "🎯 Focus: Write brief"
    assert not block.private


def test_personal_must_dos_get_no_block():
    assert (
        plan_blocks(
            [make_task(area="Personal")], False, [(at(9), at(12))], NOW, Preferences()
        )
        == []
    )


def test_partial_block_when_no_full_slot():
    blocks = plan_blocks([make_task()], False, [(at(9), at(9, 45))], NOW, Preferences())
    assert spans(blocks) == [("t1", at(9), at(9, 45))]


def test_no_block_when_no_slot_meets_minimum():
    assert (
        plan_blocks([make_task()], False, [(at(9), at(9, 20))], NOW, Preferences())
        == []
    )


def test_quick_wins_fall_back_to_earliest_slot():
    blocks = plan_blocks([], True, [(at(9), at(10))], NOW, Preferences())
    assert spans(blocks) == [(None, at(9), at(9, 30))]
