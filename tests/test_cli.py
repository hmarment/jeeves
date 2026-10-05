import json

from jeeves.cli import main
from tests.factories import make_snapshot, make_task


def test_decide_prints_plan_json(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text(make_snapshot([make_task()]).model_dump_json())
    assert main(["decide", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "planned"


def test_invalid_snapshot_exits_nonzero_with_message(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text('{"now": "2026-10-07T07:30:00", "tasks": []}')
    assert main(["decide", str(path)]) == 2
    assert "timezone-aware" in capsys.readouterr().err


def test_reset_prints_proposal_json(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text(make_snapshot([make_task()]).model_dump_json())
    assert main(["reset", str(path)]) == 0
    assert "changes" in json.loads(capsys.readouterr().out)
