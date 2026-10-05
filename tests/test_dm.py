from jeeves.dm import render_dm
from tests.factories import TODAY, make_task


def test_dm_mentions_focus_time_first_must_do_and_queue():
    text = render_dm(TODAY, 150, make_task(title="Write quarterly report"), 2, 0)
    assert "2h30" in text
    assert "Write quarterly report" in text
    assert "2 decisions waiting" in text
    assert "Run /start-day" in text


def test_dm_flags_over_capacity_and_handles_empty_plan():
    text = render_dm(TODAY, 60, None, 1, 45)
    assert "Over capacity by 45 min" in text
    assert "1 decision waiting" in text
